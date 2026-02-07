"""Parse and validate MayLang Change Package (.may.md) files.

Responsibilities
----------------
* Extract YAML frontmatter.
* Extract Markdown headings in document order.
* Validate required frontmatter keys.
* Validate required headings and their order.
* Validate that the Verification section contains at least one runnable
  command line.
* Optionally enforce a ``diff`` fenced block in the Patch section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# ── Constants ────────────────────────────────────────────────────────────────

REQUIRED_FRONTMATTER_KEYS = frozenset(
    {"id", "type", "scope", "risk", "owner", "rollback", "ai_used"}
)

REQUIRED_HEADINGS = [
    "Intent",
    "Contract",
    "Invariants",
    "Patch",
    "Verification",
    "Debug Map",
]

# Regex helpers
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---", re.DOTALL)
_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
# A "runnable command" is either a `- ` list item containing a backtick
# command, or any fenced code line.  We keep it deliberately simple.
_RUNNABLE_CMD_RE = re.compile(
    r"(^- `.+`$)|(^- .+$)|(^```)",
    re.MULTILINE,
)
# Matches a ```diff fenced block or a "Link:" line in the Patch section.
_DIFF_BLOCK_RE = re.compile(r"(^```diff)|(^Link:)", re.MULTILINE)


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class ValidationError:
    """A single validation failure."""

    file: str
    message: str
    category: str = "general"

    def __str__(self) -> str:
        return f"{self.file}: {self.message}"


@dataclass
class ParseResult:
    """Result of parsing a single .may.md file."""

    path: str
    frontmatter: dict = field(default_factory=dict)
    headings: list[str] = field(default_factory=list)
    body: str = ""
    errors: list[ValidationError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


# ── Parsing helpers ──────────────────────────────────────────────────────────


def _extract_frontmatter(text: str, path: str) -> tuple[dict | None, list[ValidationError]]:
    """Return parsed YAML frontmatter dict and any errors."""
    errors: list[ValidationError] = []
    match = _FRONTMATTER_RE.search(text)
    if not match:
        errors.append(
            ValidationError(path, "Missing YAML frontmatter (--- delimiters).", "frontmatter")
        )
        return None, errors
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        errors.append(
            ValidationError(path, f"Invalid YAML in frontmatter: {exc}", "frontmatter")
        )
        return None, errors
    if not isinstance(data, dict):
        errors.append(
            ValidationError(path, "Frontmatter must be a YAML mapping.", "frontmatter")
        )
        return None, errors
    return data, errors


def _validate_frontmatter_keys(data: dict, path: str) -> list[ValidationError]:
    """Ensure all required keys are present."""
    missing = sorted(REQUIRED_FRONTMATTER_KEYS - set(data.keys()))
    if missing:
        return [
            ValidationError(
                path,
                f"Missing required frontmatter key: {key}",
                "frontmatter",
            )
            for key in missing
        ]
    return []


def _extract_headings(text: str) -> list[str]:
    """Return top-level (``# …``) headings in document order."""
    return _HEADING_RE.findall(text)


def _validate_headings(headings: list[str], path: str) -> list[ValidationError]:
    """Validate required headings exist and appear in the correct order."""
    errors: list[ValidationError] = []
    remaining = list(REQUIRED_HEADINGS)
    for heading in headings:
        if remaining and heading.strip() == remaining[0]:
            remaining.pop(0)
    if remaining:
        for h in remaining:
            errors.append(
                ValidationError(
                    path,
                    f"Missing or out-of-order heading: '# {h}'",
                    "heading",
                )
            )
    return errors


def _section_text(body: str, heading: str) -> str:
    """Return the text between ``# <heading>`` and the next ``# `` heading."""
    pattern = re.compile(
        rf"^#\s+{re.escape(heading)}\s*\n(.*?)(?=^#\s+|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    match = pattern.search(body)
    return match.group(1) if match else ""


def _validate_verification(body: str, path: str) -> list[ValidationError]:
    """Ensure the Verification section has at least one runnable command."""
    section = _section_text(body, "Verification")
    if not section.strip():
        return [ValidationError(path, "Verification section is empty.", "verification")]
    if not _RUNNABLE_CMD_RE.search(section):
        return [
            ValidationError(
                path,
                "Verification section must contain at least one runnable command "
                "(a list item starting with '- ' or a fenced code block).",
                "verification",
            )
        ]
    return []


def _validate_patch_diff(body: str, path: str) -> list[ValidationError]:
    """Ensure the Patch section contains a ```diff block or a Link: line."""
    section = _section_text(body, "Patch")
    if not section.strip():
        return [ValidationError(path, "Patch section is empty.", "patch")]
    if not _DIFF_BLOCK_RE.search(section):
        return [
            ValidationError(
                path,
                "Patch section must contain a ```diff fenced block or a 'Link:' reference "
                "(enable with --enforce-diff).",
                "patch",
            )
        ]
    return []


# ── Public API ───────────────────────────────────────────────────────────────


def parse_file(
    filepath: str | Path,
    *,
    enforce_diff: bool = False,
) -> ParseResult:
    """Parse and validate a single ``.may.md`` file.

    Parameters
    ----------
    filepath : str | Path
        Path to the ``.may.md`` file.
    enforce_diff : bool
        When *True*, require a ``diff`` fenced block in the Patch section.

    Returns a ``ParseResult`` with any validation errors collected in
    ``result.errors``.
    """
    filepath = Path(filepath)
    result = ParseResult(path=str(filepath))

    try:
        text = filepath.read_text(encoding="utf-8")
    except OSError as exc:
        result.errors.append(ValidationError(str(filepath), f"Cannot read file: {exc}"))
        return result

    result.body = text

    # 1. Frontmatter
    fm, fm_errors = _extract_frontmatter(text, str(filepath))
    result.errors.extend(fm_errors)
    if fm is not None:
        result.frontmatter = fm
        result.errors.extend(_validate_frontmatter_keys(fm, str(filepath)))

    # 2. Headings
    result.headings = _extract_headings(text)
    result.errors.extend(_validate_headings(result.headings, str(filepath)))

    # 3. Verification section
    result.errors.extend(_validate_verification(text, str(filepath)))

    # 4. Patch diff (optional enforcement)
    if enforce_diff:
        result.errors.extend(_validate_patch_diff(text, str(filepath)))

    return result
