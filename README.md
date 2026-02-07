# MayLang CLI

**Explainable Change Standard** — a minimal, universal spec that reduces AI tech debt across ANY language or repo.

MayLang is a lightweight convention: every meaningful change ships with a **Change Package** (`.may.md` file) that documents *intent*, *contract*, *invariants*, *patch*, *verification*, and *debug map* in a single, machine-readable Markdown file with YAML frontmatter.

`maylang-cli` is the tiny Python CLI that creates and validates these packages.

> **Import note:** The Python package is `maylang_cli` (underscore) to avoid namespace conflicts. The PyPI name is `maylang-cli`. The CLI command is `may`.

[![CI](https://github.com/maylang/maylang-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/maylang/maylang-cli/actions)
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

## Install

```bash
# Recommended
pipx install maylang-cli

# Or with pip
pip install maylang-cli
```

For development:

```bash
git clone https://github.com/maylang/maylang-cli.git
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

## How to Adopt in CI

Add this step to your GitHub Actions workflow:

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

## How to Adopt in CI

Add this step to your GitHub Actions workflow:

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
        run: may check --require changed --base origin/main --paths src/,db/migrations/
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

## Release to PyPI

### Manual Release

```bash
pip install build twine
python -m build
twine upload dist/*
```

### Trusted Publishing (Recommended)

Use [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) to eliminate API tokens entirely. Add this workflow:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

permissions:
  id-token: write  # Required for trusted publishing

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install build

      - run: python -m build

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

Configure the trusted publisher at https://pypi.org/manage/project/maylang-cli/settings/publishing/.

---

## License

[MIT](LICENSE)
