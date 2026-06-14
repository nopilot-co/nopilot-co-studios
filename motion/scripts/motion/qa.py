"""Visual QA capture for motion — eyes-on-pixels on the rendered video.

Extracts one keyframe per scene (at its midpoint) from the MP4 via ffmpeg and
assembles a labelled contact sheet, so a reviewer (the visual-qa skill) can judge
pacing, legibility, brand, and motion against the storyboard.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


def _scene_starts(spec: dict[str, Any]) -> list[float]:
    starts, t = [], 0.0
    for s in spec.get("scenes", []):
        starts.append(t)
        t += float(s.get("duration", 0))
    return starts


def capture(mp4_path: Path, spec: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    """One keyframe per scene + a contact sheet. Returns paths + scene labels."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found — brew install ffmpeg")
    out_dir.mkdir(parents=True, exist_ok=True)

    starts = _scene_starts(spec)
    frames: list[tuple[Path, str]] = []
    for i, scene in enumerate(spec.get("scenes", [])):
        mid = starts[i] + float(scene.get("duration", 0)) / 2.0
        fpath = out_dir / f"scene-{i + 1:02d}.png"
        r = subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{mid:g}", "-i", str(mp4_path),
             "-frames:v", "1", str(fpath)],
            capture_output=True, text=True,
        )
        if r.returncode == 0 and fpath.exists():
            frames.append((fpath, str(scene.get("id", f"scene {i + 1}"))))

    sheet = _contact_sheet(frames, out_dir / "contact-sheet.png")
    return {"frames": [str(f) for f, _ in frames], "contact_sheet": str(sheet) if sheet else None}


def _contact_sheet(frames: list[tuple[Path, str]], out: Path) -> Path | None:
    if not frames:
        return None
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None

    cols = 2
    thumb_w = 560
    pad, label_h = 14, 26
    thumbs = []
    for fpath, label in frames:
        im = Image.open(fpath).convert("RGB")
        ratio = thumb_w / im.width
        im = im.resize((thumb_w, int(im.height * ratio)))
        thumbs.append((im, label))

    cell_h = max(im.height for im, _ in thumbs) + label_h
    rows = (len(thumbs) + cols - 1) // cols
    sheet_w = cols * thumb_w + (cols + 1) * pad
    sheet_h = rows * cell_h + (rows + 1) * pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), (241, 243, 246))
    draw = ImageDraw.Draw(sheet)
    for idx, (im, label) in enumerate(thumbs):
        c, r = idx % cols, idx // cols
        x = pad + c * (thumb_w + pad)
        y = pad + r * (cell_h + pad)
        draw.text((x, y), f"{idx + 1}. {label}", fill=(31, 36, 51))
        sheet.paste(im, (x, y + label_h))
    sheet.save(out)
    return out
