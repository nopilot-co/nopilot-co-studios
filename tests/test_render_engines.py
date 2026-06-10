#!/usr/bin/env python3
"""Render-engine dispatch (#99) — verifies layout-keyed engine selection.

The acceptance from #99: render on a frame contract builds ON the showcase
template; a linear contract uses the doc pipeline; PPTX uses the native
python-pptx engine. Selection is driven by the resolved layout/export, not
hardcoded.

Run: design/.venv/bin/python tests/test_render_engines.py
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

formats = importlib.import_module("studio.formats")
render = importlib.import_module("studio.render")

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


def engine_for(slug: str) -> str:
    r = formats.resolve(slug)
    return (r.get("render") or {}).get("engine")


# 1. Engine registry has the three engines #99 names.
known = set(render.known_engines())
check("linear-engine registered", "linear-engine" in known)
check("pptx-engine registered", "pptx-engine" in known)
check("frame-engine registered", "frame-engine" in known)

# 2. Engine selection per slug — the layout-keyed dispatch.
check("showcase-html -> frame-engine", engine_for("showcase-html") == "frame-engine")
check("pitch-pdf -> linear-engine", engine_for("pitch-pdf") == "linear-engine")
check("pitch-html -> linear-engine", engine_for("pitch-html") == "linear-engine")
check("pitch-revealjs -> linear-engine", engine_for("pitch-revealjs") == "linear-engine")
check("pitch-pptx -> pptx-engine (export overrides layout)",
      engine_for("pitch-pptx") == "pptx-engine")
check("report-pptx -> pptx-engine", engine_for("report-pptx") == "pptx-engine")

# 3. Every renderable slug resolves to a known engine.
for slug in formats.list_formats():
    try:
        r = formats.resolve(slug)
        if not formats.is_renderable(r):
            continue
        eng = (r.get("render") or {}).get("engine")
        check(f"{slug} dispatches to known engine ({eng})", eng in known)
    except Exception as e:
        failures.append(f"{slug} resolve failed: {e}")

# 4. Smoke test: _engine_frame runs end-to-end against a fixture session.
#    Builds outputs/<stem>.v<version>.html that contains the template's
#    well-known TWO-AXIS NAV markup — i.e. it really copied templates/showcase/
#    showcase.html, not a stub.
import tempfile

with tempfile.TemporaryDirectory() as td:
    session = Path(td) / "session"
    (session / "inputs").mkdir(parents=True)
    (session / "outputs").mkdir(parents=True)
    (session / "inputs" / "source.md").write_text("# placeholder\nnot used by frame-engine yet (#100).\n")
    state = {
        "brand": "nopilot",
        "format": "showcase-html",
        "source_filename": "source.md",
        "title": "Test Showcase",
        "description": "smoke test",
    }
    (session / "version.json").write_text(json.dumps({
        "brand": "nopilot", "session": "test", "format": "showcase-html",
        "source_filename": "source.md", "title": "Test Showcase",
        "description": "smoke test",
        "created": "2026-06-10", "current": "0.0.0", "history": [],
    }))

    resolved = formats.resolve("showcase-html")
    outputs = render._engine_frame(session, resolved, state, "1.0.0")
    check("frame-engine returns html output", "html" in outputs)
    out_path = outputs["html"]
    check("frame-engine output file exists", out_path.exists())
    if out_path.exists():
        text = out_path.read_text(encoding="utf-8")
        check("frame-engine output carries template's CANONICAL TEMPLATE banner",
              "CANONICAL TEMPLATE" in text)
        check("frame-engine substituted document title",
              "Test Showcase" in text)
        check("frame-engine output carries Tailwind cdn", "tailwindcss.com" in text)

# 5. Unknown engine -> registry returns None (render() then raises RuntimeError).
check("unknown engine -> registry miss", render._ENGINES.get("made-up") is None)

if failures:
    print(f"FAIL ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(f"OK — {len(known)} engines registered, dispatch verified, frame-engine smoke pass")
