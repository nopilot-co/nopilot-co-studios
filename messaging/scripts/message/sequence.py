"""Multi-step sequences: ordered, linked message sessions.

A sequence is a folder holding a ``sequence.json`` manifest plus one child
session per step (``step-01-<name>``, ``step-02-<name>`` …). Each step is a
normal message session — its own format, lint, render, and status — while the
manifest records order and links so the `sequence` skill and the
creative-director can treat the steps as one campaign. Mechanics only; the
copy/cadence judgment lives in the `sequence` skill.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import formats as formats_mod
from . import resolve_context_root
from . import session as session_mod


def sequence_root(name: str) -> Path:
    return resolve_context_root() / name


def step_id(index: int, step_name: str) -> str:
    return f"step-{index:02d}-{step_name}"


def new(brand: str, name: str, steps: list[tuple[str, str]]) -> Path:
    """Create a sequence of linked sessions.

    `steps` is an ordered list of ``(step_name, format_slug)``. All formats are
    validated up front so a bad slug fails before any folders are created.
    Returns the sequence root.
    """
    if not steps:
        raise ValueError("a sequence needs at least one step (--step NAME:FORMAT)")

    errors: list[str] = []
    for sname, fmt in steps:
        fmt_errors = formats_mod.validate(fmt)
        if fmt_errors:
            errors.append(f"step '{sname}': invalid format '{fmt}' ({fmt_errors[0]})")
    if errors:
        raise ValueError(
            "invalid sequence:\n  "
            + "\n  ".join(errors)
            + "\n  (run `message formats list` to see valid slugs)"
        )

    root = sequence_root(name)
    root.mkdir(parents=True, exist_ok=True)

    step_records: list[dict] = []
    for i, (sname, fmt) in enumerate(steps, start=1):
        sid = step_id(i, sname)
        # Each step is a full session nested under the sequence folder.
        session_mod.new(brand, f"{name}/{sid}", fmt)
        step_path = root / sid
        state = session_mod.read_state(step_path)
        state["sequence"] = name
        state["step"] = i
        state["step_name"] = sname
        session_mod.write_state(step_path, state)
        step_records.append({"step": i, "name": sname, "format": fmt, "session": sid})

    manifest = root / "sequence.json"
    if not manifest.exists():
        manifest.write_text(
            json.dumps(
                {
                    "brand": brand,
                    "sequence": name,
                    "created": datetime.now(timezone.utc).isoformat(),
                    "steps": step_records,
                },
                indent=2,
            )
        )
    return root


def read_manifest(seq_path: Path) -> dict:
    return json.loads((seq_path / "sequence.json").read_text())


def status(seq_path: Path) -> list[dict]:
    """Per-step status, read from each step session's version.json."""
    rows: list[dict] = []
    for step in read_manifest(seq_path)["steps"]:
        step_path = seq_path / step["session"]
        try:
            st = session_mod.read_state(step_path)
            rows.append(
                {
                    **step,
                    "status": st.get("status", "—"),
                    "current": st.get("current", "—"),
                }
            )
        except FileNotFoundError:
            rows.append({**step, "status": "missing", "current": "—"})
    return rows
