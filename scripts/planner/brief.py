"""Scaffold a section's brief + content files.

A *discrete brief* is what lets a section be composed independently — by a person,
another skill, or a studio. ``write_brief`` drops a focused brief template at
``sections/<id>/brief.md`` and an empty ``sections/<id>/content.md`` for the draft
to land in. The judgment (what the brief actually says) is the planner skill's;
this module only owns the file scaffolding.
"""

from __future__ import annotations

from pathlib import Path

_BRIEF_TEMPLATE = """\
# Brief — {title}

> Discrete brief for one section of: **{objective}**
> Brand: `{brand}`  ·  Section: `{section_id}`  ·  Target format: `{fmt}`

## Purpose
_What this section must achieve for the reader, and how it serves the overall
document objective._

## Key messages
- _…_

## Required content
- _…_

## Data sources
_csv / md / image inputs this section draws on (also recorded in composition.json
via `planner data add`)._
- _…_

## Visualisation
_If a chart helps, what does it show? (Recorded via `planner viz set`; the design
studio renders it.)_

## Tone of voice
_Brand voice notes for this section (see the brand's tone-of-voice)._

## Reference / best practice
_What "good" looks like for this kind of section._
"""

_CONTENT_STUB = "<!-- {title} — composed content lands here (status: drafted). -->\n"


def write_brief(
    root: Path,
    *,
    section_id: str,
    title: str,
    objective: str,
    brand: str,
    fmt: str,
) -> tuple[Path, Path]:
    """Write ``sections/<id>/brief.md`` (always) and ``content.md`` (if absent).

    Returns ``(brief_path, content_path)``. The brief is rewritten each call so an
    updated title/objective is reflected; existing composed content is never
    overwritten.
    """
    sec_dir = root / "sections" / section_id
    sec_dir.mkdir(parents=True, exist_ok=True)

    brief_path = sec_dir / "brief.md"
    brief_path.write_text(
        _BRIEF_TEMPLATE.format(
            title=title,
            objective=objective,
            brand=brand,
            section_id=section_id,
            fmt=fmt,
        )
    )

    content_path = sec_dir / "content.md"
    if not content_path.exists():
        content_path.write_text(_CONTENT_STUB.format(title=title))

    return brief_path, content_path
