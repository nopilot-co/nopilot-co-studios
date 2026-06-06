"""Per-engagement context store + manifest CRUD.

The studio is infrastructural; the store is a thin wrapper around the
tool-bench's outputs (sources/ batch directory + themes/ + themes.json +
theme-manifest.json), plus a studio-level manifest that records which
tools ran when with what args.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from . import SCHEMAS, context_root

MANIFEST_FILE = "manifest.json"
VERSION_FILE = "version.json"
SOURCES_DIR = "sources"
THEMES_DIR = "themes"
STATUSES = ("draft", "ingesting", "mapped", "ready")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _schema() -> dict:
    return json.loads((SCHEMAS / "manifest.schema.json").read_text())


def _validate(data: dict) -> list[str]:
    validator = Draft202012Validator(_schema())
    return [
        (".".join(str(p) for p in e.absolute_path) or "<root>") + ": " + e.message
        for e in sorted(
            validator.iter_errors(data), key=lambda e: list(e.absolute_path)
        )
    ]


# ----------------------------------------------------------------- engagement dirs


def engagement_dir(slug: str) -> Path:
    return context_root() / slug


def manifest_path(slug: str) -> Path:
    return engagement_dir(slug) / MANIFEST_FILE


def version_path(slug: str) -> Path:
    return engagement_dir(slug) / VERSION_FILE


def sources_dir(slug: str) -> Path:
    return engagement_dir(slug) / SOURCES_DIR


def themes_dir(slug: str) -> Path:
    return engagement_dir(slug) / THEMES_DIR


def engagement_exists(slug: str) -> bool:
    return version_path(slug).is_file()


# ----------------------------------------------------------------- scaffold


def scaffold(slug: str) -> dict:
    if engagement_exists(slug):
        raise ValueError(
            f"engagement '{slug}' already exists at {engagement_dir(slug)}"
        )
    sources_dir(slug).mkdir(parents=True, exist_ok=True)
    themes_dir(slug).mkdir(parents=True, exist_ok=True)
    write_manifest(
        slug,
        {
            "engagement": slug,
            "created": _now(),
            "runs": [],
        },
    )
    data = {
        "engagement": slug,
        "status": "draft",
        "created": _now(),
        "current": "0.0.0",
        "history": [],
    }
    write_version(slug, data)
    return data


# ----------------------------------------------------------------- manifest I/O


def read_manifest(slug: str) -> dict:
    if not manifest_path(slug).is_file():
        raise FileNotFoundError(
            f"no manifest for '{slug}' — run `context engagement new --engagement {slug}`"
        )
    return json.loads(manifest_path(slug).read_text())


def write_manifest(slug: str, data: dict) -> dict:
    errs = _validate(data)
    if errs:
        raise ValueError("invalid manifest:\n  " + "\n  ".join(errs))
    manifest_path(slug).parent.mkdir(parents=True, exist_ok=True)
    manifest_path(slug).write_text(json.dumps(data, indent=2) + "\n")
    return data


def record_run(
    slug: str,
    *,
    tool: str,
    action: str,
    args: list[str] | None = None,
    exit_code: int = 0,
    note: str | None = None,
) -> dict:
    """Append a tool-invocation record to the manifest's ``runs[]``."""
    data = read_manifest(slug)
    entry = {
        "tool": tool,
        "action": action,
        "at": _now(),
        "exit_code": exit_code,
    }
    if args:
        entry["args"] = args
    if note:
        entry["note"] = note
    data.setdefault("runs", []).append(entry)
    write_manifest(slug, data)
    return entry


# ----------------------------------------------------------------- version


def read_version(slug: str) -> dict:
    return json.loads(version_path(slug).read_text())


def write_version(slug: str, data: dict) -> None:
    version_path(slug).parent.mkdir(parents=True, exist_ok=True)
    version_path(slug).write_text(json.dumps(data, indent=2) + "\n")


def set_status(slug: str, status: str) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
    data = read_version(slug)
    data["status"] = status
    write_version(slug, data)
    return data


def list_engagements() -> list[str]:
    root = context_root()
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if (p / VERSION_FILE).is_file())
