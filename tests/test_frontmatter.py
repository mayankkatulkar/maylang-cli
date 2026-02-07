"""Tests for YAML frontmatter parsing and validation."""

from __future__ import annotations

import textwrap
from pathlib import Path

from maylang_cli.parser import REQUIRED_FRONTMATTER_KEYS, parse_file


def _write(tmp_path: Path, content: str, name: str = "MC-0001-test.may.md") -> Path:
    fp = tmp_path / name
    fp.write_text(content, encoding="utf-8")
    return fp


# ── Helpers: valid & invalid content ─────────────────────────────────────────

VALID_CONTENT = textwrap.dedent("""\
    ---
    id: "MC-0001"
    type: change
    scope: backend
    risk: low
    owner: "team"
    rollback: revert_commit
    ai_used: false
    ---

    # Intent

    Do things.

    # Contract

    - Input: x
    - Output: y
    - Side-effects: none

    # Invariants

    1. Always true.

    # Patch

    ```diff
    -old
    +new
    ```

    # Verification

    - `make test`

    # Debug Map

    | Symptom | Cause | File |
    |---------|-------|------|
    | err     | bug   | x.py |
""")

MISSING_KEYS_CONTENT = textwrap.dedent("""\
    ---
    id: "MC-0001"
    type: change
    ---

    # Intent

    Something.

    # Contract

    Details.

    # Invariants

    1. True.

    # Patch

    ```diff
    -a
    +b
    ```

    # Verification

    - `pytest`

    # Debug Map

    | S | C | F |
    |---|---|---|
    | x | y | z |
""")

NO_FRONTMATTER_CONTENT = textwrap.dedent("""\
    # Intent

    Something.

    # Contract

    Details.

    # Invariants

    1. True.

    # Patch

    Note: see PR diff.

    # Verification

    - `pytest`

    # Debug Map

    Info.
""")

INVALID_YAML_CONTENT = textwrap.dedent("""\
    ---
    id: "MC-0001
    bad: [yaml
    ---

    # Intent

    Something.
""")


# ── Tests ────────────────────────────────────────────────────────────────────


class TestFrontmatterValid:
    def test_all_keys_present(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, VALID_CONTENT)
        result = parse_file(fp)
        assert result.ok
        assert set(result.frontmatter.keys()) >= REQUIRED_FRONTMATTER_KEYS


class TestFrontmatterMissingKeys:
    def test_reports_missing_keys(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, MISSING_KEYS_CONTENT)
        result = parse_file(fp)
        assert not result.ok
        msgs = [e.message for e in result.errors]
        assert any("Missing required frontmatter key" in m for m in msgs)

    def test_lists_each_missing_key(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, MISSING_KEYS_CONTENT)
        result = parse_file(fp)
        error_text = " ".join(e.message for e in result.errors)
        for key in ("scope", "risk", "owner", "rollback", "ai_used"):
            assert key in error_text

    def test_per_key_error_has_frontmatter_category(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, MISSING_KEYS_CONTENT)
        result = parse_file(fp)
        fm_errors = [e for e in result.errors if e.category == "frontmatter"]
        assert len(fm_errors) >= 5  # one per missing key


class TestFrontmatterAbsent:
    def test_no_frontmatter_error(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, NO_FRONTMATTER_CONTENT)
        result = parse_file(fp)
        assert not result.ok
        msgs = [e.message for e in result.errors]
        assert any("Missing YAML frontmatter" in m for m in msgs)


class TestFrontmatterInvalidYAML:
    def test_invalid_yaml_error(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, INVALID_YAML_CONTENT)
        result = parse_file(fp)
        assert not result.ok
        msgs = [e.message for e in result.errors]
        assert any("Invalid YAML" in m for m in msgs)
