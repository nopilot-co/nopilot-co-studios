"""messaging-studio orchestrator.

Deterministic glue for brand-voice-aware, channel-shaped communications. LLM
judgment lives in the plugin's skills (markdown); this package handles format
resolution, session/versioning, deterministic linting, and rendering.
"""

__version__ = "0.1.0"

import os
from pathlib import Path


def docket_root() -> Path | None:
    """The explicit production-docket root, if the caller set one.

    When ``$STUDIOS_DOCKET_ROOT`` is set, the studio operates inside a
    self-contained production docket (brand + sessions under that root, no
    external dependency). Same contract as the design studio. Resolved per call.
    """
    env = os.environ.get("STUDIOS_DOCKET_ROOT")
    return Path(env).expanduser().resolve() if env else None


def resolve_context_root(studio_name: str = "messaging") -> Path:
    """Resolve where this studio's session outputs live. Override chain:

    1. ``$STUDIOS_DOCKET_ROOT`` (if set) → the docket root itself.
    2. ``$STUDIOS_PROJECT_ROOT`` → ``<env>/agents/claude/outbox/<studio>/``.
    3. Walk upward from ``cwd`` for ``.wip/config.yml`` →
       ``<found>/agents/claude/outbox/<studio>/``.
    4. Legacy global ``~/context/studios/<studio>/``.

    See design/scripts/studio/__init__.py for the rationale — same contract,
    so both studios honor a docket / wip-bootstrapped layout identically.
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
    """Base directory holding per-slug Brand Dockets — docket-local and
    authoritative (``<docket>/brand/``) when a docket root is set, else the
    shared studios-level store (``~/context/studios/brand/``). Resolved per call.
    """
    docket = docket_root()
    if docket:
        return docket / "brand"
    return Path.home() / "context" / "studios" / "brand"


PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent  # .../messaging/
FORMATS = PLUGIN_ROOT / "formats"
SCHEMAS = Path(__file__).resolve().parent / "schemas"

# Brand is a studios-level entity shared with the design studio (SPEC §6, §12.1).
# Voice is resolved from the docket-local / shared brand store first (see
# brand_root_base + voice.py), then the legacy design-owned location, then the
# canonical default.
DESIGN_CONTEXT = Path.home() / "context" / "studios" / "design"  # legacy brand location
BRAND_VOICE_DEFAULT = (
    PLUGIN_ROOT.parent
    / "design"
    / "resources"
    / "brand-voice"
    / "brand-voice-default.md"
)
