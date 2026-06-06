"""``delivery doctor`` — wiring report.

The delivery studio is largely self-contained. Optional integration with the
commercial studio's rate-card lets `delivery plan cost` derive per-phase
cost / revenue / margin; this module reports whether the `commercial` CLI is
reachable.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from . import __version__, delivery_root
from . import store


def _commercial_binary() -> str | None:
    on_path = shutil.which("commercial")
    if on_path:
        return on_path
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "commercial" / ".venv" / "bin" / "commercial"
        if cand.is_file():
            return str(cand)
    return None


def commercial_reachable() -> bool:
    return _commercial_binary() is not None


def doctor() -> dict:
    return {
        "version": __version__,
        "delivery_root": str(delivery_root()),
        "engagement_count": len(store.list_engagements()),
        "commercial_reachable": commercial_reachable(),
    }
