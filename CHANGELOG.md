# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-07

### Added

- **`may new`** command — scaffold a MayLang Change Package (`.may.md`) from a built-in template.
- **`may check`** command — validate `.may.md` files against the MayLang spec.
  - `--require always` — require at least one change package in every run.
  - `--require changed --base <ref> --paths <prefixes>` — require only when relevant files changed.
  - `--enforce-diff` — require a fenced `` ```diff `` block or `Link:` reference in the Patch section.
- **`may version --bump patch|minor|major`** — bump the version in `pyproject.toml`.
- YAML frontmatter validation (7 required keys: `id`, `type`, `scope`, `risk`, `owner`, `rollback`, `ai_used`).
- Required heading order enforcement (`Intent` → `Contract` → `Invariants` → `Patch` → `Verification` → `Debug Map`).
- Verification section validation (must contain at least one runnable command).
- Structured, grouped error output (by file, then by category).
- Git changed-files detection with detached HEAD fallback.
- Exit codes: `0` (ok), `2` (missing required), `3` (validation error).
- Verification scripts: `scripts/verify_local.sh`, `scripts/verify_wheel.sh`, `scripts/smoke_company_repo.sh`.
- GitHub Actions CI with Python 3.10–3.13 matrix, plus `verify-local` and `verify-wheel` jobs.

[0.1.0]: https://github.com/mayankkatulkar/maylang-cli/releases/tag/v0.1.0
