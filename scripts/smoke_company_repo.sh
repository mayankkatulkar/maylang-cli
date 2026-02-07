#!/bin/sh
# ============================================================================
# smoke_company_repo.sh — Simulate real-world company adoption of maylang-cli
#
# Creates a temporary git repository, exercises the full `may` CLI workflow
# exactly as a company would during adoption: checking for missing packages,
# creating one, validating it, and testing change-detection mode.
#
# Expects `may` to be on PATH (run after pip install or inside a venv).
#
# Set KEEP_TMP=1 to preserve the temp directory for manual inspection.
#
# Usage:
#   bash scripts/smoke_company_repo.sh
#   KEEP_TMP=1 bash scripts/smoke_company_repo.sh
# ============================================================================
set -e

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
    echo "  Temp directory: $SMOKE_DIR" >&2
    exit 1
}

ok() {
    echo "✓ $1"
}

cleanup() {
    if [ "${KEEP_TMP:-0}" = "1" ]; then
        echo ""
        echo "  KEEP_TMP=1 → temp directory preserved: $SMOKE_DIR"
    else
        rm -rf "$SMOKE_DIR"
        echo "  Cleaned up temp directory."
    fi
}

# ── Setup temp repo ─────────────────────────────────────────────────────────

step "Create temporary company repo"

SMOKE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/maylang-smoke-XXXX")"
trap cleanup EXIT

cd "$SMOKE_DIR"

git init --quiet .
git config user.email "ci@maylang.local"
git config user.name "MayLang CI"

# Create some "company" source files and make an initial commit
mkdir -p auth payments docs
echo 'def login(): pass' > auth/login.py
echo 'def charge(): pass' > payments/charge.py
echo '# README' > docs/readme.md
git add -A
git commit --quiet -m "initial: project scaffold"

ok "Repo initialised at $SMOKE_DIR"

# ── Test 1: may check --require always (no .may.md → exit 2) ────────────────

step "Test 1: may check --require always (expect exit 2)"

EXIT_CODE=0
may check --require always > /dev/null 2>&1 || EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 2 ]; then
    ok "Correctly returned exit code 2 (no MayLang files)"
else
    fail "Expected exit 2, got $EXIT_CODE"
fi

# ── Test 2: may new creates a valid file ─────────────────────────────────────

step "Test 2: may new creates a valid .may.md file"

may new --id MC-0001 --slug auth-sessions --scope backend --risk low --owner "team-alpha" \
    > /dev/null 2>&1 || fail "may new failed"

if [ -f "maylang/MC-0001-auth-sessions.may.md" ]; then
    ok "File created: maylang/MC-0001-auth-sessions.may.md"
else
    fail "Expected file maylang/MC-0001-auth-sessions.may.md not found"
fi

# ── Test 3: may check --require always (valid file → exit 0) ────────────────

step "Test 3: may check --require always (expect exit 0)"

EXIT_CODE=0
may check --require always > /dev/null 2>&1 || EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
    ok "may check passed (exit code 0)"
else
    fail "Expected exit 0, got $EXIT_CODE"
fi

# ── Test 4: may check --require changed with path matching ──────────────────

step "Test 4: may check --require changed --base HEAD~1 --paths auth/"

# Commit the MayLang file so it's part of history
git add -A
git commit --quiet -m "feat: add MayLang change package"

# Make a new change under auth/ and commit it
echo 'def logout(): pass' >> auth/login.py
git add -A
git commit --quiet -m "feat: add logout to auth"

# Now HEAD~1 has the MayLang file, but HEAD changed auth/login.py.
# Since maylang/ files exist and are valid, this should pass.
EXIT_CODE=0
may check --require changed --base HEAD~1 --paths auth/ 2>/dev/null || EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
    ok "may check --require changed passed (MayLang file present, exit 0)"
else
    fail "Expected exit 0 for --require changed with existing .may.md, got $EXIT_CODE"
fi

# ── Test 5: may check --require changed (no .may.md, change in auth/) ───────

step "Test 5: may check --require changed with missing .may.md (expect exit 2)"

# Remove the MayLang file and commit
rm -rf maylang
git add -A
git commit --quiet -m "chore: remove MayLang file"

# Make another auth/ change
echo '# session handling' >> auth/login.py
git add -A
git commit --quiet -m "feat: session handling"

# HEAD~1 removed the file, HEAD changed auth/.  No .may.md → exit 2.
EXIT_CODE=0
may check --require changed --base HEAD~1 --paths auth/ 2>/dev/null || EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 2 ]; then
    ok "Correctly returned exit 2 (auth/ changed, no .may.md)"
else
    fail "Expected exit 2 for missing .may.md with auth/ changes, got $EXIT_CODE"
fi

# ── Test 6: may check --require changed (change only in docs/, not auth/) ───

step "Test 6: may check --require changed (docs/ change, --paths auth/)"

echo '# updated' >> docs/readme.md
git add -A
git commit --quiet -m "docs: update readme"

# Only docs/ changed, but --paths filters on auth/ → not required → exit 0
EXIT_CODE=0
may check --require changed --base HEAD~1 --paths auth/ 2>/dev/null || EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
    ok "Correctly returned exit 0 (docs/ change does not trigger auth/ path filter)"
else
    fail "Expected exit 0 when only docs/ changed, got $EXIT_CODE"
fi

# ── Done ─────────────────────────────────────────────────────────────────────

step "All company-repo smoke tests passed ✓"
echo ""
echo "  Temp repo: $SMOKE_DIR"
echo ""
