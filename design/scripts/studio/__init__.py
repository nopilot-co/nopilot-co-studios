"""design-studio orchestrator.

Deterministic glue around Quarto + Typst for brand-aware multi-format rendering.
LLM-driven judgment lives in the plugin's skills (markdown); this package handles
file ops, subprocess orchestration, versioning, validation, and rasterization.
"""

__version__ = "0.1.0"

import os
from pathlib import Path


def resolve_context_root(studio_name: str = "design") -> Path:
    """Resolve where this studio's session outputs live, with this override chain:

    1. ``$STUDIOS_PROJECT_ROOT`` env var (if set) →
       ``<env>/agents/claude/outbox/<studio>/``
    2. Walk upward from ``cwd`` looking for ``.wip/config.yml`` — if found,
       use ``<found>/agents/claude/outbox/<studio>/``
    3. Fall back to the legacy global location
       ``~/context/studios/<studio>/`` (preserves backward compatibility).

    The intent: when the studio runs inside a ``~/context/<repo>/`` project that
    has been bootstrapped with ``wip init``, its outputs land under that repo's
    ``agents/claude/outbox/`` so they are co-located with the project they
    belong to. Brands stay shared at ``~/context/studios/brand/`` regardless —
    brand identity is cross-project.
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


CONTEXT_ROOT = resolve_context_root("design")
# Brand is a studios-level entity (shared by design + messaging), not design-owned.
# It lives here; render sessions stay under CONTEXT_ROOT/<slug>/outputs/. The legacy
# design-owned location (CONTEXT_ROOT/<slug>/brand/) is still read for back-compat —
# see brand.brand_root(). (SPEC §12.1, resolved.)
#
# Note: BRAND_ROOT is intentionally NOT per-project. Brands are cross-project
# identities; a single brand may render assets in many project repos.
BRAND_ROOT = Path.home() / "context" / "studios" / "brand"
PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent  # .../design/

TEMPLATES = PLUGIN_ROOT / "templates"
FORMATS = PLUGIN_ROOT / "formats"
SCHEMAS = Path(__file__).resolve().parent / "schemas"
