"""Command-line interface for MayLang (``may`` command).

Usage examples::

    may new --id MC-0001 --slug auth-sessions --scope fullstack --risk low --owner "team"
    may check --require always
    may check --require changed --base origin/main --paths auth/,payments/
    may version --bump patch
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from maylang_cli._version import __version__
from maylang_cli.bumper import bump
from maylang_cli.checker import run_check
from maylang_cli.template import render

# ── Subcommand handlers ─────────────────────────────────────────────────────


def _handle_new(args: argparse.Namespace) -> int:
    """Create a new MayLang Change Package file."""
    filename = f"{args.id}-{args.slug}.may.md"
    target_dir = Path("maylang")
    target_dir.mkdir(exist_ok=True)
    target = target_dir / filename

    if target.exists():
        print(f"ERROR: {target} already exists.", file=sys.stderr)
        return 1

    rollback = args.rollback or "revert_commit"

    content = render(
        id=args.id,
        slug=args.slug,
        scope=args.scope,
        risk=args.risk,
        owner=args.owner,
        rollback=rollback,
    )

    target.write_text(content, encoding="utf-8")
    print(f"Created {target}")
    return 0


def _handle_check(args: argparse.Namespace) -> int:
    """Validate MayLang Change Package(s)."""
    paths = None
    if args.paths:
        paths = [p.strip() for p in args.paths.split(",") if p.strip()]

    return run_check(
        require=args.require,
        base=args.base,
        paths=paths,
        enforce_diff=args.enforce_diff,
    )


def _handle_version_bump(args: argparse.Namespace) -> int:
    """Bump version in pyproject.toml."""
    return bump(args.bump)


# ── Argument parser ─────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="may",
        description=f"MayLang – Explainable Change Standard CLI (v{__version__})",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── may new ──────────────────────────────────────────────────────────
    new_parser = subparsers.add_parser(
        "new",
        help="Create a new MayLang Change Package (.may.md)",
    )
    new_parser.add_argument("--id", required=True, help='Change ID, e.g. "MC-0001"')
    new_parser.add_argument("--slug", required=True, help='Short slug, e.g. "auth-sessions"')
    new_parser.add_argument(
        "--scope",
        required=True,
        help='Scope of the change, e.g. "backend", "fullstack"',
    )
    new_parser.add_argument(
        "--risk",
        required=True,
        choices=["low", "medium", "high", "critical"],
        help="Risk level",
    )
    new_parser.add_argument("--owner", required=True, help="Team or person responsible")
    new_parser.add_argument(
        "--rollback",
        default=None,
        help='Rollback strategy (default: "revert_commit")',
    )
    new_parser.set_defaults(func=_handle_new)

    # ── may check ────────────────────────────────────────────────────────
    check_parser = subparsers.add_parser(
        "check",
        help="Validate MayLang Change Packages",
    )
    check_parser.add_argument(
        "--require",
        choices=["always", "changed"],
        default="always",
        help='When to require MayLang files (default: "always")',
    )
    check_parser.add_argument(
        "--base",
        default=None,
        help="Git base ref for change detection, e.g. origin/main",
    )
    check_parser.add_argument(
        "--paths",
        default=None,
        help="Comma-separated path prefixes that trigger the requirement",
    )
    check_parser.add_argument(
        "--enforce-diff",
        action="store_true",
        default=False,
        help="Require a ```diff fenced block in the Patch section",
    )
    check_parser.set_defaults(func=_handle_check)

    # ── may version ──────────────────────────────────────────────────────
    version_parser = subparsers.add_parser(
        "version",
        help="Manage project version",
    )
    version_parser.add_argument(
        "--bump",
        required=True,
        choices=["patch", "minor", "major"],
        help="Bump the version in pyproject.toml (patch, minor, or major)",
    )
    version_parser.set_defaults(func=_handle_version_bump)

    return parser


# ── Entrypoint ───────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint (installed as ``may``)."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    exit_code = args.func(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
