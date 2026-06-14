"""Critique sessions + versioning + the score tie-in.

A session is one target artifact critiqued **as one reader**. ``new`` records the
target, brief, and the audience slug; the audience-critique skill writes
``review/v<ver>/scores.yml`` (each rubric test + the reader-fit dimension); ``score``
hands that to the nitpicker engine (via ``nit_bridge``) using the slug's rubric and
writes the scorecard + the ranked strengthening-areas deliverable.

Mirrors ``nit/session.py``; sessions live under the reader model's own tree
(``<store>/<slug>/sessions/<name>/``) so they never collide with model slugs.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import nit_bridge, rubric, store

STATUSES = ["draft", "reviewing", "reviewed", "signed-off", "rejected"]


def session_root(slug: str, name: str) -> Path:
    return store.slug_dir(slug) / "sessions" / name


def _is_url(target: str) -> bool:
    return target.startswith(("http://", "https://"))


def _ingest_target(root: Path, target: str) -> tuple[str, str]:
    if _is_url(target):
        (root / "inputs" / "target").mkdir(parents=True, exist_ok=True)
        (root / "inputs" / "target" / "url.txt").write_text(target.strip() + "\n")
        return "url", target.strip()
    src = Path(target).expanduser()
    if not src.exists():
        raise ValueError(f"target not found: {target}")
    dest = root / "inputs" / "target" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return (src.suffix.lstrip(".").lower() or "file"), str(dest)


def new(slug: str, name: str, target: str, brief: str | None = None) -> Path:
    if not store.exists(slug):
        raise ValueError(
            f"no reader model '{slug}' — build one first (`audience persona new`)"
        )
    root = session_root(slug, name)
    (root / "inputs" / "target").mkdir(parents=True, exist_ok=True)
    (root / "review" / "v1.0.0").mkdir(parents=True, exist_ok=True)

    target_kind, target_ref = _ingest_target(root, target)

    brief_path = root / "inputs" / "brief.md"
    if brief:
        shutil.copy2(Path(brief).expanduser(), brief_path)
    elif not brief_path.exists():
        brief_path.write_text(
            "<!-- what was this artifact meant to do? (optional) -->\n"
        )

    version_json = root / "version.json"
    if not version_json.exists():
        version_json.write_text(
            json.dumps(
                {
                    "session": name,
                    "audience": slug,
                    "target": target_ref,
                    "target_kind": target_kind,
                    "status": "draft",
                    "created": datetime.now(timezone.utc).isoformat(),
                    "current": "1.0.0",
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


def set_status(session_path: Path, status: str) -> None:
    state = read_state(session_path)
    state["status"] = status
    write_state(session_path, state)


def score(session_path: Path, version: str | None = None) -> dict:
    """Aggregate the reader-fit scores via the nitpicker engine and write the
    scorecard + ranked strengthening-areas. Returns the scorecard dict."""
    state = read_state(session_path)
    slug = state["audience"]
    version = version or state["current"]

    review_dir = session_path / "review" / f"v{version}"
    scores_path = review_dir / "scores.yml"
    if not scores_path.exists():
        raise FileNotFoundError(
            f"no scores at {scores_path}\n"
            "  (the audience-critique skill writes per-rubric-test + reader-fit "
            "scores there)"
        )

    rubric_path = rubric.rubric_path(slug)
    if not rubric_path.is_file():
        raise FileNotFoundError(
            f"no rubric for '{slug}' — run `audience rubric derive` first"
        )

    card = nit_bridge.aggregate(scores_path, rubric_path)
    (review_dir / "scorecard.json").write_text(json.dumps(card, indent=2))
    _write_strengthening(review_dir, slug, card)
    _record(session_path, version, card)
    return card


def _write_strengthening(review_dir: Path, slug: str, card: dict) -> None:
    """Ranked target strengthening areas — the lowest-norm items first (where the
    reader's needs are least met)."""
    items = sorted(card.get("items", []), key=lambda i: i["norm"])
    lines = [
        f"# Strengthening areas — reader: {slug}",
        "",
        f"**Reader-fit verdict:** {card['verdict'].upper()}   "
        f"**Overall:** {card['overall']}/100",
    ]
    if card.get("gates_failed"):
        lines.append(f"**Unmet must-haves (gates):** {', '.join(card['gates_failed'])}")
    lines += ["", "## Target areas (most → least urgent)", ""]
    weak = [i for i in items if i["status"] != "pass"]
    if not weak:
        lines.append("- None — the work meets this reader's needs across the rubric.")
    for i in weak:
        gate = " · **must-have**" if i["gate"] else ""
        lines.append(
            f"- **{i['key']}** — {i['score']}/{i['max']} ({i['status']}){gate}: "
            "<!-- the critique skill names the concrete gap + how to strengthen it -->"
        )
    (review_dir / "strengthening-areas.md").write_text("\n".join(lines) + "\n")


def _record(session_path: Path, version: str, card: dict) -> None:
    state = read_state(session_path)
    state["history"].append(
        {
            "version": version,
            "event": "score",
            "at": datetime.now(timezone.utc).isoformat(),
            "verdict": card.get("verdict"),
            "overall": card.get("overall"),
        }
    )
    write_state(session_path, state)
