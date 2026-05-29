"""Deterministic capture of the asset under review.

Rasterises the target so the visual-qa skill has pixels to critique. Mirrors the
design studio's `qa capture`, generalised to also accept a live URL. Pure
mechanics, no judgment. Degrades with an actionable hint when a tool is missing;
text-only targets (md/txt) need no capture and return an empty list.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from . import session as session_mod

IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "gif", "svg"}
TEXT_EXTS = {"md", "markdown", "txt", "rtf"}


def capture(session_path: Path, version: str) -> list[Path]:
    """Capture the session's target into ``capture/v<version>/``."""
    state = session_mod.read_state(session_path)
    out_dir = session_path / "capture" / f"v{version}"
    out_dir.mkdir(parents=True, exist_ok=True)

    kind = (state.get("target_kind") or "").lower()
    ref = state.get("target") or ""

    if kind == "url":
        return _shoot_html(ref, out_dir, "url")

    src = Path(ref)
    ext = src.suffix.lstrip(".").lower() or kind
    if ext == "pdf":
        return _pdf_pages(src, out_dir)
    if ext in {"html", "htm"}:
        return _shoot_html(src.resolve().as_uri(), out_dir, "html")
    if ext == "pptx":
        return _pptx_pages(src, out_dir)
    if ext in IMAGE_EXTS:
        dest = out_dir / f"image{src.suffix.lower()}"
        shutil.copy2(src, dest)
        return [dest]
    if ext in TEXT_EXTS:
        return []  # text-only: nothing to rasterise
    return []  # unknown kind: best-effort no-op


# ---------------------------------------------------------------- backends
def _pdf_pages(pdf: Path, out_dir: Path, scale: float = 2.0) -> list[Path]:
    try:
        import pypdfium2 as pdfium
    except ImportError as e:
        raise RuntimeError("PDF capture needs pypdfium2 — pip install pypdfium2") from e
    doc = pdfium.PdfDocument(str(pdf))
    paths: list[Path] = []
    for i in range(len(doc)):
        image = doc[i].render(scale=scale).to_pil()
        p = out_dir / f"pdf-page-{i + 1:02d}.png"
        image.save(p)
        paths.append(p)
    return paths


def _shoot_html(url: str, out_dir: Path, label: str) -> list[Path]:
    out = out_dir / f"{label}-fullpage.png"
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        if shutil.which("wkhtmltoimage"):
            subprocess.run(
                ["wkhtmltoimage", "--quality", "90", url, str(out)], check=True
            )
            return [out]
        raise RuntimeError(
            "HTML/URL capture needs playwright "
            "(pip install playwright && playwright install chromium) "
            "or wkhtmltoimage on PATH"
        ) from None
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(url, wait_until="networkidle")
        page.screenshot(path=str(out), full_page=True)
        browser.close()
    return [out]


def _pptx_pages(pptx: Path, out_dir: Path) -> list[Path]:
    soffice = shutil.which("libreoffice") or shutil.which("soffice")
    if not soffice:
        raise RuntimeError(
            "PPTX capture needs LibreOffice — brew install --cask libreoffice"
        )
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp, str(pptx)],
            check=True,
        )
        pdfs = list(Path(tmp).glob("*.pdf"))
        if not pdfs:
            raise RuntimeError(f"LibreOffice did not produce a PDF for {pptx.name}")
        return _pdf_pages(pdfs[0], out_dir)
