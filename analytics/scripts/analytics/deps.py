"""``analytics doctor`` — wiring report."""

from __future__ import annotations

from . import __version__, analytics_root
from . import store


def doctor() -> dict:
    return {
        "version": __version__,
        "analytics_root": str(analytics_root()),
        "engagement_count": len(store.list_engagements()),
    }
