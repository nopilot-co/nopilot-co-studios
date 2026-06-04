"""The ``composition.json`` manifest: read / write / validate, section CRUD,
completion rollup, and history.

This is the planner's own manifest (distinct from the design docket's
``production-manifest.json``). It lives at the docket root and records the
ordered sections, each section's completion status and data/viz contract, a
rolled-up completion summary, and a history log. ``order`` and ``rollup`` are
**derived** — recomputed on every mutation, never hand-set.

Mechanics only: every function here is deterministic file/JSON work. The
judgment about *which* sections exist, their briefs, and when one is "approved"
lives in the planner skill.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from . import SCHEMAS

COMPOSITION = "composition.json"
SCHEMA_VERSION = "1.0"
STATUSES = ("todo", "briefed", "drafted", "approved")


# ----------------------------------------------------------------- helpers
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _schema() -> dict:
    return json.loads((SCHEMAS / "composition.schema.json").read_text())


def path_for(root: Path) -> Path:
    return root / COMPOSITION


def exists(root: Path) -> bool:
    return path_for(root).is_file()


# ----------------------------------------------------------------- validation
def validate(data: dict) -> list[str]:
    validator = Draft202012Validator(_schema())
    return [
        ("/".join(map(str, e.path)) + ": " + e.message) if e.path else e.message
        for e in sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    ]


# ----------------------------------------------------------------- read / write
def read(root: Path) -> dict:
    p = path_for(root)
    if not p.is_file():
        raise FileNotFoundError(
            f"no composition.json under {root} — run `planner plan new` first"
        )
    return json.loads(p.read_text())


def write(root: Path, data: dict) -> None:
    errors = validate(data)
    if errors:
        raise ValueError("invalid composition:\n  " + "\n  ".join(errors))
    path_for(root).write_text(json.dumps(data, indent=2) + "\n")


# ----------------------------------------------------------------- derived state
def _renumber(data: dict) -> None:
    for i, sec in enumerate(data["sections"], start=1):
        sec["order"] = i


def _rollup(data: dict) -> None:
    sections = data["sections"]
    counts = {s: 0 for s in STATUSES}
    for sec in sections:
        counts[sec["status"]] += 1
    total = len(sections)
    approved = counts["approved"]
    data["rollup"] = {
        "total": total,
        "todo": counts["todo"],
        "briefed": counts["briefed"],
        "drafted": counts["drafted"],
        "approved": approved,
        "percent_approved": round(approved / total * 100) if total else 0,
        "ready_to_assemble": bool(total) and approved == total,
    }


def _recompute(data: dict) -> None:
    _renumber(data)
    _rollup(data)


def _log(data: dict, event: str, **fields) -> None:
    data["history"].append({"at": _now(), "event": event, **fields})


def _find(data: dict, section_id: str) -> dict:
    for sec in data["sections"]:
        if sec["id"] == section_id:
            return sec
    raise ValueError(
        f"no section '{section_id}' (have: "
        f"{', '.join(s['id'] for s in data['sections']) or 'none'})"
    )


# ----------------------------------------------------------------- bump
def bump(current: str, kind: str) -> str:
    """Semver bump of the composition's own version. 0.0.0 jumps to 1.0.0."""
    if current == "0.0.0":
        return "1.0.0"
    major, minor, patch = (int(p) for p in current.split("."))
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


# ----------------------------------------------------------------- mutations
def new(root: Path, *, brand: str, objective: str, fmt: str, session: str) -> dict:
    """Build and write the initial composition manifest. Idempotent: refuses to
    clobber an existing one (start a new docket instead)."""
    if exists(root):
        raise ValueError(
            f"composition.json already exists under {root} — "
            "one composition per docket (v1)"
        )
    data = {
        "schema_version": SCHEMA_VERSION,
        "kind": "composition",
        "objective": objective,
        "brand": brand,
        "format": fmt,
        "session": session,
        "created": _now(),
        "current": "0.0.0",
        "sections": [],
        "rollup": {},
        "history": [],
    }
    _recompute(data)
    _log(data, "plan-new", note=f"objective set; format={fmt}; session={session}")
    write(root, data)
    return data


