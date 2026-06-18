#!/usr/bin/env python3
"""Native Google Slides pipeline (ADR-006). Standalone; run:
    design/.venv/bin/python tests/test_gslide.py
Hermetic: builds a tiny temp docket and asserts the Slides batchUpdate spec."""
from __future__ import annotations
import sys, tempfile, os
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))
from studio import gslide  # noqa: E402

failures: list[str] = []
def check(n, c, d=""):
    if not c: failures.append(f"{n}{(' — ' + d) if d else ''}")

check("rgb crimson", gslide._rgb("#C3094A")["red"] > 0.7 and gslide._rgb("#C3094A")["blue"] > 0.28, str(gslide._rgb("#C3094A")))

d = tempfile.mkdtemp()
os.makedirs(f"{d}/content/sections", exist_ok=True)
Path(f"{d}/content/sections/x.md").write_text("# Section: X\n\n## Sub\n\nHello world. This is body.\n\n> A quote here.\n— Me\n")
Path(f"{d}/content/manifest.yaml").write_text(
    "meta: {doc_title: Test}\ntopics:\n"
    "  - {id: cover, title: '360°'}\n"
    "  - {id: part, title: A Part, eyebrow: part one}\n"
    "  - {id: x, title: X, eyebrow: kicker, section_md: content/sections/x.md}\n")
title, reqs = gslide.build_requests(Path(f"{d}/content/manifest.yaml"))

create = [r for r in reqs if "createSlide" in r]
shapes = [r for r in reqs if "createShape" in r]
inserts = {r["insertText"]["objectId"] for r in reqs if "insertText" in r}
check("title from meta", title == "Test", title)
check(">=4 slides (cover/section/quote/content)", len(create) >= 4, str(len(create)))
check("every shape gets text", all(s["createShape"]["objectId"] in inserts for s in shapes))
check("blank layout", all(r["createSlide"]["slideLayoutReference"]["predefinedLayout"] == "BLANK" for r in create))
# cover white bg; a section uses the dark ink bg
bgs = [r["updatePageProperties"]["pageProperties"]["pageBackgroundFill"]["solidFill"]["color"]["rgbColor"] for r in reqs if "updatePageProperties" in r]
check("cover bg white", bgs[0] == {"red": 1.0, "green": 1.0, "blue": 1.0}, str(bgs[0]))
check("a dark section bg present", any(c["red"] < 0.2 and c["green"] < 0.2 for c in bgs), str(bgs))
# crimson eyebrow somewhere
styles = [r["updateTextStyle"]["style"] for r in reqs if "updateTextStyle" in r]
check("crimson text used", any(s["foregroundColor"]["opaqueColor"]["rgbColor"]["red"] > 0.7 and s["foregroundColor"]["opaqueColor"]["rgbColor"]["blue"] > 0.28 for s in styles))
check("mono fallback = IBM Plex Mono", any(s["fontFamily"] == "IBM Plex Mono" for s in styles))
check("payload dry-run shape", set(gslide.payload(Path(f"{d}/content/manifest.yaml"))) == {"title", "slides", "requests"})

if failures:
    print(f"FAIL ({len(failures)})"); [print("  -", f) for f in failures]; sys.exit(1)
print("PASS: gslide native Slides pipeline")
