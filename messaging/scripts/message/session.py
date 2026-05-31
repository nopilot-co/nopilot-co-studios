"""Message session folders + semver versioning + status.

A session is one brand × one format slug × one message. `new` locks the format
into version.json and scaffolds the composable source at inputs/message.md.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import formats as formats_mod
from . import resolve_context_root


def session_root(name: str) -> Path:
    return resolve_context_root() / name


def _stub_message(resolved: dict) -> str:
    """A front-matter + section scaffold the compose skill fills in."""
    ruleset = resolved.get("ruleset") or {}
    subject_line = 'subject: ""\n' if ruleset.get("subject_required") else ""
    sections = (resolved.get("execution_brief") or {}).get("required_sections", [])
    body = "\n\n".join(f"<!-- {s} -->" for s in sections) or "<!-- body -->"
    return (
        "---\n"
        f"{subject_line}"
        "preview: \"\"\n"
        f"channel: {resolved.get('channel')}\n"
        "status: draft\n"
        "---\n\n"
        f"{body}\n"
    )


def new(brand: str, name: str, fmt: str) -> Path:
    errors = formats_mod.validate(fmt)
    if errors:
        raise ValueError(
            f"invalid format '{fmt}':\n  "
            + "\n  ".join(errors)
            + "\n  (run `message formats list` to see valid slugs)"
        )
    resolved = formats_mod.resolve(fmt)

    root = session_root(name)
    (root / "inputs").mkdir(parents=True, exist_ok=True)
    (root / "outputs").mkdir(parents=True, exist_ok=True)
    (root / "review").mkdir(parents=True, exist_ok=True)

    msg = root / "inputs" / "message.md"
    if not msg.exists():
        msg.write_text(_stub_message(resolved))

    version_json = root / "version.json"
    if not version_json.exists():
        version_json.write_text(
            json.dumps(
                {
                    "brand": brand,
                    "session": name,
                    "format": fmt,
                    "channel": resolved.get("channel"),
                    "status": "draft",
                    "source_filename": "message.md",
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
    if current == "0.0.0":
        return "1.0.0"
    major, minor, patch = (int(p) for p in (current.split(".") + ["0", "0", "0"])[:3])
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def next_version(session_path: Path, kind: str) -> str:
    return bump(read_state(session_path)["current"], kind)


def record_render(
    session_path: Path, version: str, targets: list[str], outputs: dict
) -> None:
    state = read_state(session_path)
    state["current"] = version
    state["history"].append(
        {
            "version": version,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "targets": targets,
            "outputs": {t: str(p) for t, p in outputs.items()},
        }
    )
    write_state(session_path, state)


def set_status(session_path: Path, status: str) -> None:
    state = read_state(session_path)
    state["status"] = status
    write_state(session_path, state)
