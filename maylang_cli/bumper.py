"""Version bump helper for ``may version --bump``."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_VERSION_RE = re.compile(r'^(version\s*=\s*")(\d+\.\d+\.\d+)(")', re.MULTILINE)


def _find_pyproject(start: Path | None = None) -> Path | None:
    """Walk up from *start* (default: cwd) to find ``pyproject.toml``."""
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        candidate = parent / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def bump(part: str, *, pyproject_path: Path | None = None) -> int:
    """Bump the version in ``pyproject.toml``.

    Parameters
    ----------
    part : str
        One of ``"patch"``, ``"minor"``, ``"major"``.
    pyproject_path : Path | None
        Explicit path; if *None* we search upward from cwd.

    Returns
    -------
    int
        Exit code (0 = success, 1 = error).
    """
    path = pyproject_path or _find_pyproject()
    if path is None or not path.is_file():
        print("ERROR: Could not find pyproject.toml.", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")
    match = _VERSION_RE.search(text)
    if not match:
        print("ERROR: No version = \"x.y.z\" found in pyproject.toml.", file=sys.stderr)
        return 1

    old_version = match.group(2)
    parts = [int(x) for x in old_version.split(".")]

    if part == "major":
        parts = [parts[0] + 1, 0, 0]
    elif part == "minor":
        parts = [parts[0], parts[1] + 1, 0]
    elif part == "patch":
        parts = [parts[0], parts[1], parts[2] + 1]
    else:
        print(f"ERROR: Unknown bump part '{part}'. Use patch, minor, or major.", file=sys.stderr)
        return 1

    new_version = ".".join(str(p) for p in parts)
    new_text = _VERSION_RE.sub(rf"\g<1>{new_version}\3", text, count=1)
    path.write_text(new_text, encoding="utf-8")

    print(f"Bumped version: {old_version} → {new_version}  ({path})")
    return 0
