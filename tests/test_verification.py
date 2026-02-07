"""Tests for Verification section validation."""

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

BASE_HEADINGS_BEFORE = textwrap.dedent("""\

    # Intent

    Do something.

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

""")

BASE_HEADINGS_AFTER = textwrap.dedent("""\

    # Debug Map

    | Symptom | Cause | File |
    |---------|-------|------|
    | err     | bug   | x.py |
""")


def _write(tmp_path: Path, verification_body: str) -> Path:
    content = (
        FRONTMATTER
        + BASE_HEADINGS_BEFORE
        + "# Verification\n\n"
        + verification_body
        + "\n"
        + BASE_HEADINGS_AFTER
    )
    fp = tmp_path / "MC-0001-test.may.md"
    fp.write_text(content, encoding="utf-8")
    return fp


# ── Tests ────────────────────────────────────────────────────────────────────


class TestVerificationWithCommand:
    def test_list_item_with_backtick_command(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, "- `pytest tests/`\n")
        result = parse_file(fp)
        assert result.ok, [str(e) for e in result.errors]

    def test_plain_list_item(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, "- Run pytest tests/\n")
        result = parse_file(fp)
        assert result.ok, [str(e) for e in result.errors]

    def test_fenced_code_block(self, tmp_path: Path) -> None:
        block = "```bash\npytest tests/\n```\n"
        fp = _write(tmp_path, block)
        result = parse_file(fp)
        assert result.ok, [str(e) for e in result.errors]

    def test_multiple_commands(self, tmp_path: Path) -> None:
        body = "- `pytest tests/`\n- `ruff check .`\n"
        fp = _write(tmp_path, body)
        result = parse_file(fp)
        assert result.ok


class TestVerificationEmpty:
    def test_empty_section_fails(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, "")
        result = parse_file(fp)
        assert not result.ok
        msgs = [e.message for e in result.errors]
        assert any("Verification section" in m for m in msgs)

    def test_only_prose_fails(self, tmp_path: Path) -> None:
        fp = _write(tmp_path, "We should test this eventually.\n")
        result = parse_file(fp)
        assert not result.ok
        msgs = [e.message for e in result.errors]
        assert any("runnable command" in m for m in msgs)
