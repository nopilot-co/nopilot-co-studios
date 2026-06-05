"""``engagement.json`` manifest — read / write / validate, with a
deterministic rollup recomputed on every mutation.

Mirrors ``scripts/planner/composition.py`` for shape. The manifest lives
at the docket root (passed as ``--root``); every write goes through
``write()`` which validates against ``engagement.schema.json`` and
recomputes ``rollup`` from the canonical fields.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from . import SCHEMAS

ENGAGEMENT = "engagement.json"
SCHEMA_VERSION = "1.0"
STATUSES = ("draft", "scoping", "active", "delivered", "closed")
JOB_STATUSES = ("planned", "briefed", "in-progress", "blocked", "gated", "done")
ITEM_KINDS = ("question", "blocker", "risk")
ITEM_STATUSES = ("open", "answered", "resolved")
CHECKPOINT_LEVELS = ("L2", "L3")
CHECKPOINT_STATUSES = ("pending", "cleared", "declined")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _schema() -> dict:
    return json.loads((SCHEMAS / "engagement.schema.json").read_text())


def path_for(root: Path) -> Path:
    return root / ENGAGEMENT


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
            f"no engagement.json at {root} — run `engagement new --root <root>`"
        )
    return json.loads(p.read_text())


def write(root: Path, data: dict) -> dict:
    """Validate + recompute rollup + persist."""
    data = dict(data)
    data["rollup"] = compute_rollup(data)
    errs = validate(data)
    if errs:
        raise ValueError("invalid engagement.json:\n  " + "\n  ".join(errs))
    p = path_for(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")
    return data


# ----------------------------------------------------------------- rollup


def compute_rollup(data: dict) -> dict:
    """Derived status summary. Recomputed on every mutation; never hand-set."""
    jobs = data.get("jobs") or []
    questions = [
        i for i in (data.get("questions") or []) if i.get("status") != "resolved"
    ]
    blockers = [
        i for i in (data.get("blockers") or []) if i.get("status") != "resolved"
    ]
    risks = [i for i in (data.get("risks") or []) if i.get("status") != "resolved"]
    checkpoints = [
        c for c in (data.get("checkpoints") or []) if c.get("status") == "pending"
    ]

    by_status: dict[str, int] = {}
    for j in jobs:
        by_status[j.get("status", "unknown")] = (
            by_status.get(j.get("status", "unknown"), 0) + 1
        )

    pct = 0.0
    if jobs:
        pct = round(100 * by_status.get("done", 0) / len(jobs), 1)

    next_checkpoint = checkpoints[0] if checkpoints else None
    return {
        "jobs_total": len(jobs),
        "jobs_by_status": by_status,
        "percent_complete": pct,
        "open_questions": len(questions),
        "open_blockers": len(blockers),
        "open_risks": len(risks),
        "pending_checkpoints": len(checkpoints),
        "next_checkpoint": (
            {
                "id": next_checkpoint.get("id"),
                "level": next_checkpoint.get("level"),
                "title": next_checkpoint.get("title"),
            }
            if next_checkpoint
            else None
        ),
    }


# ----------------------------------------------------------------- new + history


def new(
    root: Path,
    *,
    engagement_slug: str,
    objective: str | None = None,
    audience: str | None = None,
    client: str | None = None,
) -> dict:
    """Scaffold an engagement.json. Idempotent on existing files only by
    refusing to overwrite — call ``set_brief`` or ``add_cast`` to mutate."""
    if exists(root):
        raise ValueError(
            f"engagement.json already exists at {path_for(root)} — refusing to overwrite"
        )
    data = {
        "schema_version": SCHEMA_VERSION,
        "engagement": engagement_slug,
        "status": "draft",
        "created": _now(),
        "brief": {
            "objective": objective or "",
            "audience": audience or "",
            "client": client or "",
            "constraints": [],
            "success_criteria": [],
        },
        "cast": [],
        "jobs": [],
        "questions": [],
        "blockers": [],
        "risks": [],
        "decisions": [],
        "checkpoints": [],
        "history": [{"at": _now(), "note": "engagement scaffolded"}],
    }
    return write(root, data)


def append_history(data: dict, note: str) -> None:
    data.setdefault("history", []).append({"at": _now(), "note": note})


def set_status(root: Path, status: str) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
    data = read(root)
    data["status"] = status
    append_history(data, f"status → {status}")
    return write(root, data)


def set_brief(
    root: Path,
    *,
    objective: str | None = None,
    audience: str | None = None,
    client: str | None = None,
    constraints: list[str] | None = None,
    success_criteria: list[str] | None = None,
) -> dict:
    data = read(root)
    b = data.setdefault("brief", {})
    if objective is not None:
        b["objective"] = objective
    if audience is not None:
        b["audience"] = audience
    if client is not None:
        b["client"] = client
    if constraints is not None:
        b["constraints"] = list(constraints)
    if success_criteria is not None:
        b["success_criteria"] = list(success_criteria)
    append_history(data, "brief updated")
    return write(root, data)


def add_cast(root: Path, *, role: str, justification: str | None = None) -> dict:
    data = read(root)
    cast = data.setdefault("cast", [])
    if any(c.get("role") == role for c in cast):
        raise ValueError(f"role '{role}' already in cast")
    cast.append({"role": role, "justification": justification or ""})
    append_history(data, f"cast + {role}")
    return write(root, data)
