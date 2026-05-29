"""Review session folders + semver versioning + status.

A session is one target asset × one review. ``new`` records the target (a file
copied into the session, or a URL), the brief it must fulfil, the brand, and the
ICP into version.json, and scaffolds the review inputs. Each capture advances the
version; a re-review of a revised asset is a new version in the same session.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import CONTEXT_ROOT

STATUSES = ["draft", "reviewing", "reviewed", "signed-off", "rejected"]


def session_root(name: str) -> Path:
    return CONTEXT_ROOT / name


def _is_url(target: str) -> bool:
    return target.startswith(("http://", "https://"))


def _ingest_target(root: Path, target: str) -> tuple[str, str]:
    """Copy a file target into the session (or record a URL). Returns (kind, ref)."""
    if _is_url(target):
        (root / "inputs" / "target" / "url.txt").write_text(target.strip() + "\n")
        return "url", target.strip()
    src = Path(target).expanduser()
    if not src.exists():
        raise ValueError(f"target not found: {target}")
    dest = root / "inputs" / "target" / src.name
    shutil.copy2(src, dest)
    return (src.suffix.lstrip(".").lower() or "file"), str(dest)


def new(
    name: str,
    target: str,
    brief: str | None = None,
    brand: str | None = None,
    icp: str | None = None,
) -> Path:
    root = session_root(name)
    (root / "inputs" / "target").mkdir(parents=True, exist_ok=True)
    (root / "capture").mkdir(parents=True, exist_ok=True)
    (root / "review").mkdir(parents=True, exist_ok=True)

    target_kind, target_ref = _ingest_target(root, target)

    brief_path = root / "inputs" / "brief.md"
    if brief:
        shutil.copy2(Path(brief).expanduser(), brief_path)
    elif not brief_path.exists():
        brief_path.write_text("<!-- paste the brief this asset must fulfil -->\n")

    icp_path = root / "inputs" / "icp.md"
    if icp:
        shutil.copy2(Path(icp).expanduser(), icp_path)
    elif not icp_path.exists():
        icp_path.write_text(
            "<!-- describe the target audience / ICP this asset speaks to -->\n"
        )

    version_json = root / "version.json"
    if not version_json.exists():
        version_json.write_text(
            json.dumps(
                {
                    "session": name,
                    "target": target_ref,
                    "target_kind": target_kind,
                    "brand": brand,
                    "status": "draft",
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


def record_capture(session_path: Path, version: str, images: list[Path]) -> None:
    state = read_state(session_path)
    state["current"] = version
    state["history"].append(
        {
            "version": version,
            "event": "capture",
            "at": datetime.now(timezone.utc).isoformat(),
            "images": [str(p) for p in images],
        }
    )
    write_state(session_path, state)


def record_score(session_path: Path, version: str, scorecard: dict) -> None:
    state = read_state(session_path)
    state["history"].append(
        {
            "version": version,
            "event": "score",
            "at": datetime.now(timezone.utc).isoformat(),
            "verdict": scorecard.get("verdict"),
            "overall": scorecard.get("overall"),
        }
    )
    write_state(session_path, state)


def set_status(session_path: Path, status: str) -> None:
    state = read_state(session_path)
    state["status"] = status
    write_state(session_path, state)
