"""ADR-style decision records, first-class.

Each ADR is one Markdown file at ``adrs/NNN-<slug>.md`` with YAML front
matter (`id`, `title`, `status`, `dates`, `links`) and the prose sections
*Context*, *Decision*, *Consequences*, *Alternatives*.

This module owns the CRUD: id allocation, front-matter validation against
``adr.schema.json``, and listing.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from . import SCHEMAS, load_yaml
from .store import adrs_dir

STATUSES = ("proposed", "accepted", "deprecated", "superseded")


def _now_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _schema() -> dict:
    return json.loads((SCHEMAS / "adr.schema.json").read_text())


def _validate(data: dict) -> list[str]:
    validator = Draft202012Validator(_schema())
    return [
        (".".join(str(p) for p in e.absolute_path) or "<root>") + ": " + e.message
        for e in sorted(
            validator.iter_errors(data), key=lambda e: list(e.absolute_path)
        )
    ]


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "decision"


def _next_id(slug: str) -> str:
    d = adrs_dir(slug)
    used = []
    for p in d.glob("[0-9][0-9][0-9]-*.md"):
        try:
            used.append(int(p.name.split("-", 1)[0]))
        except ValueError:
            continue
    n = (max(used) + 1) if used else 1
    return f"{n:03d}"


def _read_md(path: Path) -> tuple[dict, str]:
    text = path.read_text()
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) == 3:
            return load_yaml(parts[1]) or {}, parts[2].lstrip("\n")
    return {}, text


def _write_md(path: Path, fm: dict, body: str) -> None:
    front = yaml.safe_dump(fm, sort_keys=False).rstrip("\n")
    path.write_text("---\n" + front + "\n---\n\n" + body.strip() + "\n")


def add(
    slug: str,
    *,
    title: str,
    status: str = "proposed",
    context: str | None = None,
    decision: str | None = None,
    consequences: str | None = None,
    alternatives: str | None = None,
) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
    aid = _next_id(slug)
    filename = f"{aid}-{_slugify(title)}.md"
    path = adrs_dir(slug) / filename
    fm = {
        "id": f"ADR-{aid}",
        "title": title,
        "status": status,
        "date": _now_date(),
    }
    errs = _validate(fm)
    if errs:
        raise ValueError("invalid ADR front matter:\n  " + "\n  ".join(errs))
    body_parts = [
        "## Context",
        (context or "_TODO_"),
        "",
        "## Decision",
        (decision or "_TODO_"),
        "",
        "## Consequences",
        (consequences or "_TODO_"),
    ]
    if alternatives:
        body_parts += ["", "## Alternatives considered", alternatives]
    _write_md(path, fm, "\n".join(body_parts))
    return {"id": fm["id"], "path": str(path), **fm}


def show(slug: str, adr_id: str | None = None) -> list[dict]:
    out = []
    d = adrs_dir(slug)
    if not d.exists():
        return out
    for path in sorted(d.glob("[0-9][0-9][0-9]-*.md")):
        fm, _ = _read_md(path)
        if not fm:
            continue
        if adr_id and fm.get("id") != adr_id:
            continue
        fm["path"] = str(path)
        out.append(fm)
    return out


def set_status(slug: str, adr_id: str, status: str) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
    d = adrs_dir(slug)
    for path in sorted(d.glob("[0-9][0-9][0-9]-*.md")):
        fm, body = _read_md(path)
        if fm.get("id") == adr_id:
            fm["status"] = status
            _write_md(path, fm, body)
            fm["path"] = str(path)
            return fm
    raise KeyError(f"no ADR '{adr_id}' for engagement '{slug}'")
