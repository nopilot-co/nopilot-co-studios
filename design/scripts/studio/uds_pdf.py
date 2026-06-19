"""UDS-HTML → PDF (ADR-006) — the print serialiser.

Sibling to ``gslide.py``: both are serialisers off the one UDS ``:::`` source.
``gslide`` builds native Google Slides; this prints the UDS-HTML *composition
primary* (``uds_html._self_contained``) to PDF via Chromium, honouring the print
CSS (``uds/ui/uds-doc.css`` ``@media print``) with a **native running
header/footer** (Chromium ``displayHeaderFooter``). The margin box reserves the
page margin and never overlaps the body — a ``position:fixed``/``sticky`` DOM
header overlaps continuation pages (cowork-run learning,
``learnings/2026/uds-pdf-bake-ins.md``). One source, parallel renders.

Judgment vs. mechanics: this module is pure mechanics. It does not edit the
``:::`` vocabulary (that lives in ``uds_html`` ``_FENCE`` — the shared, frozen
contract); it only composes that HTML and prints it.

Playwright is an **optional** dependency (declare / detect / degrade, like
``qa.py``): the module imports without it; ``to_pdf`` raises with the exact
install command at point of use.
"""

from __future__ import annotations

import base64
from html import escape as _esc
from pathlib import Path
from typing import Any

from . import brand as brand_mod
from . import hydrate as hydrate_mod
from . import uds_html

# Page geometry is a RENDER choice (owned here), kept out of the shared doc CSS.
# Margins reserve the band the native header/footer is drawn into — top/bottom
# must exceed the header/footer height or the body collides with them.
_GEOM: dict[str, dict[str, Any]] = {
    "landscape": {"format": "A4", "landscape": True,
                  "margin": {"top": "0.72in", "bottom": "0.62in", "left": "0.5in", "right": "0.5in"}},
    "portrait":  {"format": "A4", "landscape": False,
                  "margin": {"top": "0.72in", "bottom": "0.62in", "left": "0.6in", "right": "0.6in"}},
    "16:9":      {"width": "13.333in", "height": "7.5in",   # the standard 16:9 slide canvas
                  "margin": {"top": "0.5in", "bottom": "0.45in", "left": "0.6in", "right": "0.6in"}},
}

_INSTALL = ("UDS→PDF needs Playwright's Chromium. Install it with:\n"
            "  uv sync --extra playwright && playwright install chromium\n"
            "(or: pip install playwright && playwright install chromium)")


# ------------------------------------------------------------------- brand chrome
def _brand_wordmark(b: dict[str, Any], slug: str) -> str:
    meta = b.get("meta") or {}
    return str(meta.get("name") or b.get("name") or slug.replace("-", " ").title())


def _brand_company(b: dict[str, Any]) -> str:
    meta = b.get("meta") or {}
    return str(meta.get("company") or meta.get("legal") or meta.get("name") or b.get("name") or "")


def _logo_data_uri(slug: str) -> str | None:
    """Inline the brand logo as a data URI — external refs do not load inside
    Chromium's isolated header/footer context. Falls back to the wordmark (None)."""
    try:
        root = brand_mod.brand_root(slug)
        b = brand_mod.load(slug)
    except Exception:
        return None
    candidates: list[Path] = []
    logo = b.get("logo")
    if isinstance(logo, str):
        candidates.append(root / logo)
    elif isinstance(logo, dict):
        for k in ("small", "medium", "light", "large"):
            v = logo.get(k)
            if isinstance(v, str):
                candidates.append(root / v)
            elif isinstance(v, dict) and v.get("path"):
                candidates.append(root / str(v["path"]))
    candidates += [root / "assets" / "logo.svg", root / "assets" / "logo-dark.svg"]
    for c in candidates:
        try:
            if c and c.exists():
                mime = "image/svg+xml" if c.suffix == ".svg" else f"image/{c.suffix.lstrip('.')}"
                return f"data:{mime};base64," + base64.b64encode(c.read_bytes()).decode()
        except OSError:
            continue
    return None


_BAND = ("font-family:Inter,system-ui,-apple-system,sans-serif;font-size:8px;"
         "color:#6E747A;width:100%;padding:0 0.5in;display:flex;"
         "align-items:center;justify-content:space-between;-webkit-print-color-adjust:exact;")


def _header_template(logo_uri: str | None, wordmark: str, confidential: str) -> str:
    left = (f'<img src="{logo_uri}" style="height:13px;width:auto">'
            if logo_uri else f'<span style="font-weight:600;color:#1C2022">{_esc(wordmark)}</span>')
    right = (f'<span style="text-transform:uppercase;letter-spacing:.08em">{_esc(confidential)}</span>'
             if confidential else "")
    return f'<div style="{_BAND}">{left}{right}</div>'


def _footer_template(company: str) -> str:
    pages = ('<span>Page <span class="pageNumber"></span> of '
             '<span class="totalPages"></span></span>')
    return f'<div style="{_BAND}"><span>{_esc(company)}</span>{pages}</div>'


