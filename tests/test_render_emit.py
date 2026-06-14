#!/usr/bin/env python3
"""render._emit_output creates the destination dir (#34). Standalone; run:
    design/.venv/bin/python tests/test_render_emit.py

Docket-scaffolded render sessions have no outputs/ dir, so emitting must create
it rather than raising FileNotFoundError.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import render as render_mod  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


with tempfile.TemporaryDirectory() as _t:
    tmp = Path(_t)

    # Non-HTML path (pdf) into a session whose outputs/ dir does not exist.
    produced = tmp / "source.pdf"
    produced.write_bytes(b"%PDF-1.4 test")
    dest = tmp / "session" / "outputs" / "doc.v1.0.1.pdf"
    render_mod._emit_output("pdf", produced, dest, "source", tmp)
    check("pdf: missing outputs/ created", dest.exists(), str(dest))

    # HTML path (self-contained, no sidecar) into a missing outputs/ dir.
    prod_html = tmp / "source.html"
    prod_html.write_text("<html><body>ok</body></html>", encoding="utf-8")
    dest_html = tmp / "session2" / "outputs" / "doc.v1.0.1.html"
    render_mod._emit_output("html", prod_html, dest_html, "source", tmp)
    check("html: missing outputs/ created", dest_html.exists(), str(dest_html))

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: render emits into missing outputs dir")
