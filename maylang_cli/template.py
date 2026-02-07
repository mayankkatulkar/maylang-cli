"""Internal template for MayLang Change Package (.may.md) files.

Part of the ``maylang_cli`` package (PyPI: maylang-cli).
"""

from __future__ import annotations

TEMPLATE = """\
---
id: "{id}"
type: change
scope: "{scope}"
risk: "{risk}"
owner: "{owner}"
rollback: "{rollback}"
ai_used: false
---

# Intent

_Describe **why** this change exists in one or two sentences._

# Contract

_What does this change promise to the rest of the system?_

- Input: …
- Output: …
- Side-effects: …

# Invariants

_List properties that must remain true before **and** after this change._

1. …

# Patch

```diff
# Paste or link your diff here
```

# Verification

_At least one runnable command that proves correctness._

- `pytest tests/`

# Debug Map

_If something breaks, where should an engineer look first?_

| Symptom | Likely cause | First file to check |
|---------|-------------|---------------------|
| …       | …           | …                   |
"""


def render(
    *,
    id: str,
    slug: str,
    scope: str,
    risk: str,
    owner: str,
    rollback: str,
) -> str:
    """Return a fully-rendered MayLang Change Package as a string."""
    return TEMPLATE.format(
        id=id,
        slug=slug,
        scope=scope,
        risk=risk,
        owner=owner,
        rollback=rollback,
    )
