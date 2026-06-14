"""Checkpoints in the engagement manifest — L2 / L3 gates per Bible §6.

A checkpoint pauses the engagement and surfaces a decision to the user
(via the Principal). L2 = scope / price / cast / commitment-bearing
decisions; L3 = outward delivery (send, publish, agree externally).

Allocation: ``CP-001``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from . import ledger
from .manifest import (
    CHECKPOINT_LEVELS,
    CHECKPOINT_STATUSES,
    append_history,
    read,
    write,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _allocate_id(items: list[dict]) -> str:
    used = []
    for it in items:
        cid = it.get("id") or ""
        if cid.startswith("CP-"):
            try:
                used.append(int(cid[3:]))
            except ValueError:
                continue
    n = (max(used) + 1) if used else 1
    return f"CP-{n:03d}"


def open_checkpoint(
    root,
    *,
    level: str,
    title: str,
    raised_by_role: str | None = None,
    blocking_jobs: list[str] | None = None,
    evidence: str | None = None,
) -> dict:
    if level not in CHECKPOINT_LEVELS:
        raise ValueError(f"level must be one of: {', '.join(CHECKPOINT_LEVELS)}")
    data = read(root)
    cps = data.setdefault("checkpoints", [])
    item = {
        "id": _allocate_id(cps),
        "level": level,
        "title": title,
        "status": "pending",
        "opened_at": _now(),
    }
    if raised_by_role:
        item["raised_by_role"] = raised_by_role
    if blocking_jobs:
        item["blocking_jobs"] = list(blocking_jobs)
    if evidence:
        item["evidence"] = evidence
    cps.append(item)
    append_history(data, f"checkpoint + {item['id']} ({level}): {title}")
    write(root, data)
    ledger.append(
        root,
        kind="checkpoint.open",
        subject=item["id"],
        summary=f"+ {item['id']} ({level}): {title}",
        actor=raised_by_role or "producer",
        details={"level": level, "blocking_jobs": blocking_jobs},
    )
    return item


def clear(
    root,
    *,
    checkpoint_id: str,
    outcome: str,
    status: str = "cleared",
    decided_by: str | None = None,
) -> dict:
    if status not in CHECKPOINT_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(CHECKPOINT_STATUSES)}")
    data = read(root)
    for cp in data.get("checkpoints", []):
        if cp.get("id") == checkpoint_id:
            cp["status"] = status
            cp["resolved_at"] = _now()
            cp["outcome"] = outcome
            if decided_by:
                cp["decided_by"] = decided_by
            append_history(data, f"checkpoint {checkpoint_id} → {status}")
            write(root, data)
            ledger.append(
                root,
                kind="checkpoint.clear",
                subject=checkpoint_id,
                summary=f"{checkpoint_id} → {status}: {outcome}",
                actor=decided_by or "producer",
                details={
                    "outcome": outcome,
                    "decided_by": decided_by,
                    "level": cp.get("level"),
                },
            )
            return cp
    raise KeyError(f"no checkpoint '{checkpoint_id}'")


def show(root, *, status: str | None = None) -> list[dict]:
    data = read(root)
    rows = data.get("checkpoints") or []
    if status:
        if status not in CHECKPOINT_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(CHECKPOINT_STATUSES)}")
        rows = [r for r in rows if r.get("status") == status]
    return rows
