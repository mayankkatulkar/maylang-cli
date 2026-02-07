"""Tests for heading order validation."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from maylang_cli.parser import REQUIRED_HEADINGS, parse_file


def _write(tmp_path: Path, content: str, name: str = "MC-0001-test.may.md") -> Path:
    fp = tmp_path / name
    fp.write_text(content, encoding="utf-8")
    return fp


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

VERIFICATION_LINE = "- `pytest`"


def _make_body(headings: list[str]) -> str:
    """Build a minimal body from a list of heading names."""
    sections = []
    for h in headings:
        if h == "Verification":
            sections.append(f"# {h}\n\n{VERIFICATION_LINE}\n")
        elif h == "Patch":
            sections.append(f"# {h}\n\n```diff\n-a\n+b\n```\n")
        else:
            sections.append(f"# {h}\n\nContent.\n")
    return "\n".join(sections)


# ── Tests ────────────────────────────────────────────────────────────────────


class TestCorrectOrder:
    def test_all_headings_correct_order(self, tmp_path: Path) -> None:
        content = FRONTMATTER + "\n" + _make_body(REQUIRED_HEADINGS)
        fp = _write(tmp_path, content)
        result = parse_file(fp)
        assert result.ok, [str(e) for e in result.errors]


class TestMissingHeading:
    @pytest.mark.parametrize("removed", REQUIRED_HEADINGS)
    def test_each_heading_individually_required(
        self, tmp_path: Path, removed: str
    ) -> None:
        headings = [h for h in REQUIRED_HEADINGS if h != removed]
        content = FRONTMATTER + "\n" + _make_body(headings)
        fp = _write(tmp_path, content)
        result = parse_file(fp)
        assert not result.ok
        msgs = " ".join(e.message for e in result.errors)
        assert "Missing or out-of-order" in msgs or "Verification section" in msgs

    def test_missing_heading_errors_have_heading_category(self, tmp_path: Path) -> None:
        """Per-heading errors should have category='heading'."""
        headings = [h for h in REQUIRED_HEADINGS if h != "Contract"]
        content = FRONTMATTER + "\n" + _make_body(headings)
        fp = _write(tmp_path, content)
        result = parse_file(fp)
        heading_errors = [e for e in result.errors if e.category == "heading"]
        assert len(heading_errors) >= 1
        assert any("Contract" in e.message for e in heading_errors)


class TestWrongOrder:
    def test_swapped_headings_fail(self, tmp_path: Path) -> None:
        """Swap Intent and Contract – should fail."""
        wrong = list(REQUIRED_HEADINGS)
        wrong[0], wrong[1] = wrong[1], wrong[0]
        content = FRONTMATTER + "\n" + _make_body(wrong)
        fp = _write(tmp_path, content)
        result = parse_file(fp)
        assert not result.ok

    def test_reversed_order_fails(self, tmp_path: Path) -> None:
        content = FRONTMATTER + "\n" + _make_body(list(reversed(REQUIRED_HEADINGS)))
        fp = _write(tmp_path, content)
        result = parse_file(fp)
        assert not result.ok


class TestExtraHeadingsAllowed:
    def test_extra_headings_between_required(self, tmp_path: Path) -> None:
        """Extra headings should not cause failures as long as required order is kept."""
        headings = [
            "Intent",
            "Background",  # extra
            "Contract",
            "Invariants",
            "Patch",
            "Verification",
            "Debug Map",
            "Appendix",  # extra
        ]
        content = FRONTMATTER + "\n" + _make_body(headings)
        fp = _write(tmp_path, content)
        result = parse_file(fp)
        assert result.ok, [str(e) for e in result.errors]
