"""Per-engagement analytics store."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from . import SCHEMAS, analytics_root, load_yaml

ANALYSIS_FILE = "_analysis.yml"
VERSION_FILE = "version.json"
BRIEF_FILE = "brief.md"
STATUSES = ("draft", "drafting", "reviewing", "approved")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _schema() -> dict:
    return json.loads((SCHEMAS / "analysis.schema.json").read_text())


def _validate(data: dict) -> list[str]:
    validator = Draft202012Validator(_schema())
    return [
        (".".join(str(p) for p in e.absolute_path) or "<root>") + ": " + e.message
        for e in sorted(
            validator.iter_errors(data), key=lambda e: list(e.absolute_path)
        )
    ]


def engagement_dir(slug: str) -> Path:
    return analytics_root() / slug


def analysis_path(slug: str) -> Path:
    return engagement_dir(slug) / ANALYSIS_FILE


def version_path(slug: str) -> Path:
    return engagement_dir(slug) / VERSION_FILE


def brief_path(slug: str) -> Path:
    return engagement_dir(slug) / BRIEF_FILE


def engagement_exists(slug: str) -> bool:
    return version_path(slug).is_file()


def scaffold(slug: str, *, brief: Path | None = None) -> dict:
    if engagement_exists(slug):
        raise ValueError(
            f"engagement '{slug}' already exists at {engagement_dir(slug)}"
        )
    engagement_dir(slug).mkdir(parents=True, exist_ok=True)
    (engagement_dir(slug) / "viz").mkdir(parents=True, exist_ok=True)
    if brief and brief.is_file():
        shutil.copy2(brief, brief_path(slug))
    data = {
        "engagement": slug,
        "status": "draft",
        "created": _now(),
        "current": "0.0.0",
        "history": [],
    }
    write_version(slug, data)
    return data


def read_analysis(slug: str) -> dict:
    if not analysis_path(slug).is_file():
        raise FileNotFoundError(
            f"no analysis for '{slug}' — run "
            f"`analytics analysis materialise --engagement {slug}`"
        )
    return load_yaml(analysis_path(slug).read_text())


def write_analysis(slug: str, data: dict) -> dict:
    errs = _validate(data)
    if errs:
        raise ValueError("invalid analysis:\n  " + "\n  ".join(errs))
    if not engagement_exists(slug):
        raise FileNotFoundError(
            f"no engagement '{slug}' — run "
            f"`analytics analysis new --engagement {slug}`"
        )
    data = dict(data)
    data["engagement"] = slug
    data.setdefault("provenance", {})["materialised"] = _now()
    data["provenance"].setdefault("materialised_by", "analytics-studio")
    analysis_path(slug).write_text(yaml.safe_dump(data, sort_keys=False))
    return data


def read_version(slug: str) -> dict:
    return json.loads(version_path(slug).read_text())


def write_version(slug: str, data: dict) -> None:
    version_path(slug).parent.mkdir(parents=True, exist_ok=True)
    version_path(slug).write_text(json.dumps(data, indent=2) + "\n")


def bump(slug: str, *, level: str = "patch") -> str:
    data = read_version(slug)
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
    write_version(slug, data)
    return new_ver


def set_status(slug: str, status: str) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
    data = read_version(slug)
    data["status"] = status
    write_version(slug, data)
    return data


def list_engagements() -> list[str]:
    root = analytics_root()
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if (p / VERSION_FILE).is_file())
