"""High-level checker logic for ``may check``.

Orchestrates file discovery, git-diff integration, and per-file validation.
Provides structured, grouped error output.
"""

from __future__ import annotations

import glob
import subprocess
import sys
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from maylang_cli.parser import ParseResult, ValidationError, parse_file

# ── Exit codes ───────────────────────────────────────────────────────────────

EXIT_OK = 0
EXIT_MISSING = 2
EXIT_INVALID = 3


# ── Git helpers ──────────────────────────────────────────────────────────────


def _git_changed_files(base: str) -> tuple[list[str] | None, str | None]:
    """Return list of changed file paths relative to repo root.

    Uses ``git diff --name-only <base>...HEAD``.  Returns a tuple of
    ``(file_list, warning_message)``.  *file_list* is ``None`` when git
    is not available or the command fails; *warning_message* explains why.
    """
    # First, try the three-dot merge-base diff (works on branches).
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return (
            [line.strip() for line in result.stdout.splitlines() if line.strip()],
            None,
        )
    except FileNotFoundError:
        return None, "git is not installed or not on PATH."
    except subprocess.CalledProcessError as exc:
        # Detached HEAD or missing ref – fall back to two-dot diff.
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", base, "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return (
                [line.strip() for line in result.stdout.splitlines() if line.strip()],
                None,
            )
        except subprocess.CalledProcessError:
            stderr = exc.stderr.strip() if exc.stderr else "unknown error"
            return None, f"git diff failed: {stderr}"


# ── Discovery ────────────────────────────────────────────────────────────────


def discover_maylang_files(root: str = ".") -> list[str]:
    """Glob for ``maylang/*.may.md`` under *root*."""
    pattern = str(Path(root) / "maylang" / "*.may.md")
    return sorted(glob.glob(pattern))


def _paths_match(changed_files: list[str], path_prefixes: list[str]) -> bool:
    """Return True if any changed file starts with one of *path_prefixes*.

    Files inside ``maylang/`` are excluded from matching.
    """
    for cf in changed_files:
        if cf.startswith("maylang/"):
            continue
        for prefix in path_prefixes:
            if cf.startswith(prefix):
                return True
    return False


# ── Pretty error output ─────────────────────────────────────────────────────


def _print_errors(all_errors: list[ValidationError]) -> None:
    """Print validation errors grouped by file with structured formatting."""
    grouped: dict[str, list[ValidationError]] = defaultdict(list)
    for err in all_errors:
        grouped[err.file].append(err)

    total = len(all_errors)
    file_count = len(grouped)
    print(
        f"\n✗ Validation failed: {total} error(s) in {file_count} file(s)\n",
        file=sys.stderr,
    )

    for filepath, errors in grouped.items():
        print(f"  ── {filepath} ──", file=sys.stderr)

        # Sub-group by category for readability
        by_cat: dict[str, list[ValidationError]] = defaultdict(list)
        for e in errors:
            by_cat[e.category].append(e)

        for cat, errs in by_cat.items():
            label = cat.capitalize()
            for e in errs:
                print(f"    ✗ [{label}] {e.message}", file=sys.stderr)

        print(file=sys.stderr)


# ── Main check routine ──────────────────────────────────────────────────────


def run_check(
    *,
    require: str = "always",
    base: str | None = None,
    paths: Sequence[str] | None = None,
    root: str = ".",
    enforce_diff: bool = False,
) -> int:
    """Execute the full ``may check`` pipeline.

    Parameters
    ----------
    require : str
        ``"always"`` – at least one ``.may.md`` must exist.
        ``"changed"`` – only require when relevant files changed.
    base : str | None
        Git ref to diff against (e.g. ``origin/main``).
    paths : sequence of str | None
        Path prefixes that trigger the requirement (used with
        ``--require=changed``).
    root : str
        Working directory / repo root.
    enforce_diff : bool
        When *True*, require a ``diff`` fenced block in the Patch section.

    Returns
    -------
    int
        Exit code: 0 = ok, 2 = missing required, 3 = validation failure.
    """
    maylang_files = discover_maylang_files(root)

    # ── Decide whether MayLang files are required ────────────────────────
    need_maylang = False

    if require == "always":
        need_maylang = True
    elif require == "changed":
        if base is not None:
            changed, warning = _git_changed_files(base)
            if changed is not None:
                prefixes = list(paths) if paths else []
                if prefixes:
                    need_maylang = _paths_match(changed, prefixes)
                else:
                    # No path filter → any non-maylang change triggers
                    non_ml = [f for f in changed if not f.startswith("maylang/")]
                    need_maylang = len(non_ml) > 0

                # When code changed under watched paths, also require that
                # at least one maylang/*.may.md was added/modified in the
                # same diff.  A stale file from a prior commit is not enough.
                if need_maylang:
                    maylang_in_diff = any(
                        f.startswith("maylang/") and f.endswith(".may.md")
                        for f in changed
                    )
                    if not maylang_in_diff:
                        print(
                            "\n✗ Code changed under watched paths, but no MayLang "
                            "change package was updated (maylang/*.may.md).\n"
                            "\n"
                            "  Run:\n"
                            "    may new --id MC-XXXX --slug my-change "
                            "--scope backend --risk low --owner 'your-team'\n"
                            "  and include it in this change.\n",
                            file=sys.stderr,
                        )
                        return EXIT_MISSING
            else:
                # git unavailable – warn and fall back to requiring
                print(
                    f"WARNING: Could not detect changed files ({warning}). "
                    "Falling back to requiring MayLang change packages.",
                    file=sys.stderr,
                )
                need_maylang = True
        else:
            # No base ref – cannot determine changes; require if files exist
            need_maylang = len(maylang_files) > 0

    # ── Check existence ──────────────────────────────────────────────────
    if need_maylang and not maylang_files:
        print(
            "\n✗ No MayLang change packages found in maylang/*.may.md.\n"
            "\n"
            "  Create one with:\n"
            "    may new --id MC-0001 --slug my-change "
            "--scope backend --risk low --owner 'your-team'\n",
            file=sys.stderr,
        )
        return EXIT_MISSING

    if not maylang_files:
        # Nothing to validate and not required.
        print("No MayLang files to validate – skipping.")
        return EXIT_OK

    # ── Validate each file ───────────────────────────────────────────────
    all_errors: list[ValidationError] = []
    for fpath in maylang_files:
        result: ParseResult = parse_file(fpath, enforce_diff=enforce_diff)
        all_errors.extend(result.errors)

    if all_errors:
        _print_errors(all_errors)
        return EXIT_INVALID

    print(f"✓ {len(maylang_files)} MayLang change package(s) validated successfully.")
    return EXIT_OK
