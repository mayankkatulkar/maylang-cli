#!/bin/sh
# ============================================================================
# verify_wheel.sh — Validate the *built artifact* (wheel) for maylang-cli
#
# Builds wheel + sdist, installs the wheel into an isolated venv, then runs
# CLI smoke tests against the installed package.  This proves the distribution
# works independently of the editable source tree.
#
# Usage:
#   bash scripts/verify_wheel.sh
# ============================================================================
set -e

VENV_DIR=".venv-wheel"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# ── Helpers ──────────────────────────────────────────────────────────────────

step() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  STEP: $1"
    echo "═══════════════════════════════════════════════════════════════"
}

fail() {
    echo ""
    echo "✗ FAILED: $1" >&2
    exit 1
}

ok() {
    echo "✓ $1"
}

# ── 1. Build wheel and sdist ────────────────────────────────────────────────

step "Build wheel and sdist"

# Ensure build is available (install if missing)
pip install --quiet build 2>/dev/null || python3 -m pip install --quiet build

# Clean previous builds
rm -rf dist/

python3 -m build --quiet || fail "python -m build failed"

WHEEL="$(ls dist/*.whl 2>/dev/null | head -1)"
SDIST="$(ls dist/*.tar.gz 2>/dev/null | head -1)"

if [ -z "$WHEEL" ]; then
    fail "No .whl file found in dist/"
fi

ok "Built wheel: $WHEEL"
echo "  sdist:  $SDIST"

# ── 2. Create fresh venv ────────────────────────────────────────────────────

step "Create fresh virtual environment in $VENV_DIR"

if [ -d "$VENV_DIR" ]; then
    echo "  Removing existing $VENV_DIR ..."
    rm -rf "$VENV_DIR"
fi

python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
. "$VENV_DIR/bin/activate"

pip install --quiet --upgrade pip

ok "Virtual environment ready: $(python3 -c 'import sys; print(sys.executable)')"

# ── 3. Install ONLY the built wheel ─────────────────────────────────────────

step "Install wheel (not editable source)"

pip install --quiet "$WHEEL" || fail "pip install wheel failed"

ok "Installed $(pip show maylang-cli | grep '^Version:' | awk '{print $2}') from wheel"

# ── 4. Move to a neutral directory ──────────────────────────────────────────
# Run all remaining checks from a temp directory so Python cannot accidentally
# import the local source tree via CWD.

SMOKE_DIR="$(mktemp -d)"
ORIG_DIR="$(pwd)"
cd "$SMOKE_DIR"

# ── 5. Verify the import resolves to the venv (NOT the repo source) ─────────

step "Verify maylang_cli import resolves to venv site-packages"

IMPORT_PATH="$(python3 -c 'import maylang_cli; print(maylang_cli.__file__)')"
case "$IMPORT_PATH" in
    *site-packages*)
        ok "Import resolves to venv: $IMPORT_PATH"
        ;;
    "$REPO_ROOT"*)
        cd "$ORIG_DIR"
        rm -rf "$SMOKE_DIR"
        fail "maylang_cli imported from repo source: $IMPORT_PATH (expected venv site-packages)"
        ;;
    *)
        ok "Import resolves to: $IMPORT_PATH"
        ;;
esac

# ── 6. CLI smoke test: may --version ─────────────────────────────────────────

step "CLI smoke test: may --version"

VERSION_OUTPUT="$(may --version 2>&1)"
echo "  $VERSION_OUTPUT"
case "$VERSION_OUTPUT" in
    may\ *)
        ok "may --version works"
        ;;
    *)
        cd "$ORIG_DIR"
        rm -rf "$SMOKE_DIR"
        fail "Unexpected --version output: $VERSION_OUTPUT"
        ;;
esac

# ── 7. CLI smoke test: may --help ────────────────────────────────────────────

step "CLI smoke test: may --help"

may --help > /dev/null 2>&1 || fail "may --help failed"
ok "may --help works"

# ── 8. Smoke test: may new + may check ──────────────────────────────────────

step "Smoke test: may new + may check (from wheel install)"

# We're already in SMOKE_DIR, which is outside the repo

# Initialize a minimal git repo
git init --quiet .
git commit --allow-empty -m "initial" --quiet

# Expect exit code 2 when no files exist
EXIT_CODE=0
may check --require always > /dev/null 2>&1 || EXIT_CODE=$?

if [ "$EXIT_CODE" -ne 2 ]; then
    cd "$ORIG_DIR"
    rm -rf "$SMOKE_DIR"
    fail "Expected exit code 2 (missing), got $EXIT_CODE"
fi
ok "may check correctly exited with code 2 (no .may.md files)"

# Create a change package and check again
may new --id MC-0099 --slug wheel-smoke --scope backend --risk low --owner "ci" \
    > /dev/null 2>&1 || {
    cd "$ORIG_DIR"
    rm -rf "$SMOKE_DIR"
    fail "may new failed"
}

EXIT_CODE=0
may check --require always > /dev/null 2>&1 || EXIT_CODE=$?

cd "$ORIG_DIR"
rm -rf "$SMOKE_DIR"

if [ "$EXIT_CODE" -eq 0 ]; then
    ok "may check passed after may new (exit code 0)"
else
    fail "Expected exit code 0 after may new, got $EXIT_CODE"
fi

# ── Done ─────────────────────────────────────────────────────────────────────

deactivate 2>/dev/null || true

step "All wheel verification passed ✓"
echo ""
echo "  Wheel: $WHEEL"
echo "  Venv left at $VENV_DIR for inspection (delete when done)."
echo ""
