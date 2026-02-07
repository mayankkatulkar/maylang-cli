# Releasing maylang-cli

This document describes how to publish a new version of `maylang-cli` to PyPI
using the **manual** workflow (Option A: build + twine).

---

## Pre-release Checklist

- [ ] All tests pass: `pytest -v`
- [ ] Linter is clean: `ruff check .`
- [ ] Verification scripts pass:
  - `bash scripts/verify_local.sh`
  - `bash scripts/verify_wheel.sh`
  - `bash scripts/smoke_company_repo.sh`
- [ ] `CHANGELOG.md` has an entry for the new version.
- [ ] CI is green on the `main` branch.

---

## Release Steps

### 1. Bump the version

```bash
may version --bump patch   # or minor / major
```

This updates the `version` field in `pyproject.toml`.  Commit the change:

```bash
git add pyproject.toml
git commit -m "release: v0.X.Y"
```

### 2. Run verification scripts

```bash
bash scripts/verify_local.sh
bash scripts/verify_wheel.sh
bash scripts/smoke_company_repo.sh
```

All three must pass before proceeding.

### 3. Build the distribution

```bash
python -m pip install -U build twine
python -m build
```

This creates `dist/maylang_cli-<version>.tar.gz` and `dist/maylang_cli-<version>-py3-none-any.whl`.

### 4. Upload to TestPyPI

```bash
python -m twine upload --repository testpypi dist/*
```

### 5. Verify the TestPyPI install

```bash
python -m venv /tmp/test-maylang
. /tmp/test-maylang/bin/activate
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            maylang-cli
may --version
may --help
deactivate
rm -rf /tmp/test-maylang
```

### 6. Upload to production PyPI

```bash
python -m twine upload dist/*
```

### 7. Tag the release

```bash
git tag v0.X.Y
git push origin v0.X.Y
```

### 8. Create a GitHub Release

Go to https://github.com/mayankkatulkar/maylang-cli/releases/new, select the
tag, paste the relevant `CHANGELOG.md` entry, and publish.

---

## Post-release

```bash
pipx install maylang-cli        # verify public install
may --version                    # should show the new version
```

Clean up build artifacts:

```bash
rm -rf dist/ build/ *.egg-info .venv-verify .venv-wheel
```
