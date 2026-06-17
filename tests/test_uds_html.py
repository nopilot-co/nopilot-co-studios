#!/usr/bin/env python3
"""markdown → UDS-HTML mapper (ADR-006). Standalone; run:
    design/.venv/bin/python tests/test_uds_html.py

Asserts the single 360 `:::` source maps to the UDS archetypes (base.css classes)
and wraps into a hydrated document — the HTML-primary half of the inversion.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import uds_html  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


SRC = REPO / "design" / "uds" / "examples" / "360-proposition.md"
meta, html = uds_html.render_body(SRC.read_text(encoding="utf-8"))

check("title from front-matter", str(meta.get("title", "")).startswith("Context Operating"), str(meta.get("title")))
check("hero title + standfirst", 'class="uds-hero"' in html and "uds-hero__title" in html and "uds-hero__standfirst" in html)
check("eyebrow from brand", "360 · PROPOSITION" in html)
check("stat grid", 'class="uds-grid"' in html and "uds-stat__value" in html and "uds-stat__label" in html)
check("pull-quote + attribution", "uds-pull-quote" in html and "uds-pull-quote__attribution" in html)
check("three callouts", html.count('class="uds-callout"') >= 3, str(html.count('class="uds-callout"')))
check("process cards", html.count("uds-card__title") >= 3, str(html.count("uds-card__title")))
check("table", 'class="uds-table"' in html and "<th>" in html and "<td>" in html)
check("cta banner + button", "uds-banner--promo" in html and "uds-button--primary" in html)
check("h2 sections", html.count("<h2>") >= 4, str(html.count("<h2>")))
check("fences consumed", ":::" not in html)
check("html-escaped", "&amp;" in html or "&#x27;" in html)

# Full hydrated document: webfonts + base.css + the nopilot theme.
out = uds_html.render_file(SRC, REPO / "design" / "uds" / "examples" / "360-proposition.html", brand="nopilot")
doc = out.read_text(encoding="utf-8")
check("hydrated doc", 'class="uds-root"' in doc and "theme-nopilot.css" in doc and "base.css" in doc)

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: UDS-HTML mapper (360 rebuild)")
