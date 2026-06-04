"""planner — composite-document planning + assembly for the studios root plugin.

Deterministic glue for the ``planner`` orchestration skill: it scaffolds a
multi-section *composition* over an **in-place production docket**, tracks each
section's completion status, and merges the approved sections into one
``source.md`` for the design studio to render. LLM-driven judgment (which
sections, ordering, research, briefs, synthesis) lives in
``skills/planner/SKILL.md``; this package handles file ops, the ``composition.json``
manifest, validation, and the deterministic merge — no judgment here.

The planner is **not** a maker studio: it never renders. It plans + assembles,
then the creative-director chains the merged ``source.md`` to the design studio's
``render-asset`` capability (``studio session init`` → ``studio render``).
"""

from __future__ import annotations

from pathlib import Path

__version__ = "0.1.0"

PACKAGE_ROOT = Path(__file__).resolve().parent
SCHEMAS = PACKAGE_ROOT / "schemas"
