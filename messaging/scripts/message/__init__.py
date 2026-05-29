"""messaging-studio orchestrator.

Deterministic glue for brand-voice-aware, channel-shaped communications. LLM
judgment lives in the plugin's skills (markdown); this package handles format
resolution, session/versioning, deterministic linting, and rendering.
"""

__version__ = "0.1.0"

import os
from pathlib import Path


def resolve_context_root(studio_name: str = "messaging") -> Path:
    """Resolve where this studio's session outputs live, with this override chain:

    1. ``$STUDIOS_PROJECT_ROOT`` env var (if set) →
       ``<env>/agents/claude/outbox/<studio>/``
    2. Walk upward from ``cwd`` for ``.wip/config.yml`` — if found, use
       ``<found>/agents/claude/outbox/<studio>/``
    3. Fall back to ``~/context/studios/<studio>/`` (legacy default).

    See design/scripts/studio/__init__.py for the rationale — same contract,
    so both studios honor a project's wip-bootstrapped layout identically.
    """
    env = os.environ.get("STUDIOS_PROJECT_ROOT")
    if env:
        return Path(env).expanduser() / "agents" / "claude" / "outbox" / studio_name

    d = Path.cwd().resolve()
    while d != d.parent:
        if (d / ".wip" / "config.yml").is_file():
            return d / "agents" / "claude" / "outbox" / studio_name
        d = d.parent

    return Path.home() / "context" / "studios" / studio_name


CONTEXT_ROOT = resolve_context_root("messaging")
PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent  # .../messaging/
FORMATS = PLUGIN_ROOT / "formats"
SCHEMAS = Path(__file__).resolve().parent / "schemas"

# Brand is a studios-level entity shared with the design studio (SPEC §6, §12.1).
# Voice is resolved from the shared brand store first, then the legacy design-owned
# location, then the canonical default (see voice.py).
#
# Note: BRAND_ROOT and DESIGN_CONTEXT are intentionally NOT per-project. Brands
# are cross-project identities; a single brand may render assets in many repos.
BRAND_ROOT = Path.home() / "context" / "studios" / "brand"
DESIGN_CONTEXT = Path.home() / "context" / "studios" / "design"  # legacy brand location
BRAND_VOICE_DEFAULT = (
    PLUGIN_ROOT.parent
    / "design"
    / "resources"
    / "brand-voice"
    / "brand-voice-default.md"
)
