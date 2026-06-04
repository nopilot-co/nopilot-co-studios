"""Render a storyboard to its export(s).

S2 ships the **declarative** path (ADR-002): an animated, brand-tokenised HTML
(the embeddable preview) recorded to an H.264 MP4. **Remotion** is the optional
high-fidelity engine for the *same* storyboard — scaffolded under
``templates/remotion/`` and selected with ``engine="remotion"`` once a Node
toolchain + the project are present (detection lands with that slice).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from . import animate
from . import capture as capture_mod
from . import storyboard as storyboard_mod
from . import tokens as tokens_mod


def _stem(spec_path: Path) -> str:
    name = spec_path.name
    for suffix in (".storyboard.json", ".json"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return spec_path.stem


def select_engine(engine: str) -> str:
    """Resolve the engine. ``auto`` → remotion if its toolchain is available,
    else declarative. S2: declarative is the only wired engine."""
    if engine in ("declarative", "remotion"):
        return engine
    return "remotion" if _remotion_available() else "declarative"


def _remotion_available() -> bool:
    # A wired Remotion project + node would flip this on; not shipped in S2.
    return False


def produce(
    spec_path: Path,
    out_dir: Path | None = None,
    engine: str = "auto",
    make_video: bool = True,
) -> dict[str, Path]:
    """Render ``spec_path`` to outputs. Returns ``{export: path}``."""
    spec = storyboard_mod.load(spec_path)
    g = spec["global"]
    tok = tokens_mod.resolve(g.get("brand"), g.get("motion_system"))

    out_dir = Path(out_dir) if out_dir else spec_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = _stem(spec_path)

    eng = select_engine(engine)
    if eng == "remotion":
        raise RuntimeError(
            "the Remotion engine is scaffolded but not wired yet — use the "
            "declarative path (the default). See motion/CLAUDE.md / "
            "templates/remotion/."
        )

    outputs: dict[str, Path] = {}
    html_path = out_dir / f"{stem}.html"
    html_path.write_text(animate.render_html(spec, tok), encoding="utf-8")
    outputs["html"] = html_path

    if make_video:
        w, h = animate.stage_size(spec)
        total = storyboard_mod.total_duration(spec)
        mp4 = out_dir / f"{stem}.mp4"
        capture_mod.html_to_video(html_path, mp4, total, w, h, fps=int(g.get("fps", 30)))
        outputs["mp4"] = mp4

    return outputs
