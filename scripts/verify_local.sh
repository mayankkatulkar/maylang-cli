#!/bin/sh
# ============================================================================
# verify_local.sh — Post-hardening local verification for maylang-cli
#
# Creates a fresh virtual environment, installs in editable mode with dev
# deps, runs linting, tests, and CLI smoke tests.  Exits non-zero on any
# failure.
#
# Usage:
#   bash scripts/verify_local.sh
# ============================================================================
set -e

VENV_DIR=".venv-verify"
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

# ── 1. Create fresh venv ────────────────────────────────────────────────────

step "Create fresh virtual environment in $VENV_DIR"

if [ -d "$VENV_DIR" ]; then
    echo "  Removing existing $VENV_DIR ..."
    rm -rf "$VENV_DIR"
fi

python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
. "$VENV_DIR/bin/activate"

# Upgrade pip inside the venv (avoid noisy warnings)
pip install --quiet --upgrade pip

ok "Virtual environment ready: $(python3 -c 'import sys; print(sys.executable)')"

# ── 2. Install project in editable mode ─────────────────────────────────────

step "Install maylang-cli in editable mode with dev deps"

pip install --quiet -e ".[dev]"

ok "Installed maylang-cli $(pip show maylang-cli | grep '^Version:' | awk '{print $2}')"

# ── 3. Verify the import resolves to THIS repo ─────────────────────────────

step "Verify maylang_cli import resolves to this repo"

IMPORT_PATH="$(python3 -c 'import maylang_cli; print(maylang_cli.__file__)')"
case "$IMPORT_PATH" in
    "$REPO_ROOT"*)
        ok "Import resolves to repo: $IMPORT_PATH"
        ;;
    *)
        fail "maylang_cli imported from $IMPORT_PATH (expected under $REPO_ROOT)"
        ;;
esac

# ── 4. Lint with ruff ───────────────────────────────────────────────────────

step "Lint with ruff"

ruff check . || fail "ruff check failed"

ok "ruff check passed"

# ── 5. Run pytest ────────────────────────────────────────────────────────────

step "Run pytest"

pytest -q || fail "pytest failed"

ok "All tests passed"

# ── 6. CLI smoke tests ──────────────────────────────────────────────────────

step "CLI smoke test: may --help"

may --help > /dev/null 2>&1 || fail "may --help failed"
ok "may --help works"

step "CLI smoke test: may --version"

VERSION_OUTPUT="$(may --version 2>&1)"
echo "  $VERSION_OUTPUT"
case "$VERSION_OUTPUT" in
    may\ *)
        ok "may --version works"
        ;;
    *)
        fail "Unexpected --version output: $VERSION_OUTPUT"
        ;;
esac

# ── 7. Smoke test: may check should FAIL when no .may.md files exist ────────

step "Smoke test: may check --require always (expect exit 2 = missing)"

SMOKE_DIR="$(mktemp -d)"
ORIG_DIR="$(pwd)"
cd "$SMOKE_DIR"

# Initialize a minimal git repo so git commands don't fail
git init --quiet .
git commit --allow-empty -m "initial" --quiet

EXIT_CODE=0
may check --require always > /dev/null 2>&1 || EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 2 ]; then
    ok "may check correctly exited with code 2 (missing)"
else
    cd "$ORIG_DIR"
    rm -rf "$SMOKE_DIR"
    fail "Expected exit code 2, got $EXIT_CODE"
fi

# ── 8. Smoke test: may new + may check should PASS ──────────────────────────

step "Smoke test: may new + may check --require always (expect exit 0)"

may new --id MC-0099 --slug smoke-test --scope backend --risk low --owner "ci" \
    > /dev/null 2>&1 || fail "may new failed"

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

step "All local verification passed ✓"
echo ""
echo "  Venv left at $VENV_DIR for inspection (delete when done)."
echo ""
