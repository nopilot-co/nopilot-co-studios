"""Meta-content convention — the ``nopilot:`` namespace (issue #11).

Content ``.md`` files carry three renderer-invisible channels:

- **YAML front-matter** (``version`` / ``status`` / ``format_target`` / ``author``),
- a **mutable** ``<!-- nopilot:guidance ... -->`` block — the consolidated,
  canonical "how to render this" (overwritten each pass),
- an **append-only** ``<!-- nopilot:history ... -->`` block — version + approval
  log that travels with the content element,

plus inline ``<!-- nopilot:comment ... -->``.

``strip()`` removes the front-matter and **every** ``nopilot:`` region so they
never reach Quarto/MJML. HTML comments are NOT self-hiding on the HTML/RevealJS
path — unstripped, internal notes leak into client-facing source — so this strip
is mandatory on every export, not a safety net. ``has_meta_leak()`` is the guard
that verifies it on the HTML path.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

_FM_RE = re.compile(r"\A---\n(.*?)\n---[ \t]*\n?", re.DOTALL)
_NOPILOT_RE = re.compile(r"<!--\s*nopilot:.*?-->", re.DOTALL)
_HISTORY_RE = re.compile(r"(<!--\s*nopilot:history\b.*?)(-->)", re.DOTALL)
_VERSION_DATE_FMT = "%Y-%m-%d"


def _as_text(text_or_path: str | Path) -> str:
    if isinstance(text_or_path, Path):
        return text_or_path.read_text(encoding="utf-8")
    return text_or_path


def split_front_matter(text: str) -> tuple[str | None, str]:
    """Return ``(raw_front_matter_or_None, body)``."""
    m = _FM_RE.match(text)
    if m:
        return m.group(1), text[m.end() :]
    return None, text


def read_meta(text_or_path: str | Path) -> dict:
    """Parse the YAML front-matter into a dict ({} if absent/empty)."""
    raw, _ = split_front_matter(_as_text(text_or_path))
    if not raw:
        return {}
    data = yaml.safe_load(raw)
    return data if isinstance(data, dict) else {}


def strip(text_or_path: str | Path) -> str:
    """Clean markdown for rendering: front-matter + all ``nopilot:`` regions removed."""
    _, body = split_front_matter(_as_text(text_or_path))
    body = _NOPILOT_RE.sub("", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.lstrip("\n").rstrip() + "\n"


def has_meta_leak(rendered_text: str) -> bool:
    """True if any ``nopilot:`` region survived into rendered output."""
    return "nopilot:" in rendered_text


def set_front_matter_field(path: Path, key: str, value: object) -> None:
    """Set/replace a single front-matter field, preserving body and key order."""
    text = path.read_text(encoding="utf-8")
    raw, body = split_front_matter(text)
    data = yaml.safe_load(raw) if raw else {}
    if not isinstance(data, dict):
        data = {}
    data[key] = value
    fm = yaml.safe_dump(data, sort_keys=False).strip()
    sep = "" if body.startswith("\n") else "\n"
    path.write_text(f"---\n{fm}\n---{sep}{body}", encoding="utf-8")


def append_history(
    path: Path,
    *,
    version: str,
    author: str | None = None,
    status: str | None = None,
    note: str | None = None,
) -> None:
    """Append one entry to the append-only ``nopilot:history`` block (created if absent)."""
    text = path.read_text(encoding="utf-8")
    stamp = datetime.now(timezone.utc).strftime(_VERSION_DATE_FMT)
    bits = [stamp, f"v{version}"]
    if author:
        bits.append(f"author={author}")
    if status:
        bits.append(f"status={status}")
    line = "- " + " ".join(bits) + (f' note="{note}"' if note else "")

    m = _HISTORY_RE.search(text)
    if m:
        head, close = m.group(1).rstrip("\n"), m.group(2)
        new_block = f"{head}\n{line}\n{close}"
        text = text[: m.start()] + new_block + text[m.end() :]
    else:
        block = f"\n<!-- nopilot:history   (append-only — newest last)\n{line}\n-->\n"
        text = text.rstrip("\n") + "\n" + block
    path.write_text(text, encoding="utf-8")
