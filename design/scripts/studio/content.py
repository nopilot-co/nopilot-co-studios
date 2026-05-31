"""Content version bumping — the explicit reconciliation point (issue #9).

Authoring edits (LLM/human) don't flow through the CLI, so a content file's
version only changes when the user runs ``studio content bump``. It is the single
place that: stamps the filename's ``-v<semver>`` label, sets the front-matter
``version``, and appends the append-only ``nopilot:history`` entry — keeping the
filename, front-matter, and history in agreement.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import metacontent
from . import session as session_mod

# Matches a -v1.0.0 label immediately before the extension, e.g. foo-v1.2.3.md
_VER_RE = re.compile(r"-v(\d+\.\d+\.\d+)(?=\.[^.]+$)")


def current_version(path: Path) -> str:
    """Front-matter ``version`` wins; else the filename label; else ``0.0.0``."""
    meta = metacontent.read_meta(path)
    if meta.get("version"):
        return str(meta["version"])
    m = _VER_RE.search(path.name)
    return m.group(1) if m else "0.0.0"


def stamped_name(name: str, version: str) -> str:
    """Replace (or add) the ``-v<semver>`` label in a filename."""
    if _VER_RE.search(name):
        return _VER_RE.sub(f"-v{version}", name)
    stem, dot, ext = name.rpartition(".")
    return f"{stem}-v{version}.{ext}" if dot else f"{name}-v{version}"


def bump(
    path: Path,
    kind: str,
    *,
    author: str | None = None,
    status: str | None = None,
    note: str | None = None,
) -> tuple[Path, str]:
    """Bump ``path`` by ``kind`` (patch|minor|major). Returns (new_path, new_version)."""
    new_version = session_mod.bump(current_version(path), kind)
    metacontent.set_front_matter_field(path, "version", new_version)
    if status:
        metacontent.set_front_matter_field(path, "status", status)
    metacontent.append_history(
        path, version=new_version, author=author, status=status, note=note
    )
    new_path = path.with_name(stamped_name(path.name, new_version))
    if new_path != path:
        path.rename(new_path)
    return new_path, new_version
