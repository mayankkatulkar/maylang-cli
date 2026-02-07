# MayLang CLI

**Explainable Change Standard** — a minimal, universal spec that reduces AI tech debt across ANY language or repo.

MayLang is a lightweight convention: every meaningful change ships with a **Change Package** (`.may.md` file) that documents *intent*, *contract*, *invariants*, *patch*, *verification*, and *debug map* in a single, machine-readable Markdown file with YAML frontmatter.

`maylang-cli` is the tiny Python CLI that creates and validates these packages.

> **Import note:** The Python package is `maylang_cli` (underscore) to avoid namespace conflicts. The PyPI name is `maylang-cli`. The CLI command is `may`.

[![CI](https://github.com/mayankkatulkar/maylang-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/mayankkatulkar/maylang-cli/actions)
[![PyPI](https://img.shields.io/pypi/v/maylang-cli)](https://pypi.org/project/maylang-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What Is a MayLang Change Package?

A `.may.md` file lives at `maylang/MC-<id>-<slug>.may.md` and contains:

```markdown
---
id: "MC-0001"
type: change
scope: fullstack
risk: low
owner: "team-alpha"
rollback: revert_commit
ai_used: false
---

# Intent

Add session caching to reduce auth latency by 40%.

# Contract

- Input: session token (JWT)
- Output: cached session object
- Side-effects: writes to Redis

# Invariants

1. Tokens are never stored in plain text.
2. Cache TTL ≤ session expiry.

# Patch

```diff
--- a/auth/sessions.py
+++ b/auth/sessions.py
@@ -12,6 +12,9 @@
 def get_session(token: str) -> Session:
-    return db.query(Session).filter_by(token=token).first()
+    cached = redis.get(f"sess:{token}")
+    if cached:
+        return Session.from_cache(cached)
+    session = db.query(Session).filter_by(token=token).first()
+    redis.setex(f"sess:{token}", session.ttl, session.to_cache())
+    return session
```

# Verification

- `pytest tests/test_sessions.py`
- `curl -H "Authorization: Bearer $TOKEN" localhost:8000/me`

# Debug Map

| Symptom | Likely cause | First file to check |
|---------|-------------|---------------------|
| 401 after deploy | Cache not warmed | auth/sessions.py |
| Stale session data | TTL mismatch | config/redis.yml |
```

### Required Frontmatter Keys

`id`, `type`, `scope`, `risk`, `owner`, `rollback`, `ai_used`

### Required Headings (in order)

1. `# Intent`
2. `# Contract`
3. `# Invariants`
4. `# Patch`
5. `# Verification` — must contain at least one runnable command
6. `# Debug Map`

---

## Installation

```bash
# Recommended (isolated install)
pipx install maylang-cli

# Or with pip
pip install maylang-cli
```

For development:

```bash
git clone https://github.com/mayankkatulkar/maylang-cli.git
cd maylang-cli
pip install -e ".[dev]"
```

---

## Usage

### Create a New Change Package

```bash
may new \
  --id MC-0001 \
  --slug auth-sessions \
  --scope fullstack \
  --risk low \
  --owner "team-alpha" \
  --rollback revert_commit
```

This creates `maylang/MC-0001-auth-sessions.may.md` from the built-in template.

### Validate Change Packages

```bash
# Always require at least one .may.md
may check

# Same as above (explicit)
may check --require always

# Only require when files in specific paths changed
may check --require changed --base origin/main --paths auth/,payments/,db/migrations/
```

#### Exit Codes

| Code | Meaning |
|------|---------|
| `0`  | All checks passed |
| `2`  | Missing required MayLang file |
| `3`  | Validation error (bad frontmatter, wrong headings, etc.) |

#### Enforce Diff Block

By default, the Patch section is not strictly validated for a `diff` block. To require one:

```bash
may check --enforce-diff
```

### Bump Version

```bash
# Bump patch version (0.1.0 → 0.1.1)
may version --bump patch

# Bump minor version (0.1.0 → 0.2.0)
may version --bump minor

# Bump major version (0.1.0 → 1.0.0)
may version --bump major
```

This updates the `version` field in your `pyproject.toml`.

---

## Project Structure

```
maylang-cli/
├── maylang_cli/
│   ├── __init__.py      # Package marker
│   ├── _version.py      # Version via importlib.metadata
│   ├── bumper.py        # Version bump helper
│   ├── cli.py           # Argparse CLI (entrypoint: may)
│   ├── checker.py       # High-level check orchestration
│   ├── parser.py        # .may.md parsing & validation
│   └── template.py      # Built-in template for `may new`
├── tests/
│   ├── test_check_required.py
│   ├── test_frontmatter.py
│   ├── test_headings_order.py
│   ├── test_verification.py
│   ├── test_enforce_diff.py
│   └── test_version_bump.py
├── .github/workflows/ci.yml
├── .gitignore
├── LICENSE
├── README.md
└── pyproject.toml
```

---

## Company Adoption Guide

### Why Adopt MayLang?

- **AI Accountability** — Every AI-assisted change has a human-readable spec.
- **Cross-team Clarity** — Backend, frontend, and infra teams share one format.
- **Audit Trail** — Change packages live in git; they're versioned and reviewable.
- **CI-enforceable** — Block PRs that lack proper documentation.

### Step-by-Step

1. **Install:** `pip install maylang-cli` in your CI environment.
2. **Create a change package** for every meaningful PR:
   ```bash
   may new --id MC-0001 --slug add-rate-limiter --scope backend --risk medium --owner "platform-team"
   ```
3. **Fill in the template** — document intent, contract, invariants, patch, verification steps, and debug map.
4. **Add CI enforcement** (see below).
5. **Review `.may.md` files in PR reviews** just like code.

### Suggested Team Conventions

| Decision | Recommendation |
|----------|---------------|
| When to require | Use `--require changed --paths` for gradual adoption |
| ID format | `MC-NNNN` (monotonically increasing) |
| Who writes it | The PR author, reviewed by the team |
| AI changes | Set `ai_used: true` in frontmatter |
| Rollback | Always specify a concrete rollback strategy |

---

## Company Adoption: CI Snippet

```bash
# In your CI pipeline:
pipx install maylang-cli
may check --require changed --base origin/main --paths auth/,payments/,db/migrations/
```

Or as a GitHub Actions step:

```yaml
name: MayLang Check

on:
  pull_request:
    branches: [main]

jobs:
  maylang:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install maylang-cli

      - name: Validate MayLang Change Packages
        run: may check --require changed --base origin/main --paths auth/,payments/,db/migrations/
```

For repos that want to enforce MayLang on **every** PR:

```yaml
      - run: may check --require always
```

To also enforce diff blocks in the Patch section:

```yaml
      - run: may check --require always --enforce-diff
```

---

## Manual PyPI Release (Option A)

```bash
# 1. Install build tools
python -m pip install -U build twine

# 2. Build wheel + sdist
python -m build

# 3. Upload to TestPyPI first
python -m twine upload --repository testpypi dist/*

# 4. Verify in a fresh venv
python -m venv /tmp/test-maylang && . /tmp/test-maylang/bin/activate
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ maylang-cli
may --version
deactivate && rm -rf /tmp/test-maylang

# 5. Upload to production PyPI
python -m twine upload dist/*

# 6. Install from PyPI
pipx install maylang-cli
```

See [docs/RELEASING.md](docs/RELEASING.md) for the full release checklist.

---

## License

[MIT](LICENSE)