# ------------------------------------------------------------------- compose
def _ensure_theme(brand: str) -> None:
    """Generate the brand's theme CSS on demand if absent — themes derive from the
    brand's tokens.yaml, so a render shouldn't fail just because a brand hasn't been
    pre-themed (only nopilot/greyscale ship pre-generated). Writes ONLY the brand's
    theme file — deliberately not ``hydrate.write_themes``, which also rewrites the
    shared single-brand ``uds-ui.lock.json`` (a build-step side effect, wrong to
    trigger from a render)."""
    theme = hydrate_mod.THEMES_DIR / f"theme-{brand}.css"
    if theme.exists():
        return
    try:
        css = hydrate_mod.theme_css(hydrate_mod.vars_for_brand(brand), label=f"{brand} (hydrated)")
        theme.write_text(css, encoding="utf-8")
    except Exception:
        pass  # _self_contained raises a clear FileNotFoundError if truly missing


def compose_html(source: Path, *, brand: str) -> tuple[str, str]:
    """Produce the self-contained UDS-HTML to print, from a flat ``:::`` ``.md``
    source, a docket manifest (``.yaml``/``.yml``), or an already-built ``.html``.
    Reuses ``uds_html`` so the inlined theme/base/doc CSS is identical to the
    on-screen document (no print-only divergence beyond ``@media print``)."""
    source = Path(source)
    if source.suffix == ".html":
        return source.read_text(encoding="utf-8"), source.stem
    _ensure_theme(brand)  # md / docket compose inlines theme-{brand}.css
    if source.suffix in (".yaml", ".yml"):
        meta, body = uds_html.render_docket(source)
        title = str(meta.get("title", "Proposition"))
        return uds_html._self_contained(body, title, brand), title
    meta, body = uds_html.render_body(source.read_text(encoding="utf-8"), brand=brand)
    title = str(meta.get("title", "Untitled"))
    return uds_html._self_contained(body, title, brand), title


def to_pdf(html: str, out_path: Path, *, orientation: str = "landscape",
           logo_uri: str | None = None, wordmark: str = "",
           confidential: str = "", company: str = "") -> Path:
    """Print a self-contained HTML string to PDF via Chromium, with the native
    running header/footer and the proven print settings."""
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as e:                      # declare / detect / degrade
        raise RuntimeError(_INSTALL) from e

    geom = _GEOM.get(orientation) or _GEOM["landscape"]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")  # let the webfonts load
            try:
                page.evaluate("async () => { await document.fonts.ready }")
            except Exception:
                pass
            page.emulate_media(media="print")
            pdf_kwargs: dict[str, Any] = dict(
                path=str(out_path),
                print_background=True,
                display_header_footer=True,
                header_template=_header_template(logo_uri, wordmark, confidential),
                footer_template=_footer_template(company),
                margin=geom["margin"],
            )
            if "width" in geom:                              # explicit page size (e.g. 16:9 slide)
                pdf_kwargs.update(width=geom["width"], height=geom["height"])
            else:                                            # named paper + orientation
                pdf_kwargs.update(format=geom["format"], landscape=geom["landscape"])
            page.pdf(**pdf_kwargs)
        finally:
            browser.close()
    return out_path


def render(source: Path, out_path: Path, *, brand: str = "nopilot",
           orientation: str = "landscape", present: bool = False,
           confidential: str = "Confidential — not for distribution") -> Path:
    """High-level: compose the UDS-HTML for ``source`` and print it to ``out_path``,
    pulling the running header/footer chrome (logo, wordmark, company) from the brand.
    ``present=True`` renders a 16:9 slide deck — each top-level section on its own
    page (gated by the ``data-uds-present`` body attribute the print CSS keys on)."""
    try:
        b = brand_mod.load(brand)
    except Exception:
        b = {}
    html, _title = compose_html(Path(source), brand=brand)
    if present:
        html = html.replace('<body class="uds-root doc">',
                            '<body class="uds-root doc" data-uds-present="1">', 1)
    return to_pdf(
        html, Path(out_path), orientation=("16:9" if present else orientation),
        logo_uri=_logo_data_uri(brand), wordmark=_brand_wordmark(b, brand),
        confidential=confidential, company=_brand_company(b),
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="studio-uds-pdf", description="UDS-HTML → PDF (ADR-006).")
    ap.add_argument("source", help="a flat ::: .md source, a docket manifest (.yaml), or a self-contained .html")
    ap.add_argument("--out", required=True)
    ap.add_argument("--brand", default="nopilot")
    ap.add_argument("--orientation", choices=["landscape", "portrait"], default="landscape")
    ap.add_argument("--present", action="store_true",
                    help="render a 16:9 slide deck, one section per page (presentation purpose)")
    ap.add_argument("--confidential", default="Confidential — not for distribution")
    args = ap.parse_args(argv)
    print("wrote", render(Path(args.source), Path(args.out), brand=args.brand,
                          orientation=args.orientation, present=args.present,
                          confidential=args.confidential))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
