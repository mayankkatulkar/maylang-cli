"""Tests for ``may check --require`` behaviour (always vs changed)."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest import mock

from maylang_cli.checker import EXIT_MISSING, EXIT_OK, run_check

# ── Helpers ──────────────────────────────────────────────────────────────────

VALID_MAY_MD = textwrap.dedent("""\
    ---
    id: "MC-0001"
    type: change
    scope: backend
    risk: low
    owner: "team-alpha"
    rollback: revert_commit
    ai_used: false
    ---

    # Intent

    Add session caching.

    # Contract

    - Input: session token
    - Output: cached session object
    - Side-effects: none

    # Invariants

    1. Tokens are never stored in plain text.

    # Patch

    ```diff
    --- a/auth.py
    +++ b/auth.py
    @@ -1 +1 @@
    -old
    +new
    ```

    # Verification

    - `pytest tests/test_sessions.py`

    # Debug Map

    | Symptom | Likely cause | First file to check |
    |---------|-------------|---------------------|
    | 500     | cache miss  | auth.py             |
""")


def _write_valid(tmp_path: Path, name: str = "MC-0001-auth.may.md") -> None:
    ml_dir = tmp_path / "maylang"
    ml_dir.mkdir(exist_ok=True)
    (ml_dir / name).write_text(VALID_MAY_MD, encoding="utf-8")


# ── Tests ────────────────────────────────────────────────────────────────────


class TestRequireAlways:
    """``--require always`` must fail if no .may.md files exist."""

    def test_missing_files_returns_exit_missing(self, tmp_path: Path) -> None:
        code = run_check(require="always", root=str(tmp_path))
        assert code == EXIT_MISSING

    def test_valid_file_returns_ok(self, tmp_path: Path) -> None:
        _write_valid(tmp_path)
        code = run_check(require="always", root=str(tmp_path))
        assert code == EXIT_OK


class TestRequireChanged:
    """``--require changed`` should only require .may.md when relevant files changed."""

    def test_no_base_no_files_returns_ok(self, tmp_path: Path) -> None:
        """Without --base and no existing files, nothing is required."""
        code = run_check(require="changed", root=str(tmp_path))
        assert code == EXIT_OK

    def test_no_base_with_files_validates(self, tmp_path: Path) -> None:
        _write_valid(tmp_path)
        code = run_check(require="changed", root=str(tmp_path))
        assert code == EXIT_OK

    @mock.patch(
        "maylang_cli.checker._git_changed_files",
        return_value=(["auth/login.py"], None),
    )
    def test_changed_matching_paths_requires_maylang(
        self, mock_git: mock.MagicMock, tmp_path: Path
    ) -> None:
        """If changed files match --paths and no .may.md exists → EXIT_MISSING."""
        code = run_check(
            require="changed",
            base="origin/main",
            paths=["auth/"],
            root=str(tmp_path),
        )
        assert code == EXIT_MISSING

    @mock.patch(
        "maylang_cli.checker._git_changed_files",
        return_value=(["docs/readme.md"], None),
    )
    def test_changed_non_matching_paths_ok(
        self, mock_git: mock.MagicMock, tmp_path: Path
    ) -> None:
        """Changed files that don't match --paths → no requirement."""
        code = run_check(
            require="changed",
            base="origin/main",
            paths=["auth/", "payments/"],
            root=str(tmp_path),
        )
        assert code == EXIT_OK

    @mock.patch(
        "maylang_cli.checker._git_changed_files",
        return_value=(["auth/login.py"], None),
    )
    def test_changed_code_only_no_maylang_in_diff_returns_missing(
        self, mock_git: mock.MagicMock, tmp_path: Path
    ) -> None:
        """Code changed under watched paths but no maylang/*.may.md in diff → EXIT_MISSING.

        Even though a .may.md file exists on disk, it was not part of this change.
        """
        _write_valid(tmp_path)
        code = run_check(
            require="changed",
            base="origin/main",
            paths=["auth/"],
            root=str(tmp_path),
        )
        assert code == EXIT_MISSING

    @mock.patch(
        "maylang_cli.checker._git_changed_files",
        return_value=(["auth/login.py", "maylang/MC-0001-auth.may.md"], None),
    )
    def test_changed_matching_with_maylang_in_diff_ok(
        self, mock_git: mock.MagicMock, tmp_path: Path
    ) -> None:
        """Code changed AND maylang/*.may.md is in the diff → EXIT_OK."""
        _write_valid(tmp_path)
        code = run_check(
            require="changed",
            base="origin/main",
            paths=["auth/"],
            root=str(tmp_path),
        )
        assert code == EXIT_OK

    @mock.patch(
        "maylang_cli.checker._git_changed_files",
        return_value=(None, "git is not installed or not on PATH."),
    )
    def test_git_unavailable_fallback(
        self, mock_git: mock.MagicMock, tmp_path: Path
    ) -> None:
        """When git is unavailable, warn and fall back to requiring .may.md."""
        code = run_check(
            require="changed",
            base="origin/main",
            root=str(tmp_path),
        )
        assert code == EXIT_MISSING
