"""Session folder management + semver versioning."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import formats as formats_mod
from . import resolve_context_root


def session_root(slug: str, name: str) -> Path:
    return resolve_context_root() / slug / "outputs" / name


def init(slug: str, name: str, source: Path, fmt: str) -> Path:
    """Create the session folder structure, lock in a format, and copy source.

    `fmt` is a format slug (e.g. `pitch-pdf`); it is validated against the format
    contracts and stored in version.json so every later step renders and QAs the
    same locked format. Returns the session root path.
    """
    errors = formats_mod.validate(fmt)
    if errors:
        raise ValueError(
            f"invalid format '{fmt}':\n  "
            + "\n  ".join(errors)
            + "\n  (run `studio formats list` to see valid slugs)"
        )

    root = session_root(slug, name)
    if root.exists():
        # Idempotent: don't blow it away, just make sure subfolders exist.
        # The user gets a new version on next render rather than overwriting.
        pass
    (root / "inputs").mkdir(parents=True, exist_ok=True)
    (root / "outputs").mkdir(parents=True, exist_ok=True)
    (root / "qa").mkdir(parents=True, exist_ok=True)

    dest = root / "inputs" / "source.md"
    shutil.copy2(source, dest)

    version_json = root / "version.json"
    if not version_json.exists():
        version_json.write_text(
            json.dumps(
                {
                    "brand": slug,
                    "session": name,
                    "format": fmt,
                    "source_filename": source.name,
                    "created": datetime.now(timezone.utc).isoformat(),
                    "current": "0.0.0",
                    "history": [],
                },
                indent=2,
            )
        )
    return root


def read_state(session_path: Path) -> dict:
    return json.loads((session_path / "version.json").read_text())


def write_state(session_path: Path, state: dict) -> None:
    (session_path / "version.json").write_text(json.dumps(state, indent=2))


def bump(current: str, kind: str) -> str:
    """Semver bump. 'patch'|'minor'|'major'. 0.0.0 always jumps to 1.0.0."""
    parts = [int(p) for p in current.split(".")]
    while len(parts) < 3:
        parts.append(0)
    if current == "0.0.0":
        return "1.0.0"
    major, minor, patch = parts
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def next_version(session_path: Path, kind: str) -> str:
    state = read_state(session_path)
    return bump(state["current"], kind)


def record_render(
    session_path: Path, version: str, formats: list[str], outputs: dict[str, Path]
) -> None:
    state = read_state(session_path)
    state["current"] = version
    state["history"].append(
        {
            "version": version,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "formats": formats,
            "outputs": {fmt: str(p) for fmt, p in outputs.items()},
        }
    )
    write_state(session_path, state)
