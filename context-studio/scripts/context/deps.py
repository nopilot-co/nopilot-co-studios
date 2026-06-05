"""``context doctor`` — per-tool reachability report."""

from __future__ import annotations

from . import __version__, context_root
from . import bridge
from . import store


def doctor() -> dict:
    reach = bridge.reachability_report()
    return {
        "version": __version__,
        "context_root": str(context_root()),
        "engagement_count": len(store.list_engagements()),
        "tools_reachable": reach,
        "tools_ok": sum(1 for v in reach.values() if v),
        "tools_missing": [k for k, v in reach.items() if not v],
    }
