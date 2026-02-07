"""Tests for ``--enforce-diff`` flag on ``may check``."""

from __future__ import annotations

import textwrap
from pathlib import Path

from maylang_cli.parser import parse_file

FRONTMATTER = textwrap.dedent("""\
    ---
    id: "MC-0001"
    type: change
    scope: backend
    risk: low
    owner: "team"
    rollback: revert_commit
    ai_used: false
    ---
""")

BASE_BEFORE_PATCH = textwrap.dedent("""\

    # Intent

    Do something.

    # Contract

    - Input: x
    - Output: y
    - Side-effects: none

    # Invariants

    1. Always true.

""")

AFTER_PATCH = textwrap.dedent("""\

    # Verification

    - `pytest tests/`

    # Debug Map

    | Symptom | Cause | File |
    |---------|-------|------|
    | err     | bug   | x.py |
""")


def _write(tmp_path: Path, patch_body: str) -> Path:
    content = (
        FRONTMATTER
        + BASE_BEFORE_PATCH
        + "# Patch\n\n"
        + patch_body
        + "\n"
        + AFTER_PATCH
    )
    fp = tmp_path / "MC-0001-test.may.md"
    fp.write_text(content, encoding="utf-8")
    return fp


# ── Tests ────────────────────────────────────────────────────────────────────


class TestEnforceDiffEnabled:
    def test_diff_block_passes(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, "```diff\n-old\n+new\n```\n")
        result = parse_file(fp, enforce_diff=True)
        assert result.ok, [str(e) for e in result.errors]

    def test_link_reference_passes(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, "Link: https://github.com/org/repo/pull/42\n")
        result = parse_file(fp, enforce_diff=True)
        assert result.ok, [str(e) for e in result.errors]

    def test_prose_only_fails(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, "See the PR for the diff.\n")
        result = parse_file(fp, enforce_diff=True)
        assert not result.ok
        msgs = [e.message for e in result.errors]
        assert any("Patch section must contain" in m for m in msgs)

    def test_empty_patch_fails(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, "")
        result = parse_file(fp, enforce_diff=True)
        assert not result.ok
        msgs = [e.message for e in result.errors]
        assert any("Patch section" in m for m in msgs)

    def test_error_has_patch_category(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, "No diff here.\n")
        result = parse_file(fp, enforce_diff=True)
        patch_errors = [e for e in result.errors if e.category == "patch"]
        assert len(patch_errors) >= 1


class TestEnforceDiffDisabled:
    def test_prose_only_passes_without_flag(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, "See the PR for the diff.\n")
        result = parse_file(fp, enforce_diff=False)
        assert result.ok, [str(e) for e in result.errors]

    def test_empty_patch_passes_without_flag(self, tmp_path: Path) -> None:
        """Without --enforce-diff, empty Patch is not an error."""
        fp = _write(tmp_path, "")
        result = parse_file(fp, enforce_diff=False)
        assert result.ok, [str(e) for e in result.errors]
