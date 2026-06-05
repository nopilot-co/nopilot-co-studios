"""planner — composite-document planning + assembly for the studios root plugin.

Deterministic glue for the ``planner`` orchestration skill: it scaffolds a
multi-section *composition* over an **in-place production docket**, tracks each
section's completion status, and merges the approved sections into one
``source.md`` for the design studio to render. LLM-driven judgment (which
sections, ordering, research, briefs, synthesis) lives in
``skills/planner/SKILL.md``; this package handles file ops, the ``composition.json``
manifest, validation, and the deterministic merge — no judgment here.

The planner is **not** a maker studio: it never renders. It plans + assembles,
then the Producer chains the merged ``source.md`` to the design studio's
``render-asset`` capability (``studio session init`` → ``studio render``).
"""

from __future__ import annotations

from pathlib import Path

__version__ = "0.1.2"

PACKAGE_ROOT = Path(__file__).resolve().parent
SCHEMAS = PACKAGE_ROOT / "schemas"

# Shared, studios-level reader-model store produced by the audience studio
# (parallel to the brand store). A composition can be bound to a reader by slug.
AUDIENCE_STORE = Path.home() / "context" / "studios" / "audience"


def audience_model_path(root: Path, slug: str) -> Path | None:
    """Resolve a reader model's ``_audience.yml`` for ``slug``, or None.

    Checks the docket-local store first (``<root>/audience/<slug>/`` — when the
    docket carries its own reader, like it carries its own brand), then the shared
    studios-level store (``~/context/studios/audience/<slug>/``). The reader model
    is an *optional* produce-time input: the planner warns rather than fails when a
    named slug doesn't resolve.
    """
    for base in (root / "audience" / slug, AUDIENCE_STORE / slug):
        p = base / "_audience.yml"
        if p.is_file():
            return p
    return None
