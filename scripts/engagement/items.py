"""First-class Questions / Blockers / Risks in the engagement manifest.

Mirrors the Bible §8 shape:
``{ id, kind, title, raised_by_role, raised_at, needs, status, resolution?,
   blocking_jobs?[] }``

Allocation: ``Q-001``, ``B-001``, ``R-001`` (per-kind sequences).
"""

from __future__ import annotations

from datetime import datetime, timezone

from .manifest import ITEM_KINDS, ITEM_STATUSES, append_history, read, write

KIND_PREFIX = {"question": "Q", "blocker": "B", "risk": "R"}
KIND_LIST = {"question": "questions", "blocker": "blockers", "risk": "risks"}
NEEDS = ("user", "client", "role")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _list_key(kind: str) -> str:
    if kind not in ITEM_KINDS:
        raise ValueError(f"kind must be one of: {', '.join(ITEM_KINDS)}")
    return KIND_LIST[kind]


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
    root,
    *,
    kind: str,
    title: str,
    raised_by_role: str | None = None,
    needs: str | None = None,
    blocking_jobs: list[str] | None = None,
) -> dict:
    if needs and needs not in NEEDS:
        raise ValueError(f"needs must be one of: {', '.join(NEEDS)}")
    data = read(root)
    key = _list_key(kind)
    items = data.setdefault(key, [])
    item = {
        "id": _allocate_id(items, kind),
        "kind": kind,
        "title": title,
        "status": "open",
        "raised_at": _now(),
    }
    if raised_by_role:
        item["raised_by_role"] = raised_by_role
    if needs:
        item["needs"] = needs
    if blocking_jobs:
        item["blocking_jobs"] = list(blocking_jobs)
    items.append(item)
    append_history(data, f"{kind} + {item['id']}: {title}")
    write(root, data)
    return item


def resolve(
    root,
    *,
    kind: str,
    item_id: str,
    resolution: str,
    status: str = "resolved",
) -> dict:
    if status not in ITEM_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(ITEM_STATUSES)}")
    data = read(root)
    key = _list_key(kind)
    for it in data.get(key, []):
        if it.get("id") == item_id:
            it["status"] = status
            it["resolved_at"] = _now()
            it["resolution"] = resolution
            append_history(data, f"{kind} {item_id} → {status}")
            write(root, data)
            return it
    raise KeyError(f"no {kind} '{item_id}'")


def show(root, *, kind: str | None = None, status: str | None = None) -> list[dict]:
    data = read(root)
    if kind:
        rows = data.get(_list_key(kind)) or []
    else:
        rows = []
        for k in ITEM_KINDS:
            rows.extend(data.get(_list_key(k)) or [])
    if status:
        if status not in ITEM_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(ITEM_STATUSES)}")
        rows = [r for r in rows if r.get("status") == status]
    return rows
