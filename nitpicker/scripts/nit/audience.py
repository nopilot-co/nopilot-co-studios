"""Resolve + project an audience-studio reader model into a review session.

The audience studio owns the structured reader model
(``~/context/studios/audience/<slug>/_audience.yml`` — or ``<docket>/audience/<slug>/``
inside a production docket). When ``nit new --audience <slug>`` is given, we render
that model into the session's ``inputs/icp.md`` so the existing ``audience-fit``
skill consumes one shared reader model instead of a freetext stub. Read-only — the
audience studio owns the model; this only resolves, loads, and projects it.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from . import AUDIENCE_ROOT

AUDIENCE_FILE = "_audience.yml"


def model_path(slug: str) -> Path | None:
    """Resolve a reader model's ``_audience.yml``, or None. Docket-local first
    (``$STUDIOS_DOCKET_ROOT/audience/<slug>/``), then the shared studios store."""
    bases = []
    docket = os.environ.get("STUDIOS_DOCKET_ROOT")
    if docket:
        bases.append(Path(docket).expanduser() / "audience" / slug)
    bases.append(AUDIENCE_ROOT / slug)
    for base in bases:
        p = base / AUDIENCE_FILE
        if p.is_file():
            return p
    return None


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


# ----------------------------------------------------------------- projection
def _bullets(items, fmt=str) -> list[str]:
    out = []
    for it in items or []:
        out.append(f"- {fmt(it)}")
    return out


def render_icp(model: dict) -> str:
    """Project a structured reader model into a readable ICP markdown document the
    ``audience-fit`` skill judges against (same role as a freetext ``icp.md``)."""
    slug = model.get("audience", "?")
    name = model.get("name", slug)
    status = model.get("status", "")
    persona = model.get("persona") or {}
    need = model.get("need_state") or {}
    comms = model.get("communication") or {}
    psy = model.get("psychographics") or {}

    lines: list[str] = [
        f"# Reader / ICP — {name}",
        "",
        f"> Projected from the audience studio reader model `{slug}`"
        + (f" (status: {status})" if status else "")
        + ". Source of truth is `_audience.yml`; do not hand-edit this projection.",
        "",
    ]

    # Persona
    persona_bits = [
        f"**{k.replace('_', ' ').title()}:** {v}"
        for k, v in (
            ("role", persona.get("role")),
            ("seniority", persona.get("seniority")),
            ("org_context", persona.get("org_context")),
            ("one_line", persona.get("one_line")),
        )
        if v
    ]
    if persona_bits or model.get("segment"):
        lines.append("## Who they are")
        if model.get("segment"):
            lines.append(f"**Segment:** {model['segment']}")
        lines += persona_bits
        lines.append("")

    # Need-state — the heart of audience-fit
    if need:
        lines.append("## Need-state")
        if need.get("stage"):
            lines.append(f"**Stage:** {need['stage']}")
        if need.get("needs"):
            lines.append("\n**Needs (priority):**")
            for n in need["needs"]:
                lines.append(
                    f"- **{n.get('id', '?')}** ({n.get('priority', '?')}): "
                    f"{n.get('statement', '')}"
                )
        for key in ("challenges", "objectives", "pains", "decision_factors"):
            if need.get(key):
                lines.append(f"\n**{key.replace('_', ' ').title()}:**")
                lines += _bullets(need[key])
        if need.get("objections"):
            lines.append("\n**Objections (and the counter they need):**")
            for o in need["objections"]:
                counter = o.get("counter_needed")
                lines.append(
                    f"- {o.get('objection', '')}"
                    + (f" → needs: {counter}" if counter else "")
                )
        lines.append("")

    # Psychographics
    if psy:
        lines.append("## How they think")
        for key in ("values", "motivations"):
            if psy.get(key):
                lines.append(f"**{key.title()}:** {', '.join(map(str, psy[key]))}")
        if psy.get("attitudes"):
            lines.append("**Attitudes:**")
            lines += _bullets(
                psy["attitudes"],
                lambda a: f"{a.get('stance', a)}"
                + (
                    f" ({a['strength']})"
                    if isinstance(a, dict) and a.get("strength")
                    else ""
                ),
            )
        if psy.get("approach"):
            lines.append(f"**Approach:** {psy['approach']}")
        lines.append("")

    # Communication preferences — directly feeds linguistic/tone fit
    if comms:
        lines.append("## How to speak to them")
        for key in (
            "register",
            "reading_level",
            "preferred_evidence",
            "avoid",
            "channels",
        ):
            v = comms.get(key)
            if not v:
                continue
            v_str = ", ".join(map(str, v)) if isinstance(v, list) else str(v)
            lines.append(f"**{key.replace('_', ' ').title()}:** {v_str}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
