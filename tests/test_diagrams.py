#!/usr/bin/env python3
"""Slice 4a diagram engine — structured ::: <diagram> YAML expanded per export.
Standalone; run: design/.venv/bin/python tests/test_diagrams.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import diagrams  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


TOK = {
    "color": {
        "neutral": "#142F54",
        "surface": "#21456b",
        "tertiary": "#B14B33",
        "on_primary": "#FFFFFF",
        "secondary": "#6B7280",
        "primary": "#142F54",
    },
    "space": {"sm": "8pt", "md": "16pt", "lg": "32pt"},
    "radius": {"sm": "2pt", "md": "4pt", "lg": "8pt"},
}

# A doc with one flow diagram between ordinary paragraphs.
DOC = """Intro paragraph.

::: flow
nodes: [Brief, Plan, Render]
:::

Closing paragraph.
"""

# HTML target -> a mermaid fenced block; div + yaml gone; prose preserved.
html = diagrams.expand(DOC, "html", TOK)
check("html: mermaid block", "```mermaid" in html, html)
check("html: flowchart", "flowchart" in html, html)
check("html: node label", "Brief" in html and "Render" in html)
check("html: no raw div", "::: flow" not in html)
check("html: prose kept", "Intro paragraph." in html and "Closing paragraph." in html)

# PDF target -> a typst raw block importing fletcher.
pdf = diagrams.expand(DOC, "pdf", TOK)
check("pdf: typst raw block", "```{=typst}" in pdf, pdf)
check("pdf: fletcher import", "fletcher" in pdf, pdf)
check("pdf: node label", "Brief" in pdf and "Render" in pdf)
check("pdf: brand colour", "#142F54" in pdf or "142F54" in pdf, pdf)
check("pdf: no raw div", "::: flow" not in pdf)

# Non-diagram docs pass through untouched.
plain = "Just text.\n\n::: pullquote\nA quote.\n:::\n"
check("passthrough: pullquote untouched", diagrams.expand(plain, "html", TOK) == plain)

# process: numbered steps, both targets.
PROC = "::: process\nsteps: [Discover, Design, Build, Ship]\n:::\n"
ph = diagrams.expand(PROC, "html", TOK)
check("process html mermaid", "```mermaid" in ph and "Discover" in ph)
pp = diagrams.expand(PROC, "pdf", TOK)
check("process pdf fletcher", "fletcher" in pp and "Ship" in pp)

# timeline: events with at/label.
TL = (
    "::: timeline\nevents:\n  - {at: Q1, label: Kickoff}\n"
    "  - {at: Q2, label: Beta}\n  - {at: Q3, label: GA}\n:::\n"
)
th = diagrams.expand(TL, "html", TOK)
check("timeline html", "```mermaid" in th and "Kickoff" in th and "Q3" in th)
tp = diagrams.expand(TL, "pdf", TOK)
check("timeline pdf", "fletcher" in tp and "Beta" in tp and "Q1" in tp)

# hierarchy/org: nested tree, computed layout.
TREE = (
    "::: org\nroot: CEO\nchildren:\n  - root: CTO\n    children: [Eng, Data]\n"
    "  - COO\n:::\n"
)
oh = diagrams.expand(TREE, "html", TOK)
check("org html mermaid TD", "flowchart TD" in oh and "CEO" in oh and "Eng" in oh)
check(
    "org html edges", oh.count("-->") >= 4, oh
)  # CEO->CTO, CEO->COO, CTO->Eng, CTO->Data
op = diagrams.expand(TREE, "pdf", TOK)
check("org pdf fletcher", "fletcher" in op and "CEO" in op and "Data" in op)
check("org pdf edges", op.count("edge(") >= 4, op)
# layout helper assigns distinct coordinates to siblings
nodes, edges = diagrams._flatten_tree({"root": "A", "children": ["B", "C"]})
xs = {n["x"] for n in nodes if n["depth"] == 1}
check("layout: siblings distinct x", len(xs) == 2, str(nodes))

# Escaping: labels with Typst-special chars (#, [, ]) must NOT break the content
# block — they're emitted as a quoted string literal `[#"..."]`, so the raw `]`/`#`
# never appears unquoted between the `[` and `]` of the node content.
HAZ = '::: flow\nnodes: ["C#", "Q&A]", "Step #1"]\n:::\n'
hp = diagrams.expand(HAZ, "pdf", TOK)
check("escape: quoted string form", '[#"C#"]' in hp, hp)
check("escape: bracket label quoted", '[#"Q&A]"]' in hp, hp)
check("escape: no bare bracket break", "[Q&A]]" not in hp, hp)
# Mermaid side: newline + bracket neutralised.
hh = diagrams.expand('::: flow\nnodes: ["A]B"]\n:::\n', "html", TOK)
check("escape: mermaid no raw bracket in label", '["A]B"]' not in hh, hh)

# HTML diagrams are brand-tokenized (Mermaid %%{init}%% theme block).
check("html: mermaid theme block", "%%{init:" in html and "themeVariables" in html, html)
check("html: theme uses brand colour", "#142F54" in html or "142F54" in html, html)

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: diagrams (flow)")
