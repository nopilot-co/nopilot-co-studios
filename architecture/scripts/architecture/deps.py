"""``arch doctor`` — wiring report."""

from __future__ import annotations

from . import __version__, architecture_root
from . import design_bridge
from . import store


def doctor() -> dict:
    return {
        "version": __version__,
        "architecture_root": str(architecture_root()),
        "engagement_count": len(store.list_engagements()),
        "design_reachable": design_bridge.reachable(),
    }
