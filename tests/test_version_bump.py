"""Tests for ``may version --bump`` functionality."""

from __future__ import annotations

import textwrap
from pathlib import Path

from maylang_cli.bumper import bump

PYPROJECT_TEMPLATE = textwrap.dedent("""\
    [build-system]
    requires = ["setuptools>=68.0"]
    build-backend = "setuptools.build_meta"

    [project]
    name = "example"
    version = "{version}"
    description = "Test project"
""")


def _write_pyproject(tmp_path: Path, version: str = "0.1.0") -> Path:
    fp = tmp_path / "pyproject.toml"
    fp.write_text(PYPROJECT_TEMPLATE.format(version=version), encoding="utf-8")
    return fp


def _read_version(fp: Path) -> str:
    import re

    text = fp.read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*"(\d+\.\d+\.\d+)"', text)
    assert match, f"No version found in {fp}"
    return match.group(1)


# ── Tests ────────────────────────────────────────────────────────────────────


class TestBumpPatch:
    def test_patch_bump(self, tmp_path: Path) -> None:
        fp = _write_pyproject(tmp_path, "1.2.3")
        code = bump("patch", pyproject_path=fp)
        assert code == 0
        assert _read_version(fp) == "1.2.4"

    def test_patch_from_zero(self, tmp_path: Path) -> None:
        fp = _write_pyproject(tmp_path, "0.0.0")
        code = bump("patch", pyproject_path=fp)
        assert code == 0
        assert _read_version(fp) == "0.0.1"


class TestBumpMinor:
    def test_minor_bump(self, tmp_path: Path) -> None:
        fp = _write_pyproject(tmp_path, "1.2.3")
        code = bump("minor", pyproject_path=fp)
        assert code == 0
        assert _read_version(fp) == "1.3.0"

    def test_minor_resets_patch(self, tmp_path: Path) -> None:
        fp = _write_pyproject(tmp_path, "0.5.9")
        code = bump("minor", pyproject_path=fp)
        assert code == 0
        assert _read_version(fp) == "0.6.0"


class TestBumpMajor:
    def test_major_bump(self, tmp_path: Path) -> None:
        fp = _write_pyproject(tmp_path, "1.2.3")
        code = bump("major", pyproject_path=fp)
        assert code == 0
        assert _read_version(fp) == "2.0.0"

    def test_major_resets_minor_and_patch(self, tmp_path: Path) -> None:
        fp = _write_pyproject(tmp_path, "3.7.11")
        code = bump("major", pyproject_path=fp)
        assert code == 0
        assert _read_version(fp) == "4.0.0"


class TestBumpEdgeCases:
    def test_missing_pyproject(self, tmp_path: Path) -> None:
        """Bump should fail gracefully if pyproject.toml doesn't exist."""
        fake = tmp_path / "nonexistent" / "pyproject.toml"
        code = bump("patch", pyproject_path=fake)
        assert code == 1

    def test_no_version_field(self, tmp_path: Path) -> None:
        fp = tmp_path / "pyproject.toml"
        fp.write_text("[project]\nname = 'x'\n", encoding="utf-8")
        code = bump("patch", pyproject_path=fp)
        assert code == 1

    def test_invalid_part(self, tmp_path: Path) -> None:
        fp = _write_pyproject(tmp_path, "1.0.0")
        code = bump("mega", pyproject_path=fp)
        assert code == 1

    def test_preserves_other_content(self, tmp_path: Path) -> None:
        fp = _write_pyproject(tmp_path, "1.0.0")
        bump("patch", pyproject_path=fp)
        updated = fp.read_text(encoding="utf-8")
        # Only the version line should change
        assert 'name = "example"' in updated
        assert 'version = "1.0.1"' in updated
