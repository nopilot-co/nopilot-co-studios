"""``engagement doctor`` — report whether engagement tooling is wired up."""

from __future__ import annotations

import shutil
from pathlib import Path

from . import __version__


def _which(name: str) -> str | None:
    return shutil.which(name)


def doctor() -> dict:
    """Return readiness for engagement manifest maintenance."""
    repo_root = Path(__file__).resolve().parents[2]
    engagement_cli = _which("engagement")
    planner_cli = _which("planner")
    studio_cli = _which("studio")
    return {
        "version": __version__,
        "engagement_cli": engagement_cli,
        "planner_cli": planner_cli,
        "studio_cli": studio_cli,
        "manifest_schema": str(
            repo_root / "scripts" / "engagement" / "schemas" / "engagement.schema.json"
        ),
    }
