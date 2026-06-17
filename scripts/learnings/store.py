"""Deterministic file mechanics for the append-only learnings store.

Judgment (what counts as a plugin-improvement learning) lives in
``skills/reflect/SKILL.md``; this module only writes, reads, lists, and
status-transitions the markdown records. One learning = one markdown file with
YAML frontmatter under ``learnings/<YYYY>/<YYYY-MM-DD>-<studio>-<slug>.md``.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import learnings_dir

CATEGORIES = ("skill", "cli", "format", "asset", "orchestration", "docs", "none")
SEVERITIES = ("low", "medium", "high")
STATUSES = ("open", "triaged", "promoted", "wontfix", "fixed")

_PROMOTION_PLACEHOLDER = "_(filled when promoted → issue # or ADR-NNN)_"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def slugify(text: str, *, max_len: int = 48) -> str:
    s = _SLUG_RE.sub("-", str(text).strip().lower()).strip("-")
    return s[:max_len].rstrip("-") or "note"


# ----------------------------------------------------------------- frontmatter


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            fm = yaml.safe_load(text[4:end]) or {}
            body = text[end + 4 :].lstrip("\n")
            return (fm if isinstance(fm, dict) else {}), body
    return {}, text


def _render(fm: dict, body: str) -> str:
    front = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{front}\n---\n\n{body.rstrip()}\n"


# ----------------------------------------------------------------- paths


def _dir() -> Path:
    return learnings_dir()


def _unique_path(year_dir: Path, base: str) -> Path:
    cand = year_dir / f"{base}.md"
    n = 2
    while cand.exists():  # never overwrite — append a discriminator
        cand = year_dir / f"{base}-{n}.md"
        n += 1
    return cand


def _iter_files() -> list[Path]:
    d = _dir()
    if not d.exists():
        return []
    return sorted(p for p in d.rglob("*.md") if p.name != "README.md")


def _find(learning_id: str) -> Path:
    p = Path(learning_id)
    if p.suffix == ".md" and p.exists():
        return p
    matches = [f for f in _iter_files() if f.stem == learning_id]
    if not matches:
        raise FileNotFoundError(f"no learning with id '{learning_id}'")
    return matches[0]


def _load(path: Path) -> dict:
    fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    out = dict(fm)
    out.setdefault("id", path.stem)
    out["_path"] = str(path)
    out["_body"] = body
    return out


# ----------------------------------------------------------------- write


def add(
    *,
    studio: str,
    category: str,
    severity: str,
    title: str,
    proposed_change: str | None = None,
    engagement: str = "",
    body: str | None = None,
) -> dict:
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}")
    if severity not in SEVERITIES:
        raise ValueError(f"severity must be one of {SEVERITIES}")
    if not str(title).strip():
        raise ValueError("title is required")

    date = _today()
    year_dir = _dir() / date[:4]
    year_dir.mkdir(parents=True, exist_ok=True)
    base = f"{date}-{slugify(studio)}-{slugify(title)}"
    path = _unique_path(year_dir, base)

    fm = {
        "id": path.stem,
        "date": date,
        "studio": studio,
        "engagement": engagement or "",
        "category": category,
        "severity": severity,
        "title": str(title).strip(),
        "proposed-change": (proposed_change or "").strip(),
        "status": "open",
        "ref": "",
    }
    what = (body or "").strip() or "_(describe the friction or insight observed during the run)_"
    change = (proposed_change or "").strip() or "_(the concrete change to the plugin)_"
    doc = (
        f"## What happened\n\n{what}\n\n"
        "## Why it matters (tool, not deliverable)\n\n"
        "_(why this is about the studio/plugin itself)_\n\n"
        f"## Proposed change\n\n{change}\n\n"
        f"## Promotion\n\n{_PROMOTION_PLACEHOLDER}\n"
    )
    path.write_text(_render(fm, doc), encoding="utf-8")
    return {k: v for k, v in fm.items()} | {"path": str(path)}


def add_none(*, engagement: str = "", reason: str) -> dict:
    return add(
        studio="none",
        category="none",
        severity="low",
        title=f"no learnings — {engagement or 'run'}",
        engagement=engagement,
        body=reason,
    )


# ----------------------------------------------------------------- read / list


def list_(
    *,
    status: str | None = None,
    studio: str | None = None,
    category: str | None = None,
) -> list[dict]:
    rows = [_load(p) for p in _iter_files()]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    if studio:
        rows = [r for r in rows if r.get("studio") == studio]
    if category:
        rows = [r for r in rows if r.get("category") == category]
    rows.sort(key=lambda r: (r.get("date", ""), r.get("id", "")), reverse=True)
    return rows


def read_one(learning_id: str) -> dict:
    return _load(_find(learning_id))


# ----------------------------------------------------------------- status / promote


def set_status(learning_id: str, *, status: str, ref: str | None = None) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    path = _find(learning_id)
    fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    fm["status"] = status
    if ref:
        fm["ref"] = ref
        body = _record_promotion(body, ref)
    path.write_text(_render(fm, body), encoding="utf-8")
    out = dict(fm)
    out["_path"] = str(path)
    return out


def _record_promotion(body: str, ref: str) -> str:
    line = f"Promoted → {ref}"
    if _PROMOTION_PLACEHOLDER in body:
        return body.replace(_PROMOTION_PLACEHOLDER, line)
    if "## Promotion" in body:
        return body.rstrip() + f"\n\n{line}\n"
    return body.rstrip() + f"\n\n## Promotion\n\n{line}\n"


def promote_command(learning_id: str) -> dict:
    """Build a dry-run ``gh issue create`` payload for a learning.

    Outward action (actually creating the issue) stays manual — this only
    returns the command. Mirrors ``engagement sync github``, which builds a
    plan rather than firing it.
    """
    r = read_one(learning_id)
    rel = Path(r["_path"])
    try:
        rel = rel.relative_to(_dir().parent)
    except ValueError:
        pass
    title = f"[learning] {r.get('title', '')}"
    label = f"learning,{r.get('category', '')}"
    body = (
        f"Source: {rel}\n\n"
        f"Studio: {r.get('studio', '')} · severity: {r.get('severity', '')}\n\n"
        f"Proposed change: {r.get('proposed-change', '')}\n"
    )
    cmd = ["gh", "issue", "create", "--title", title, "--label", label, "--body", body]
    return {"id": r["id"], "command": cmd}
