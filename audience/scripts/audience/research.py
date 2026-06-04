"""File a research source into the reader-model store + record provenance.

The *review* of a source (what the transcript/doc tells us about the reader's
needs) is the audience-research skill's judgment, written to
``research/<source>.md``. This module only files the raw source and records it in
``_audience.yml → provenance.sources`` so every claim in the model is traceable.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import store


def _is_url(source: str) -> bool:
    return source.startswith(("http://", "https://"))


def add_source(
    slug: str, source: str, *, kind: str | None = None, source_id: str | None = None
) -> dict:
    """Copy a file source into ``research/`` (or record a URL) and append it to
    ``provenance.sources``. Returns the updated model."""
    if not store.exists(slug):
        raise ValueError(f"no reader model '{slug}' — run `audience persona new` first")
    research_dir = store.slug_dir(slug) / "research"
    research_dir.mkdir(parents=True, exist_ok=True)

    if _is_url(source):
        ref = source.strip()
        resolved_kind = kind or "url"
        sid = source_id or _slug_from(ref)
    else:
        src = Path(source).expanduser()
        if not src.exists():
            raise ValueError(f"source not found: {source}")
        dest = research_dir / "sources" / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        ref = str(dest.relative_to(store.slug_dir(slug)))
        resolved_kind = kind or _kind_from_suffix(src.suffix)
        sid = source_id or src.stem

    data = store.read(slug)
    prov = data.setdefault("provenance", {})
    sources = prov.setdefault("sources", [])
    entry = {
        "id": sid,
        "kind": resolved_kind,
        "ref": ref,
        "captured": datetime.now(timezone.utc).date().isoformat(),
    }
    # de-dupe by id
    prov["sources"] = [s for s in sources if s.get("id") != sid] + [entry]
    store.write(slug, data)
    return data


def _kind_from_suffix(suffix: str) -> str:
    s = suffix.lower().lstrip(".")
    if s in ("md", "txt"):
        return "doc"
    if s in ("vtt", "srt"):
        return "transcript"
    return "doc"


def _slug_from(url: str) -> str:
    tail = url.rstrip("/").split("/")[-1] or "source"
    return (
        "".join(c if c.isalnum() else "-" for c in tail.lower()).strip("-")[:40]
        or "source"
    )
