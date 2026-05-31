"""Production docket scaffolding + manifests (issues #8, #10, #12).

A *production docket* is a self-contained, portable folder tree under a chosen
``production_root``: shared ``specs/``, ``assets/``, ``brand/`` plus one or more
``<production-session>/`` folders. ``init_docket`` builds the tree; this module
also owns the two manifests (production-level + session-level) and their
JSON-Schema validation, and the brand-import provenance record.

The studio reaches a docket by running with ``$STUDIOS_DOCKET_ROOT`` pointed at
the ``production_root`` (see :func:`studio.docket_root`), which makes brand and
session outputs land inside it with no external dependency.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from . import SCHEMAS

PRODUCTION_MANIFEST = "production-manifest.json"
SESSION_MANIFEST = "session-manifest.json"

_GITIGNORE = """\
# Production docket — commit the source of truth (specs, brand, content,
# manifests, logs); ignore regenerable rendered binaries (issue #12).
**/outputs/
_render/
"""

_CONTENT_DEFAULTS = {
    "author": "",
    "title_format": "{title}",
    "footer": "",
    "address": "",
}

_SCHEMA_FILES = {
    "production": "production-manifest.schema.json",
    "session": "session-manifest.schema.json",
}


# ----------------------------------------------------------------- manifests
def _schema(kind: str) -> dict:
    return json.loads((SCHEMAS / _SCHEMA_FILES[kind]).read_text())


def validate_manifest(kind: str, data: dict) -> list[str]:
    validator = Draft202012Validator(_schema(kind))
    return [
        ("/".join(map(str, e.path)) + ": " + e.message) if e.path else e.message
        for e in sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    ]


def read_manifest(path: Path) -> dict:
    return json.loads(path.read_text())


def write_manifest(path: Path, kind: str, data: dict) -> None:
    errors = validate_manifest(kind, data)
    if errors:
        raise ValueError(f"invalid {kind}-manifest:\n  " + "\n  ".join(errors))
    path.write_text(json.dumps(data, indent=2) + "\n")


# ----------------------------------------------------------------- scaffolding
def init_docket(
    production_root: Path, brand: str | None = None, session: str | None = None
) -> Path:
    """Create (or top up) the docket tree under ``production_root``. Idempotent."""
    root = production_root.expanduser()
    (root / "specs" / "formats").mkdir(parents=True, exist_ok=True)
    (root / "assets").mkdir(parents=True, exist_ok=True)
    (root / "brand").mkdir(parents=True, exist_ok=True)

    _write_if_absent(root / ".gitignore", _GITIGNORE)
    _write_if_absent(root / "CLAUDE.md", _claude_md(root.name))
    _write_if_absent(root / "README.md", _readme_md(root.name))
    _write_if_absent(root / "nopilot-co-studios-plugin.md", _plugin_md())
    _write_if_absent(
        root / "specs" / "content-defaults.yaml",
        yaml.safe_dump(_CONTENT_DEFAULTS, sort_keys=False),
    )

    sessions: list[str] = []
    if session:
        init_session(root, session)
        sessions.append(session)

    manifest_path = root / PRODUCTION_MANIFEST
    if manifest_path.exists():
        data = read_manifest(manifest_path)
        for s in sessions:
            if s not in data.setdefault("sessions", []):
                data["sessions"].append(s)
    else:
        data = {
            "schema_version": "1.0",
            "plugin": "nopilot-co-studios",
            "brand_dockets": [],
            "specs": "specs/",
            "assets": "assets/",
            "sessions": sessions,
        }
    if brand and brand not in [d.get("slug") for d in data.get("brand_dockets", [])]:
        # Recorded as intended; brand-ingest --import-from fills in provenance.
        pass
    write_manifest(manifest_path, "production", data)
    return root


def init_session(root: Path, name: str) -> Path:
    """Create a ``<production-session>/`` with its inputs/content/outputs/logs + manifest."""
    s = root / name
    for sub in ("inputs", "content", "outputs", "logs"):
        (s / sub).mkdir(parents=True, exist_ok=True)
    _write_if_absent(s / "inputs" / "brief.md", "# Brief\n\n")
    _write_if_absent(s / "inputs" / "response-to-brief.md", "# Response to brief\n\n")
    _write_if_absent(s / "logs" / "production.log", "")
    sm_path = s / SESSION_MANIFEST
    if not sm_path.exists():
        write_manifest(
            sm_path,
            "session",
            {
                "schema_version": "1.0",
                "session": name,
                "inputs": {
                    "brief": "inputs/brief.md",
                    "response_to_brief": "inputs/response-to-brief.md",
                },
                "content": [],
                "outputs": [],
            },
        )
    return s


# ----------------------------------------------------------------- provenance
def register_brand_import(
    root: Path, slug: str, *, imported_from: str | None, content_hash: str
) -> None:
    """Record a one-shot brand import in the production-manifest (origin = log only)."""
    manifest_path = root / PRODUCTION_MANIFEST
    if not manifest_path.exists():
        return
    data = read_manifest(manifest_path)
    entry = {
        "slug": slug,
        "path": f"brand/{slug}",
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": content_hash,
    }
    if imported_from:
        entry["imported_from"] = imported_from
    data["brand_dockets"] = [
        d for d in data.get("brand_dockets", []) if d.get("slug") != slug
    ] + [entry]
    write_manifest(manifest_path, "production", data)


def hash_dir(path: Path) -> str:
    """Stable content hash of a directory tree (path + bytes of every file)."""
    h = hashlib.sha256()
    for f in sorted(p for p in path.rglob("*") if p.is_file()):
        h.update(f.relative_to(path).as_posix().encode())
        h.update(f.read_bytes())
    return "sha256:" + h.hexdigest()


# ----------------------------------------------------------------- helpers
def _write_if_absent(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content)


def _claude_md(name: str) -> str:
    return (
        f"# Production docket: {name}\n\n"
        "Self-contained, portable production tree built by the nopilot-co-studios\n"
        "creative-director. Brand, specs, content, and outputs all live here — no\n"
        "external filesystem dependency.\n\n"
        "- `production-manifest.json` — what this folder is + the session list.\n"
        "- `brand/<slug>/` — the authoritative Brand Docket (render reads only this).\n"
        "- `specs/` — content-defaults + format overrides.\n"
        "- `<session>/` — one production-session (inputs / content / outputs / logs).\n"
    )


def _readme_md(name: str) -> str:
    return (
        f"# {name}\n\n"
        "Production docket created by nopilot-co-studios. See `CLAUDE.md` for the\n"
        "layout and `nopilot-co-studios-plugin.md` for how the plugin uses it.\n"
    )


def _plugin_md() -> str:
    return (
        "# nopilot-co-studios\n\n"
        "This docket is produced and consumed by the nopilot-co-studios plugin\n"
        "(design + messaging studios, orchestrated by the creative-director).\n\n"
        "The studio operates on this docket by running with `$STUDIOS_DOCKET_ROOT`\n"
        "set to this folder, so brand and session outputs stay self-contained.\n"
    )
