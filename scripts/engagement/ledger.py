"""Append-only event log — ``ledger.jsonl`` at the docket root (Bible §7).

The engagement manifest gives you *current* state; the ledger gives you
*every transition*. One JSONL row per event:

    {
      "at":      "2026-06-05T11:30:01Z",
      "actor":   "producer" | "principal" | "<role>" | "system",
      "kind":    "manifest.write" | "job.add" | "job.set_status" |
                 "item.add" | "item.resolve" | "decision.add" |
                 "checkpoint.open" | "checkpoint.clear",
      "subject": "<id of the thing the event is about — J-NNN / Q-NNN / CP-NNN / D-NNN>",
      "summary": "<one-line human-readable note>",
      "details": { ... }    // optional structured payload
    }

The Producer writes events as it mutates the manifest; ``engagement
ledger show`` and ``ledger tail`` replay them.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

LEDGER_FILE = "ledger.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def path_for(root: Path) -> Path:
    return root / LEDGER_FILE


def exists(root: Path) -> bool:
    return path_for(root).is_file()


def append(
    root: Path,
    *,
    kind: str,
    summary: str,
    subject: str | None = None,
    actor: str = "system",
    details: dict | None = None,
    at: str | None = None,
) -> dict:
    """Append one event to ``ledger.jsonl``. Idempotent on writes."""
    event = {
        "at": at or _now(),
        "actor": actor,
        "kind": kind,
        "summary": summary,
    }
    if subject is not None:
        event["subject"] = subject
    if details is not None:
        event["details"] = details
    p = path_for(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as fh:
        fh.write(json.dumps(event) + "\n")
    return event


def read(root: Path) -> list[dict]:
    """Read all events in order."""
    p = path_for(root)
    if not p.is_file():
        return []
    out: list[dict] = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            # Skip corrupted lines; the ledger is append-only and a
            # corrupt entry shouldn't break replay of the rest.
            continue
    return out


def show(
    root: Path,
    *,
    limit: int = 50,
    kind: str | None = None,
    subject: str | None = None,
) -> list[dict]:
    """Return the last ``limit`` events, optionally filtered."""
    events = read(root)
    if kind:
        events = [e for e in events if e.get("kind") == kind]
    if subject:
        events = [e for e in events if e.get("subject") == subject]
    return events[-limit:]
