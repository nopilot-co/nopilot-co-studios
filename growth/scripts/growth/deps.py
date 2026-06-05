"""``growth doctor`` — wiring report."""

from __future__ import annotations

from . import __version__, growth_root
from . import store


def doctor() -> dict:
    return {
        "version": __version__,
        "growth_root": str(growth_root()),
        "engagement_count": len(store.list_engagements()),
    }
