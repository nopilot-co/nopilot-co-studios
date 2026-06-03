#!/usr/bin/env python3
"""HTML QA rasterization is a first-class, declared capability (#36). Standalone:
    design/.venv/bin/python tests/test_qa_html.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import deps as deps_mod  # noqa: E402
from studio import formats as formats_mod  # noqa: E402
from studio import qa as qa_mod  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


# 1. html / revealjs exports DECLARE the qa rasterization dependency.
for export_slug in ("proposal-html", "pitch-revealjs"):
    r = formats_mod.resolve(export_slug)
    qa_req = (r.get("requires") or {}).get("qa") or []
    check(f"{export_slug} declares html-raster", "html-raster" in qa_req, str(qa_req))

# 2. html-raster has an install hint (provisioning is documented, not improvised).
check("html-raster install hint", bool(deps_mod.INSTALL_HINTS.get("html-raster")))

# 3. have('html-raster') tracks html_rasterizer() and returns a bool.
avail = deps_mod.html_rasterizer()
check("html_rasterizer returns id-or-None", avail in (None, "playwright", "wkhtmltoimage"), str(avail))
check("have() matches rasterizer", deps_mod.have("html-raster") == (avail is not None))

# 4. When no rasterizer is available, capture FAILS LOUDLY (never a silent skip).
_real = deps_mod.html_rasterizer
deps_mod.html_rasterizer = lambda: None  # force "unavailable"
try:
    with tempfile.TemporaryDirectory() as _t:
        out = Path(_t)
        (out / "x.html").write_text("<html><body>hi</body></html>", encoding="utf-8")
        raised = False
        try:
            qa_mod._html_to_png(out / "x.html", out, "fullpage.png")
        except RuntimeError as e:
            raised = True
            check("loud error names provisioning", "playwright install chromium" in str(e), str(e))
        check("html capture raises when no rasterizer", raised)
finally:
    deps_mod.html_rasterizer = _real

# 5. missing_for surfaces html-raster as a qa gap when unavailable.
deps_mod.html_rasterizer = lambda: None
try:
    miss = deps_mod.missing_for(formats_mod.resolve("proposal-html"), "qa")
    check("missing_for flags html-raster", "html-raster" in miss, str(miss))
finally:
    deps_mod.html_rasterizer = _real

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: html QA rasterization is declared, detected, and fails loudly")