def add_section(
    root: Path, *, section_id: str, title: str, after: str | None = None
) -> dict:
    data = read(root)
    if any(s["id"] == section_id for s in data["sections"]):
        raise ValueError(f"section '{section_id}' already exists")
    sec = {
        "id": section_id,
        "title": title,
        "order": 0,  # set by _renumber
        "status": "todo",
        "brief": f"sections/{section_id}/brief.md",
        "content": f"sections/{section_id}/content.md",
        "data_sources": [],
        "viz": None,
        "source": {"origin": "drafted", "provenance": ""},
    }
    if after:
        idx = next(
            (i for i, s in enumerate(data["sections"]) if s["id"] == after), None
        )
        if idx is None:
            raise ValueError(f"--after '{after}' is not an existing section")
        data["sections"].insert(idx + 1, sec)
    else:
        data["sections"].append(sec)
    _recompute(data)
    _log(data, "section-add", section=section_id)
    write(root, data)
    (root / "sections" / section_id).mkdir(parents=True, exist_ok=True)
    return data


def move_section(root: Path, *, section_id: str, after: str | None) -> dict:
    data = read(root)
    sec = _find(data, section_id)
    data["sections"].remove(sec)
    if after is None:
        data["sections"].insert(0, sec)
    else:
        if after == section_id:
            raise ValueError("cannot move a section after itself")
        idx = next(
            (i for i, s in enumerate(data["sections"]) if s["id"] == after), None
        )
        if idx is None:
            raise ValueError(f"--after '{after}' is not an existing section")
        data["sections"].insert(idx + 1, sec)
    _recompute(data)
    _log(data, "section-move", section=section_id, after=after or "(start)")
    write(root, data)
    return data


def set_section(
    root: Path,
    *,
    section_id: str,
    status: str | None = None,
    title: str | None = None,
    note: str | None = None,
) -> dict:
    data = read(root)
    sec = _find(data, section_id)
    if status is not None:
        if status not in STATUSES:
            raise ValueError(f"status must be one of {', '.join(STATUSES)}")
        sec["status"] = status
    if title is not None:
        sec["title"] = title
    if note is not None:
        sec["source"]["provenance"] = note
    _recompute(data)
    _log(
        data,
        "section-set",
        section=section_id,
        **{k: v for k, v in (("status", status), ("title", title)) if v is not None},
    )
    write(root, data)
    return data


def add_data(root: Path, *, section_id: str, rel_path: str, kind: str) -> dict:
    data = read(root)
    sec = _find(data, section_id)
    if any(d["path"] == rel_path for d in sec["data_sources"]):
        raise ValueError(f"'{rel_path}' is already a data source for '{section_id}'")
    sec["data_sources"].append({"path": rel_path, "kind": kind})
    _recompute(data)
    _log(data, "data-add", section=section_id, path=rel_path, kind=kind)
    write(root, data)
    return data


def set_viz(
    root: Path,
    *,
    section_id: str,
    chart_type: str,
    source: str,
    x: str | None = None,
    y: str | None = None,
    caption: str | None = None,
) -> dict:
    data = read(root)
    sec = _find(data, section_id)
    viz = {"type": chart_type, "source": source, "rendered_by": "design"}
    if x is not None:
        viz["x"] = x
    if y is not None:
        viz["y"] = y
    if caption is not None:
        viz["caption"] = caption
    sec["viz"] = viz
    _recompute(data)
    _log(data, "viz-set", section=section_id, type=chart_type)
    write(root, data)
    return data


def record_assemble(
    root: Path, *, version: str, source_path: str, sections: list[str]
) -> dict:
    data = read(root)
    data["current"] = version
    _log(data, "assemble", version=version, source=source_path, sections=sections)
    write(root, data)
    return data
