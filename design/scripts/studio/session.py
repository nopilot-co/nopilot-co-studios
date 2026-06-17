"""Session folder management + semver versioning."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import docket_root, docket_session
from . import config as config_mod
from . import formats as formats_mod
from . import resolve_context_root
from .uuid_util import mint_production_uuid


def session_root(slug: str, name: str) -> Path:
    # Precedence:
    # 1. Inside a docket with a named production-session, nest the render session
    #    under it (<root>/<session>/renders/<name>).
    # 2. The slug's persistent working folder (studio.config) → <wf>/<name>.
    # 3. Legacy per-brand layout (<slug>/outputs/<name>).
    droot, dsession = docket_root(), docket_session()
    if droot is not None and dsession:
        return droot / dsession / "renders" / name
    wf = config_mod.working_folder(slug)
    if wf is not None:
        return wf / name
    return resolve_context_root() / slug / "outputs" / name


def init(
    slug: str, name: str, source: Path, fmt: str, design_system: str | None = None
) -> Path:
    """Create the session folder structure, lock in a format, and copy source.

    `fmt` is a format slug (e.g. `pitch-pdf`); it is validated against the format
    contracts and stored in version.json so every later step renders and QAs the
    same locked format. `design_system` optionally locks a visual system
    (`resources/design-systems/<slug>`); render layers its tokens under the brand.
    Returns the session root path.
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
                    "design_system": design_system,
                    "source_filename": source.name,
                    "production_uuid": mint_production_uuid(),
                    "created": datetime.now(timezone.utc).isoformat(),
                    "current": "0.0.0",
                    "history": [],
                },
                indent=2,
            )
        )
    else:
        # Idempotent re-init: ensure ADR-0001 production_uuid without clobbering.
        state = read_state(root)
        if not state.get("production_uuid"):
            state["production_uuid"] = mint_production_uuid()
            write_state(root, state)
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
    session_path: Path,
    version: str,
    formats: list[str],
    outputs: dict[str, Path],
    built_against: dict | None = None,
    data: list | None = None,
) -> None:
    """Append a render to history and stamp built_against on state + history.

    ``built_against`` is the provenance dict from
    ``formats.resolve_for_session()``. It identifies *which contract* the
    artifact was rendered against — one version of the truth per asset (ADR-005,
    #101). Persisted twice for convenience: at session root for the latest
    render, and on the history entry for the per-version record.

    ``data`` is the normalised-CSV sidecar manifest from ``viz_data.scan_session``
    — one entry per visualisation in the source ({viz_id, type, family, files[],
    rows, page_key, engine, rendered}). Persisted the same way (latest at root,
    per-version in history) so a downstream data editor can find the CSV behind
    each viz. Empty/None when the source has no visualisations.
    """
    state = read_state(session_path)
    state["current"] = version
    entry: dict = {
        "version": version,
        "rendered_at": datetime.now(timezone.utc).isoformat(),
        "formats": formats,
        "outputs": {fmt: str(p) for fmt, p in outputs.items()},
    }
    if built_against is not None:
        entry["built_against"] = built_against
        state["built_against"] = built_against
    if data:
        entry["data"] = data
        state["data"] = data
    state["history"].append(entry)
    write_state(session_path, state)
