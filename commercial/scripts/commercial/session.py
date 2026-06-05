"""Per-deal `check-commercials` sessions: scaffold, version, status.

Mirrors `audience/scripts/audience/session.py` for the per-critique session
shape: ``sessions/<deal-slug>/`` with ``inputs/`` + ``review/v<ver>/``.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import commercial_root, load_yaml

STATUSES = ("draft", "reviewing", "reviewed", "blocked", "signed-off")
VERSION_FILE = "version.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sessions_root() -> Path:
    return commercial_root() / "sessions"


def session_dir(slug: str) -> Path:
    return sessions_root() / slug


def version_path(slug: str) -> Path:
    return session_dir(slug) / VERSION_FILE


def exists(slug: str) -> bool:
    return version_path(slug).is_file()


def _read_version(slug: str) -> dict:
    return json.loads(version_path(slug).read_text())


def _write_version(slug: str, data: dict) -> None:
    version_path(slug).parent.mkdir(parents=True, exist_ok=True)
    version_path(slug).write_text(json.dumps(data, indent=2) + "\n")


def new(slug: str, *, deal_file: Path, brief: Path | None = None) -> dict:
    """Create a new check-commercials session. Idempotent on the session
    folder; refuses to clobber an existing version.json."""
    if exists(slug):
        raise ValueError(
            f"session '{slug}' already exists at {session_dir(slug)} "
            "— pick a new --deal-slug or re-version manually"
        )
    inputs = session_dir(slug) / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    target = inputs / "deal.yml"
    shutil.copy2(deal_file, target)
    if brief and brief.is_file():
        shutil.copy2(brief, inputs / "brief.md")
    data = {
        "session": slug,
        "deal": str(target),
        "status": "draft",
        "created": _now(),
        "current": "0.0.0",
        "history": [],
    }
    _write_version(slug, data)
    return data


def bump(slug: str, *, level: str = "patch") -> str:
    """Bump the session version (semver). Default: patch."""
    data = _read_version(slug)
    cur = data.get("current") or "0.0.0"
    major, minor, patch = (int(x) for x in cur.split("."))
    if level == "major":
        major, minor, patch = major + 1, 0, 0
    elif level == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    new_ver = f"{major}.{minor}.{patch}"
    data.setdefault("history", []).append({"version": new_ver, "at": _now()})
    data["current"] = new_ver
    _write_version(slug, data)
    return new_ver


def review_dir(slug: str, version: str | None = None) -> Path:
    if version is None:
        version = _read_version(slug)["current"]
    return session_dir(slug) / "review" / f"v{version}"


def write_scores(slug: str, scores_yaml: dict) -> Path:
    rd = review_dir(slug)
    rd.mkdir(parents=True, exist_ok=True)
    p = rd / "scores.yml"
    p.write_text(yaml.safe_dump(scores_yaml, sort_keys=False))
    return p


def write_scorecard(slug: str, scorecard: dict) -> Path:
    rd = review_dir(slug)
    rd.mkdir(parents=True, exist_ok=True)
    p = rd / "scorecard.json"
    p.write_text(json.dumps(scorecard, indent=2) + "\n")
    return p


def read_deal(slug: str) -> dict:
    return load_yaml((session_dir(slug) / "inputs" / "deal.yml").read_text())


def set_status(slug: str, status: str) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
    data = _read_version(slug)
    data["status"] = status
    _write_version(slug, data)
    return data


def list_sessions() -> list[str]:
    root = sessions_root()
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if (p / VERSION_FILE).is_file())
