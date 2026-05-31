"""design-studio orchestrator.

Deterministic glue around Quarto + Typst for brand-aware multi-format rendering.
LLM-driven judgment lives in the plugin's skills (markdown); this package handles
file ops, subprocess orchestration, versioning, validation, and rasterization.
"""

__version__ = "0.1.0"

import os
from pathlib import Path


def docket_root() -> Path | None:
    """The explicit production-docket root, if the caller set one.

    When ``$STUDIOS_DOCKET_ROOT`` is set, the studio is operating inside a
    self-contained **production docket**: brand *and* session outputs live under
    that root with no external filesystem dependency (see the docket spec).
    Resolved on every call so a long-lived host (server modes) can switch
    dockets per request, not just per process.
    """
    env = os.environ.get("STUDIOS_DOCKET_ROOT")
    return Path(env).expanduser().resolve() if env else None


def resolve_context_root(studio_name: str = "design") -> Path:
    """Resolve where this studio's session outputs live. Override chain:

    1. ``$STUDIOS_DOCKET_ROOT`` (if set) → the docket root itself — a
       self-contained production docket.
    2. ``$STUDIOS_PROJECT_ROOT`` → ``<env>/agents/claude/outbox/<studio>/``.
    3. Walk upward from ``cwd`` for ``.wip/config.yml`` →
       ``<found>/agents/claude/outbox/<studio>/`` (co-located with the project).
    4. Legacy global ``~/context/studios/<studio>/`` (backward compatibility).
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
    """Base directory holding per-slug Brand Dockets.

    Docket-local and **authoritative** when a docket root is set
    (``<docket>/brand/``) — the docket carries its own brand with no external
    dependency. Otherwise the shared studios-level store
    (``~/context/studios/brand/``), used across projects. Resolved per call so
    the override applies in-process, not only at import.
    """
    docket = docket_root()
    if docket:
        return docket / "brand"
    return Path.home() / "context" / "studios" / "brand"


PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent  # .../design/

TEMPLATES = PLUGIN_ROOT / "templates"
FORMATS = PLUGIN_ROOT / "formats"
SCHEMAS = Path(__file__).resolve().parent / "schemas"
