"""Per-slug persistent settings (#32).

A user-level config mapping a slug to its **working folder**, so the studio
reads inputs / writes outputs and resolves the brand for that slug without
per-invocation env vars. Stored at ``$STUDIOS_CONFIG`` or
``$XDG_CONFIG_HOME/studios/slugs.yml`` (default ``~/.config/studios/slugs.yml``).
Not git-tracked — it holds machine paths.

Derived layout for a slug whose working folder is ``<wf>``:

    sessions   <wf>/<session-name>
    brand      <wf>/brand/<slug>

Resolution precedence (see brand.brand_root / session.session_root): an explicit
docket env (server modes) wins, then this per-slug setting, then the legacy
global store.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def config_path() -> Path:
    """Location of the per-slug config file (XDG-aware; env-overridable)."""
    override = os.environ.get("STUDIOS_CONFIG")
    if override:
        return Path(override).expanduser()
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "studios" / "slugs.yml"


def load() -> dict[str, Any]:
    """Parse the config file; ``{}`` if absent or malformed."""
    path = config_path()
    if not path.is_file():
        return {}
    try:
        return yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {}


def working_folder(slug: str) -> Path | None:
    """The configured working-folder base for ``slug``, or ``None`` if unset."""
    entry = (load().get("slugs") or {}).get(slug) or {}
    wf = entry.get("working_folder")
    return Path(wf).expanduser().resolve() if isinstance(wf, str) and wf else None


def set_working_folder(slug: str, path: str | Path) -> Path:
    """Persist ``slug``'s working folder. Returns the resolved path written."""
    resolved = Path(path).expanduser().resolve()
    data = load()
    slugs = data.get("slugs")
    if not isinstance(slugs, dict):
        slugs = data["slugs"] = {}
    slugs[slug] = {"working_folder": str(resolved)}
    cfg = config_path()
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(yaml.safe_dump(data, sort_keys=True))
    return resolved
