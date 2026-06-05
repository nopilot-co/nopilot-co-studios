"""Decisions in the engagement manifest — pointers to ADR-style records.

Per Bible §7, decisions live in their own append-only store
(``decisions/`` dir of ADRs, or the architecture studio's per-engagement
``adrs/``). The engagement manifest holds *pointers* — id, title, ref
(path or URL), recorded-at — so the rollup can surface decisions without
duplicating their content.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .manifest import append_history, read, write


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _allocate_id(items: list[dict]) -> str:
    used = []
    for it in items:
        did = it.get("id") or ""
        if did.startswith("D-"):
            try:
                used.append(int(did[2:]))
            except ValueError:
                continue
    n = (max(used) + 1) if used else 1
    return f"D-{n:03d}"


def add(
    root,
    *,
    title: str,
    ref: str | None = None,
    role: str | None = None,
    summary: str | None = None,
) -> dict:
    data = read(root)
    decisions = data.setdefault("decisions", [])
    item = {
        "id": _allocate_id(decisions),
        "title": title,
        "recorded_at": _now(),
    }
    if ref:
        item["ref"] = ref
    if role:
        item["role"] = role
    if summary:
        item["summary"] = summary
    decisions.append(item)
    append_history(data, f"decision + {item['id']}: {title}")
    write(root, data)
    return item


def show(root) -> list[dict]:
    return read(root).get("decisions") or []
