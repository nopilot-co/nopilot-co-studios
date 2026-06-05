"""Render diagrams via the design studio over the CLI boundary.

Mirror of ``audience/scripts/audience/nit_bridge.py`` and
``commercial/scripts/commercial/nit_bridge.py``. Keeps render math + brand
logic single-sourced in the design studio. We shell out to ``studio``
(design CLI) when present; degrades cleanly with an install hint otherwise.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def _design_binary() -> str | None:
    on_path = shutil.which("studio")
    if on_path:
        return on_path
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "design" / ".venv" / "bin" / "studio"
        if cand.is_file():
            return str(cand)
    return None


def reachable() -> bool:
    return _design_binary() is not None


def render(spec: dict, *, out_dir: Path, fmt: str = "pdf") -> Path | None:
    """Render a diagram from the architecture spec via the design studio.

    For v0.1.0 this writes a Mermaid-style source from the spec into
    ``<out_dir>/architecture.md`` and (when reachable) asks the design
    studio to render it. Returns the rendered path, or None when the
    design CLI isn't reachable (caller surfaces the install hint).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "architecture.md"
    md_path.write_text(_mermaid_source(spec))
    if not reachable():
        return None
    # The design studio's render-asset CLI is its single point of contact;
    # the engagement-side caller hands a Markdown source. We stop short of
    # actually invoking it for v0.1.0 — the contract surface and the
    # source file are the contract this PR owns. A follow-up will wire
    # the full handoff (`studio session init` + `studio render`).
    return md_path


def _mermaid_source(spec: dict) -> str:
    """Render the spec as a Mermaid flowchart (a deterministic preview).

    The design studio renders the final diagram; this is the source it
    consumes. Systems become nodes, flows become edges (labelled by
    payload + frequency), integrations are noted via edge labels.
    """
    lines = [
        "# Architecture — auto-generated from _architecture.yml",
        "",
        "```mermaid",
        "flowchart LR",
    ]
    for s in spec.get("systems") or []:
        sid = s.get("id") or "?"
        label = s.get("name") or sid
        lines.append(f'  {sid}["{label}"]')
    int_by_flow = {
        i.get("flow"): i for i in (spec.get("integrations") or []) if i.get("flow")
    }
    for f in spec.get("data_flows") or []:
        fid = f.get("id") or "?"
        a = f.get("from")
        b = f.get("to")
        if not (a and b):
            continue
        arrow = "<-->" if f.get("direction") == "bidirectional" else "-->"
        payload = f.get("payload", "")
        freq = f.get("frequency", "")
        edge = f"{fid}"
        if payload:
            edge += f" {payload}"
        if freq:
            edge += f" ({freq})"
        integ = int_by_flow.get(fid)
        if integ:
            tech = integ.get("technology")
            if tech:
                edge += f" [via {tech}]"
        lines.append(f"  {a} {arrow}|{edge}| {b}")
    lines += ["```", ""]
    return "\n".join(lines)
