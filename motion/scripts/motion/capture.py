"""Rasterize an HTML file to PNG via headless Chromium (Playwright).

Shared helper: the storyboard board preview uses it now; visual-QA keyframe
contact-sheets will reuse it later. Playwright is the optional ``capture`` extra
(``pip install 'motion-studio[capture]' && playwright install chromium``); this
module degrades with a clear message if it's absent.
"""

from __future__ import annotations

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
