"""First-class RAID register: Risks / Assumptions / Issues / Dependencies.

Each entry mirrors the Bible §8 first-class-open-items shape (id, kind,
title, severity, owner, status, raised_at, resolution). The CLI gives it
the same first-class treatment as the engagement plan.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .store import read_raid, write_raid

KINDS = ("risk", "assumption", "issue", "dependency")
SEVERITIES = ("low", "medium", "high", "critical")
KIND_PREFIX = {"risk": "R", "assumption": "A", "issue": "I", "dependency": "D"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _allocate_id(items: list[dict], kind: str) -> str:
    prefix = KIND_PREFIX[kind]
    used = []
    for it in items:
        rid = it.get("id") or ""
        if rid.startswith(prefix + "-"):
            try:
                used.append(int(rid[len(prefix) + 1 :]))
            except ValueError:
                continue
    n = (max(used) + 1) if used else 1
    return f"{prefix}-{n:03d}"


def add(
    slug: str,
    *,
    kind: str,
    title: str,
    severity: str = "medium",
    owner: str | None = None,
    notes: str | None = None,
) -> dict:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of: {', '.join(KINDS)}")
    if severity not in SEVERITIES:
        raise ValueError(f"severity must be one of: {', '.join(SEVERITIES)}")
    data = read_raid(slug)
    items = data.setdefault("items", [])
    item = {
        "id": _allocate_id(items, kind),
        "kind": kind,
        "title": title,
        "severity": severity,
        "status": "open",
        "raised_at": _now(),
    }
    if owner:
        item["owner"] = owner
    if notes:
        item["notes"] = notes
    items.append(item)
    write_raid(slug, data)
    return item


def resolve(slug: str, *, raid_id: str, resolution: str) -> dict:
    data = read_raid(slug)
    for it in data.get("items", []):
        if it.get("id") == raid_id:
            it["status"] = "resolved"
            it["resolved_at"] = _now()
            it["resolution"] = resolution
            write_raid(slug, data)
            return it
    raise KeyError(f"no RAID entry '{raid_id}' for engagement '{slug}'")


def show(slug: str, *, kind: str | None = None) -> list[dict]:
    data = read_raid(slug)
    items = data.get("items") or []
    if kind:
        if kind not in KINDS:
            raise ValueError(f"kind must be one of: {', '.join(KINDS)}")
        items = [it for it in items if it.get("kind") == kind]
    return items


def summary(slug: str) -> dict:
    data = read_raid(slug)
    items = data.get("items") or []
    out = {"total": len(items)}
    for k in KINDS:
        out[k] = {
            "open": sum(
                1 for i in items if i.get("kind") == k and i.get("status") == "open"
            ),
            "resolved": sum(
                1 for i in items if i.get("kind") == k and i.get("status") == "resolved"
            ),
        }
    out["open"] = sum(1 for i in items if i.get("status") == "open")
    out["resolved"] = sum(1 for i in items if i.get("status") == "resolved")
    return out
