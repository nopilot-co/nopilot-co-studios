"""Render a storyboard to its export(s).

Two engines for the *same* storyboard (ADR-002):

- **declarative** (default) — animated, brand-tokenised HTML recorded to MP4 via
  Playwright + ffmpeg. No Node; renders in any host.
- **remotion** — React/Node high-fidelity render of the storyboard via the
  project under ``templates/remotion/``. Selected with ``engine="remotion"``;
  ``node`` must be present (``motion doctor``). node_modules is installed into the
  template dir on first use and cached.

``engine="auto"`` keeps the safe default (declarative); ask for ``remotion``
explicitly when you want the high-fidelity render.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import json

from . import TEMPLATES, animate
from . import capture as capture_mod
from . import lottie as lottie_mod
from . import storyboard as storyboard_mod
from . import tokens as tokens_mod


def _stem(spec_path: Path) -> str:
    name = spec_path.name
    for suffix in (".storyboard.json", ".json"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return spec_path.stem


def _remotion_dir() -> Path:
    return TEMPLATES / "remotion"


def _remotion_available() -> bool:
    return bool(shutil.which("node")) and (_remotion_dir() / "package.json").exists()


def select_engine(engine: str) -> str:
    """Resolve the engine. ``auto`` keeps the declarative default (fast, no Node);
    ``declarative`` / ``remotion`` are explicit."""
    if engine in ("declarative", "remotion"):
        return engine
    return "declarative"


def _ensure_remotion_install(tpl: Path) -> None:
    if (tpl / "node_modules").exists():
        return
    if not shutil.which("npm"):
        raise RuntimeError("npm not found — install Node (brew install node)")
    r = subprocess.run(
        ["npm", "install", "--no-audit", "--no-fund"],
        cwd=tpl, capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"npm install (Remotion) failed:\n{r.stderr[-800:]}")


def _render_remotion(spec: dict, tok: dict, out_dir: Path, stem: str) -> Path:
    tpl = _remotion_dir()
    if not shutil.which("node"):
        raise RuntimeError("node not found — the Remotion engine needs Node (brew install node)")
    _ensure_remotion_install(tpl)

    props = out_dir / f"{stem}.props.json"
    props.write_text(json.dumps({"spec": spec, "tokens": tok}), encoding="utf-8")
    mp4 = out_dir / f"{stem}.mp4"
    r = subprocess.run(
        ["npx", "remotion", "render", "src/index.ts", "storyboard",
         str(mp4.resolve()), f"--props={props.resolve()}"],
        cwd=tpl, capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"remotion render failed:\n{r.stderr[-1200:]}")
    return mp4


def produce(
    spec_path: Path,
    out_dir: Path | None = None,
    engine: str = "auto",
    make_video: bool = True,
    make_lottie: bool = False,
) -> dict[str, Path]:
    """Render ``spec_path`` to outputs. Returns ``{export: path}``."""
    spec = storyboard_mod.load(spec_path)
    g = spec["global"]
    tok = tokens_mod.resolve(g.get("brand"), g.get("motion_system"))

    out_dir = Path(out_dir) if out_dir else spec_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = _stem(spec_path)
    outputs: dict[str, Path] = {}

    # The animated HTML is always the embeddable preview (and the declarative
    # capture source).
    html_path = out_dir / f"{stem}.html"
    html_path.write_text(animate.render_html(spec, tok), encoding="utf-8")
    outputs["html"] = html_path

    # Lottie: the embeddable vector export (independent of the video engine).
    if make_lottie:
        lottie_path = out_dir / f"{stem}.lottie.json"
        lottie_path.write_text(json.dumps(lottie_mod.render(spec, tok)), encoding="utf-8")
        outputs["lottie"] = lottie_path

    if not make_video:
        return outputs

    eng = select_engine(engine)
    if eng == "remotion":
        outputs["mp4"] = _render_remotion(spec, tok, out_dir, stem)
    else:
        w, h = animate.stage_size(spec)
        total = storyboard_mod.total_duration(spec)
        mp4 = out_dir / f"{stem}.mp4"
        capture_mod.html_to_video(html_path, mp4, total, w, h, fps=int(g.get("fps", 30)))
        outputs["mp4"] = mp4

    return outputs
