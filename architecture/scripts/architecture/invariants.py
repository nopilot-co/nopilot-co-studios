"""Deterministic referential-integrity invariants for the architecture spec.

These run after schema validation. The CLI rejects materialise if any
invariant fails — the spec is the source of truth and pieces that point at
nothing aren't truth, they're typos.

Invariants enforced:

- Every ``system`` has a unique ``id``.
- Every ``data_flow`` has a unique ``id``; ``from`` and ``to`` resolve to
  existing system ids.
- Every ``integration`` has a unique ``id``; ``flow`` resolves to an
  existing data-flow id.
"""

from __future__ import annotations


def check(spec: dict) -> list[str]:
    """Return a list of human-readable violations. Empty = clean."""
    out: list[str] = []
    systems = spec.get("systems") or []
    flows = spec.get("data_flows") or []
    integrations = spec.get("integrations") or []

    # Unique ids per collection.
    sys_ids: set[str] = set()
    for s in systems:
        sid = s.get("id")
        if sid in sys_ids:
            out.append(f"duplicate system id: '{sid}'")
        if sid:
            sys_ids.add(sid)

    flow_ids: set[str] = set()
    for f in flows:
        fid = f.get("id")
        if fid in flow_ids:
            out.append(f"duplicate data_flow id: '{fid}'")
        if fid:
            flow_ids.add(fid)
        src = f.get("from")
        dst = f.get("to")
        if src and src not in sys_ids:
            out.append(
                f"data_flow '{fid}' references missing system in `from`: '{src}'"
            )
        if dst and dst not in sys_ids:
            out.append(f"data_flow '{fid}' references missing system in `to`: '{dst}'")

    int_ids: set[str] = set()
    for i in integrations:
        iid = i.get("id")
        if iid in int_ids:
            out.append(f"duplicate integration id: '{iid}'")
        if iid:
            int_ids.add(iid)
        flw = i.get("flow")
        if flw and flw not in flow_ids:
            out.append(
                f"integration '{iid}' references missing data_flow in `flow`: '{flw}'"
            )

    return out
