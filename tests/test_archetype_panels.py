#!/usr/bin/env python3
"""stat-panel / pullquote / cta — native gslide (ADR-006 / #129). Standalone.
HTML already renders these; this pins the new gslide native renderers."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import archetype_ir as ir  # noqa: E402
from studio import gslide  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


# normalise
s = ir.normalise_stats([{"value": "45%", "label": "faster", "delta": "+12"}, {"value": "£267k", "label": "cost"}])
check("stats: 2 items", [x.value for x in s.items] == ["45%", "£267k"], str(s.items))
check("stats: delta kept", s.items[0].delta == "+12")
pq = ir.normalise_pullquote("A quote worth keeping.\n— Andy O'Brien")
check("pullquote: body + attribution split", pq.body == "A quote worth keeping." and pq.attribution == "Andy O'Brien", str(pq))
cta = ir.normalise_cta("Book a paid Lunch and Learn.")
check("cta: text", cta.text == "Book a paid Lunch and Learn.")
check("capabilities present", {"stat-panel", "pullquote", "cta"} <= set(ir.CAPABILITIES))

MD = ("---\ntitle: T\n---\n\n## Numbers {#n}\n\n"
      "::: stat-panel\n- {value: \"45%\", label: faster delivery, delta: \"+12pts\"}\n"
      "- {value: \"£267k\", label: programme cost}\n- {value: \"3\", label: principals}\n:::\n\n"
      "## Voice {#v}\n\n::: pullquote\nThis is the quote that matters.\n— Andy O'Brien\n:::\n\n"
      "## Ask {#a}\n\n::: cta\nBook a paid Lunch and Learn to scope your readiness.\n:::\n")
with tempfile.TemporaryDirectory() as td:
    src = Path(td) / "d.md"
    src.write_text(MD)
    _t, reqs = gslide.build_requests(src, brand="nopilot", profile="proposal")
    inserts = [r["insertText"]["text"] for r in reqs if "insertText" in r]
    check("gslide: stat values", all(v in inserts for v in ("45%", "£267k", "3")), str(inserts))
    check("gslide: stat delta", any("+12" in t for t in inserts))
    check("gslide: pullquote body + attribution", any("quote that matters" in t for t in inserts) and any("Andy" in t for t in inserts))
    check("gslide: cta text", any("Lunch and Learn" in t for t in inserts))
    check("gslide: cta button (default)", any("Get in touch" in t for t in inserts))

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: stat-panel / pullquote / cta — native gslide")
