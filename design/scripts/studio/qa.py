"""Visual QA capture: rasterize PDF, convert PPTX→PDF→PNG, screenshot HTML.

The actual critique is written by the LLM (visual-qa skill) after looking at
the captured images. This module only does deterministic capture.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from . import session as session_mod


def capture(session_path: Path, version: str | None = None) -> list[Path]:
    state = session_mod.read_state(session_path)
    version = version or state["current"]
    if version == "0.0.0":
        raise ValueError("session has no renders yet; run `studio render` first")

    qa_dir = session_path / "qa" / f"v{version}"
    qa_dir.mkdir(parents=True, exist_ok=True)

    # Find the render record for this version
    record = next((h for h in state["history"] if h["version"] == version), None)
    if record is None:
        raise ValueError(f"no render history for v{version}")

    images: list[Path] = []
    for fmt, out_path_str in record["outputs"].items():
        out_path = Path(out_path_str)
        if not out_path.exists():
            continue
        if fmt == "pdf":
            images.extend(_pdf_to_png(out_path, qa_dir, prefix="pdf-page"))
        elif fmt == "pptx":
            images.extend(_pptx_to_png(out_path, qa_dir, prefix="pptx-slide"))
        elif fmt in ("html", "revealjs"):
            png = _html_to_png(out_path, qa_dir, name=f"{fmt}-fullpage.png")
            if png is not None:
                images.append(png)
    return images


def _pdf_to_png(pdf: Path, out_dir: Path, prefix: str) -> list[Path]:
    """Rasterize a PDF to one PNG per page using pypdfium2."""
    try:
        import pypdfium2 as pdfium
    except ImportError as e:
        raise RuntimeError("pypdfium2 not installed — pip install pypdfium2") from e

    pdf_doc = pdfium.PdfDocument(str(pdf))
    results: list[Path] = []
    for i, page in enumerate(pdf_doc, start=1):
        bitmap = page.render(scale=2.0)  # ~144 DPI
        pil = bitmap.to_pil()
        dest = out_dir / f"{prefix}-{i:02d}.png"
        pil.save(dest)
        results.append(dest)
    return results


def _pptx_to_png(pptx: Path, out_dir: Path, prefix: str) -> list[Path]:
    """Convert PPTX → PDF via libreoffice, then rasterize."""
    soffice = shutil.which("libreoffice") or shutil.which("soffice")
    if not soffice:
        raise RuntimeError(
            "libreoffice/soffice not found — install with: brew install --cask libreoffice"
        )
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        cmd = [
            soffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(td_path),
            str(pptx),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            raise RuntimeError(f"libreoffice PPTX→PDF failed:\n{result.stderr}")
        pdf = td_path / (pptx.stem + ".pdf")
        if not pdf.exists():
            raise RuntimeError(f"libreoffice reported success but {pdf} not found")
        return _pdf_to_png(pdf, out_dir, prefix=prefix)


def _html_to_png(html: Path, out_dir: Path, name: str) -> Path | None:
    """Screenshot HTML to PNG.

    Order of preference:
      1. playwright (if installed + browsers installed)
      2. wkhtmltoimage (if installed)
      3. None — return None and let the skill capture via Claude_Preview MCP
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(html.absolute().as_uri())
            dest = out_dir / name
            page.screenshot(path=str(dest), full_page=True)
            browser.close()
            return dest
    except Exception:
        pass

    wkh = shutil.which("wkhtmltoimage")
    if wkh:
        dest = out_dir / name
        result = subprocess.run(
            [wkh, "--width", "1440", str(html), str(dest)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and dest.exists():
            return dest

    # Neither available — caller (the skill) should use Claude_Preview MCP
    return None
