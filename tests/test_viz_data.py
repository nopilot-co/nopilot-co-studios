#!/usr/bin/env python3
"""Normalised CSV sidecar (viz_data) — long-form CSV per viz, stable ids,
never-crash, NEW-type CSV-without-render, scan_session.
Standalone; run: design/.venv/bin/python tests/test_viz_data.py
"""

from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import viz_data  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


def rows_of(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


DOC = """---
title: t
---

# Title

::: chart
type: bar
x: [Q1, Q2]
series:
  - {name: Plan, y: [10, 14]}
  - {name: Actual, y: [12, 18]}
:::

| Region | Q1 | Q2 |
|--------|----|----|
| EMEA | 120 | 140 |

::: chart
type: pie
labels: [A, B, C]
values: [30, 50, 20]
:::

::: flow
nodes: [Brief, Plan, Render]
:::

::: hierarchy
root: Strategy
children:
  - root: Pillar A
    children: [Init 1, Init 2]
:::

::: swimlane
lanes:
  - {lane: Customer, nodes: [Request, Approve]}
  - {lane: Ops, nodes: [Fulfil]}
:::

::: decision-tree
root: Qualified?
children:
  - {condition: "yes", root: Proposal}
  - {condition: "no", root: Nurture}
:::

::: bullseye
rings:
  - {ring: core, items: [A, B]}
:::

::: matrix
items:
  - {label: A, x: high, y: low, quadrant: Win}
:::

::: funnel
stages:
  - {stage: Visits, value: 1000}
  - {stage: Signups, value: 200}
:::

::: heatmap
rag: true
rows: [T1]
cols: [Q1, Q2]
cells:
  - [green, red]
:::

```
| ignored | table |
|---------|-------|
| in | code |
```
"""

with tempfile.TemporaryDirectory() as td:
    dd = Path(td) / "data"
    man = viz_data.scan(DOC, dd)
    by_id = {m["viz_id"]: m for m in man}

    # --- document-order ids, code-fenced table ignored ---
    ids = [m["viz_id"] for m in man]
    check("count = 11 viz (code table ignored)", len(man) == 11, str(ids))
    check("first is 01-bar", ids[0] == "01-bar", ids[0])
    check("table detected once", sum(1 for i in ids if i.endswith("-table")) == 1, str(ids))

    # --- charts long form (multi-series) ---
    bar = rows_of(dd / "01-bar.csv")
    check("bar header", bar[0] == ["viz_id", "type", "series", "x", "y"], str(bar[0]))
    check("bar long-form rows = 4", len(bar) - 1 == 4, str(bar))
    check("bar has Plan Q1 10", ["01-bar", "bar", "Plan", "Q1", "10"] in bar)
    check("bar has Actual Q2 18", ["01-bar", "bar", "Actual", "Q2", "18"] in bar)

    # --- pie folds into series/x/y ---
    pie_id = next(i for i in ids if i.endswith("-pie"))
    pie = rows_of(dd / f"{pie_id}.csv")
    check("pie rows = 3", len(pie) - 1 == 3, str(pie))
    check("pie label=value", pie[1][2] == pie[1][3] == "A" and pie[1][4] == "30", str(pie[1]))

    # --- table verbatim ---
    tbl_id = next(i for i in ids if i.endswith("-table"))
    tbl = rows_of(dd / f"{tbl_id}.csv")
    check("table verbatim header", tbl[0] == ["Region", "Q1", "Q2"], str(tbl[0]))
    check("table verbatim row", tbl[1] == ["EMEA", "120", "140"], str(tbl[1]))

    # --- flow nodes/edges ---
    flow_id = next(i for i in ids if i.endswith("-flow"))
    fn = rows_of(dd / f"{flow_id}.nodes.csv")
    fe = rows_of(dd / f"{flow_id}.edges.csv")
    check("flow 3 nodes", len(fn) - 1 == 3, str(fn))
    check("flow 2 edges", len(fe) - 1 == 2, str(fe))
    check("flow node cols", fn[0] == ["viz_id", "node_id", "label", "order"], str(fn[0]))

    # --- hierarchy parent derived ---
    h_id = next(i for i in ids if i.endswith("-hierarchy"))
    hn = rows_of(dd / f"{h_id}.nodes.csv")
    check("hierarchy parent col", hn[0][-1] == "parent", str(hn[0]))
    check("hierarchy child has parent", any(r[-1].startswith("n") for r in hn[1:]), str(hn))

    # --- the 6 newer types now render (Phase 2) AND still ship CSV ---
    for new_type in ("swimlane", "decision-tree", "bullseye", "matrix", "funnel", "heatmap"):
        e = next((m for m in man if m["type"] == new_type), None)
        check(f"{new_type} present", e is not None, str(ids))
        if e:
            check(f"{new_type} rendered=true", e["rendered"] is True)
            check(f"{new_type} engine=frameworks", e["engine"] == "frameworks")
            for rel in e["files"]:
                check(f"{new_type} csv exists", (Path(td) / rel).exists() if not Path(rel).is_absolute() else Path(rel).exists(), rel)

    # swimlane lane column populated
    sw_id = next(i for i in ids if i.endswith("-swimlane"))
    sw = rows_of(dd / f"{sw_id}.nodes.csv")
    check("swimlane lane col", sw[0] == ["viz_id", "node_id", "label", "order", "lane"], str(sw[0]))
    check("swimlane has Ops lane", any(r[-1] == "Ops" for r in sw[1:]), str(sw))

    # decision-tree edge conditions
    dt_id = next(i for i in ids if i.endswith("-decision-tree"))
    de = rows_of(dd / f"{dt_id}.edges.csv")
    check("dtree edge condition col", de[0] == ["viz_id", "source", "target", "condition"], str(de[0]))
    check("dtree has yes condition", any(r[-1] == "yes" for r in de[1:]), str(de))

    # heatmap rag in rag column
    hm_id = next(i for i in ids if i.endswith("-heatmap"))
    hm = rows_of(dd / f"{hm_id}.csv")
    check("heatmap cols", hm[0] == ["viz_id", "type", "row", "col", "value", "rag"], str(hm[0]))
    check("heatmap rag value", any(r[5] == "green" for r in hm[1:]), str(hm))

# --- chart series authored with `label:` populates the CSV `series` column ---
with tempfile.TemporaryDirectory() as td_lbl:
    dd = Path(td_lbl) / "data"
    doc = (
        "::: chart\ntype: bar\nx: [Q1, Q2]\n"
        "series:\n  - {label: Product, y: [10, 14]}\n  - {label: Service, y: [12, 18]}\n:::\n"
    )
    viz_data.scan(doc, dd)
    bar = rows_of(dd / "01-bar.csv")
    series_col = {r[2] for r in bar[1:]}
    check("csv series from label", {"Product", "Service"} <= series_col, str(bar))

# --- id stability across two scans ---
with tempfile.TemporaryDirectory() as td2:
    m1 = viz_data.scan(DOC, Path(td2) / "a")
    m2 = viz_data.scan(DOC, Path(td2) / "b")
    check("id stability", [m["viz_id"] for m in m1] == [m["viz_id"] for m in m2])

# --- never crash on malformed: bad chart skipped, good ones survive ---
with tempfile.TemporaryDirectory() as td3:
    bad = (
        "::: chart\ntype: bar\nx: [A]\ny: notanumber\n:::\n\n"
        "::: flow\nnodes: [A, B]\n:::\n"
    )
    try:
        m = viz_data.scan(bad, Path(td3) / "d")
        crashed = False
    except Exception:  # noqa: BLE001
        crashed = True
    check("malformed does not crash", not crashed)
    check("good viz still emitted after bad", any(x["type"] == "flow" for x in m), str([x["viz_id"] for x in m]))

# --- scan_session: meta-strip + outputs/data + relative file paths ---
with tempfile.TemporaryDirectory() as td4:
    sess = Path(td4) / "sess"
    (sess / "inputs").mkdir(parents=True)
    (sess / "inputs" / "source.md").write_text(DOC, encoding="utf-8")
    man = viz_data.scan_session(sess)
    check("scan_session returns manifest", len(man) == 11, str(len(man)))
    check("data dir created", (sess / "outputs" / "data").is_dir())
    check(
        "files are session-relative",
        all(m["files"][0].startswith("outputs/data/") for m in man),
        str(man[0]["files"]),
    )
    check("empty source -> []", viz_data.scan_session(Path(td4) / "nope") == [])

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: viz_data (17 types, 6 families, CSV sidecars)")
