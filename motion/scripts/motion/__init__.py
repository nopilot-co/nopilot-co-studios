"""motion-studio orchestrator — deterministic glue for animated/narrated assets.

LLM judgment lives in the plugin's skills (markdown); this package handles file
ops, storyboard validation, render orchestration (Remotion / declarative SVG /
external providers), versioning, and rasterization. Mirrors the design studio's
shape so behaviour is identical across the three invocation modes.
"""

__version__ = "0.1.0"

import os
from pathlib import Path


def docket_root() -> Path | None:
    """The explicit production-docket root, if the caller set one.

    When ``$STUDIOS_DOCKET_ROOT`` is set, the studio operates inside a
    self-contained production docket: brand, twin, and session outputs live under
    that root with no external filesystem dependency. Resolved on every call so a
    long-lived host (server modes) can switch dockets per request.
    """
    env = os.environ.get("STUDIOS_DOCKET_ROOT")
    return Path(env).expanduser().resolve() if env else None


def resolve_context_root(studio_name: str = "motion") -> Path:
    """Where this studio's session outputs live. Override chain:

    1. ``$STUDIOS_DOCKET_ROOT`` → the docket root itself.
    2. ``$STUDIOS_PROJECT_ROOT`` → ``<env>/agents/claude/outbox/<studio>/``.
    3. Walk up from cwd for ``.wip/config.yml`` → co-located outbox.
    4. Legacy global ``~/context/studios/<studio>/``.
    """
    docket = docket_root()
    if docket:
        return docket

    env = os.environ.get("STUDIOS_PROJECT_ROOT")
    if env:
        return Path(env).expanduser() / "agents" / "claude" / "outbox" / studio_name

    d = Path.cwd().resolve()
    while d != d.parent:
        if (d / ".wip" / "config.yml").is_file():
            return d / "agents" / "claude" / "outbox" / studio_name
        d = d.parent

    return Path.home() / "context" / "studios" / studio_name


def brand_root_base() -> Path:
    """Per-slug brand store (shared studios-level entity). Docket-local when a
    docket root is set; else the shared ``~/context/studios/brand/``."""
    docket = docket_root()
    if docket:
        return docket / "brand"
    return Path.home() / "context" / "studios" / "brand"


def twin_root_base() -> Path:
    """Per-slug digital-twin store — likeness + voice reference + consent record.

    Motion-specific entity (the presenter archetype). Docket-local when a docket
    root is set (``<docket>/twin/``); else the shared studios-level store. A twin
    is never written without a consent record (enforced in the twin skill/CLI).
    """
    docket = docket_root()
    if docket:
        return docket / "twin"
    return Path.home() / "context" / "studios" / "twin"


def docket_session() -> str | None:
    """The production-session a render belongs to, when inside a docket."""
    return os.environ.get("STUDIOS_DOCKET_SESSION") or None


PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent  # .../motion/
TEMPLATES = PLUGIN_ROOT / "templates"
FORMATS = PLUGIN_ROOT / "formats"
RESOURCES = PLUGIN_ROOT / "resources"
SCHEMAS = Path(__file__).resolve().parent / "schemas"
