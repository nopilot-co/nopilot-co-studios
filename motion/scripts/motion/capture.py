"""Rasterize/record HTML via headless Chromium (Playwright) + ffmpeg.

Shared helpers:
- ``html_to_png`` — full-page screenshot (storyboard board preview, QA sheets).
- ``html_to_video`` — record an auto-playing HTML to MP4 (the declarative render
  path, ADR-002): Playwright records WebM, ffmpeg transcodes to H.264 MP4.

Playwright is the optional ``capture`` extra; ffmpeg is a Brewfile binary. Both
degrade with a clear message if absent (see ``motion doctor``).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def html_to_png(html_path: Path, png_path: Path, width: int = 1180) -> Path:
    """Full-page screenshot of a local HTML file. Raises RuntimeError if
    Playwright/Chromium isn't available."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError(
            "Playwright not installed — run:\n"
            "  pip install 'motion-studio[capture]' && playwright install chromium"
        ) from e

    png_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(
                    viewport={"width": width, "height": 900}, device_scale_factor=2
                )
                page.goto(html_path.resolve().as_uri())
                page.wait_for_timeout(150)
                page.screenshot(path=str(png_path), full_page=True)
            finally:
                browser.close()
    except Exception as e:  # noqa: BLE001 — degrade on any Playwright/launch error
        raise RuntimeError(
            f"headless capture failed ({type(e).__name__}). Install the browser: "
            "playwright install chromium"
        ) from e
    return png_path


def html_to_video(
    html_path: Path,
    mp4_path: Path,
    seconds: float,
    width: int,
    height: int,
    fps: int = 30,
) -> Path:
    """Record an auto-playing HTML page to an H.264 MP4.

    Playwright records the page (WebM) for ``seconds``; ffmpeg transcodes to MP4
    at ``fps``. Raises RuntimeError (degrades) if Playwright or ffmpeg is missing.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError(
            "Playwright not installed — pip install 'motion-studio[capture]' "
            "&& playwright install chromium"
        ) from e
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found — brew install ffmpeg")

    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = mp4_path.parent / "_rec"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(
                viewport={"width": width, "height": height},
                record_video_dir=str(tmp_dir),
                record_video_size={"width": width, "height": height},
            )
            page = ctx.new_page()
            page.goto(html_path.resolve().as_uri())
            # Hold the page open for the full timeline (+ a small tail).
            page.wait_for_timeout(int(seconds * 1000) + 400)
            webm = page.video.path()
            ctx.close()  # finalizes the WebM
            browser.close()
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            f"video capture failed ({type(e).__name__}). Ensure Chromium is "
            "installed: playwright install chromium"
        ) from e

    cmd = [
        "ffmpeg", "-y", "-i", str(webm),
        "-r", str(fps),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(mp4_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg transcode failed:\n{result.stderr[-800:]}")
    return mp4_path
