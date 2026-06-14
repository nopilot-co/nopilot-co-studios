#!/usr/bin/env python3
"""planner (#39) — composite-document composition manifest + deterministic merge.
Standalone; run: design/.venv/bin/python tests/test_planner.py

Exercises the planner mechanics that need no studio CLI: composition.json CRUD,
rollup/ordering recompute, schema validation, and the assemble merge. Docket
scaffolding (which shells out to `studio docket init`) is covered by the CLI
end-to-end run, not here.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from planner import assemble as asm  # noqa: E402
from planner import audience_model_path  # noqa: E402
from planner import brief as brief_mod  # noqa: E402
from planner import composition as comp  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


def raises(fn, exc=Exception) -> bool:
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


with tempfile.TemporaryDirectory() as td:
    root = Path(td)

    # --- new -----------------------------------------------------------------
    data = comp.new(
        root,
        brand="acme",
        objective="Proposition doc",
        fmt="proposal-pdf",
        session="acme-prop",
    )
    check("new: file written", comp.exists(root))
    check("new: validates clean", comp.validate(data) == [], str(comp.validate(data)))
    check("new: starts at 0.0.0", data["current"] == "0.0.0")
    check(
        "new: refuses to clobber",
        raises(lambda: comp.new(root, brand="x", objective="y", fmt="z", session="s")),
    )

    # --- sections + ordering -------------------------------------------------
    comp.add_section(root, section_id="exec", title="Exec")
    comp.add_section(root, section_id="market", title="Market", after="exec")
    comp.add_section(root, section_id="team", title="Team")
    comp.move_section(root, section_id="team", after="market")
    data = comp.read(root)
    ids = [s["id"] for s in data["sections"]]
    check("order: respects add/move", ids == ["exec", "market", "team"], str(ids))
    check("order: renumbered 1..n", [s["order"] for s in data["sections"]] == [1, 2, 3])
    check("section: folder created", (root / "sections" / "exec").is_dir())
    check(
        "section: dup rejected",
        raises(lambda: comp.add_section(root, section_id="exec", title="dupe")),
    )
    check(
        "section: bad --after rejected",
        raises(lambda: comp.add_section(root, section_id="x", title="X", after="nope")),
    )

    # --- data + viz contract -------------------------------------------------
    comp.add_data(root, section_id="market", rel_path="assets/tam.csv", kind="csv")
    comp.set_viz(
        root,
        section_id="market",
        chart_type="bar",
        source="assets/tam.csv",
        x="seg",
        y="tam",
    )
    data = comp.read(root)
    mkt = next(s for s in data["sections"] if s["id"] == "market")
    check(
        "data: recorded",
        mkt["data_sources"] == [{"path": "assets/tam.csv", "kind": "csv"}],
    )
    check("viz: rendered_by design", mkt["viz"]["rendered_by"] == "design")
    check("viz: still valid", comp.validate(data) == [], str(comp.validate(data)))

    # --- rollup --------------------------------------------------------------
    comp.set_section(root, section_id="exec", status="approved")
    data = comp.read(root)
    check(
        "rollup: 1/3 approved",
        data["rollup"]["approved"] == 1 and data["rollup"]["percent_approved"] == 33,
    )
    check("rollup: not ready", data["rollup"]["ready_to_assemble"] is False)

    # --- assemble guards -----------------------------------------------------
    (root / "sections" / "exec" / "content.md").write_text("<!-- stub -->")
    check(
        "assemble: empty approved content errors",
        raises(lambda: asm.assemble(root), asm.AssembleError),
    )

    # --- assemble merge ------------------------------------------------------
    (root / "sections" / "exec" / "content.md").write_text("# Exec\n\nBody.\n")
    (root / "sections" / "market" / "content.md").write_text("# Market\n\nTAM.\n")
    (root / "sections" / "team" / "content.md").write_text("# Team\n\nPeople.\n")

    # market/team still not approved → full assemble blocked without --allow-partial
    check(
        "assemble: partial needs flag",
        raises(lambda: asm.assemble(root), asm.AssembleError),
    )

    comp.set_section(root, section_id="market", status="approved")
    comp.set_section(root, section_id="team", status="approved")
    data = comp.read(root)
    check(
        "rollup: ready when all approved", data["rollup"]["ready_to_assemble"] is True
    )

    result = asm.assemble(root, bump_kind="minor")
    src = result["source"]
    check(
        "assemble: source at session/inputs",
        src == root / "acme-prop" / "inputs" / "source.md",
        str(src),
    )
    check("assemble: source exists", src.is_file())
    body = src.read_text()
    check(
        "assemble: order preserved",
        body.index("# Exec") < body.index("# Market") < body.index("# Team"),
        body,
    )
    check("assemble: 0.0.0 → 1.0.0", result["version"] == "1.0.0")
    check(
        "assemble: render hint carries format+source",
        "format=proposal-pdf" in result["render_hint"]
        and str(src) in result["render_hint"],
    )
    check(
        "assemble: logged in history",
        comp.read(root)["history"][-1]["event"] == "assemble",
    )

# --- reader-model binding (#46) ----------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)

    # no reader → audience is null, still valid
    d0 = comp.new(root, brand="acme", objective="o", fmt="proposal-pdf", session="s0")
    check("reader: default audience is null", d0["audience"] is None)
    check(
        "reader: valid without audience",
        comp.validate(d0) == [],
        str(comp.validate(d0)),
    )

with tempfile.TemporaryDirectory() as td:
    root = Path(td)

    # a docket-local reader model resolves; bound audience is stored + validates
    model_dir = root / "audience" / "vp-eng"
    model_dir.mkdir(parents=True)
    (model_dir / "_audience.yml").write_text("audience: vp-eng\n")
    check(
        "reader: docket-local model resolves",
        audience_model_path(root, "vp-eng") == model_dir / "_audience.yml",
    )
    check(
        "reader: unknown slug resolves to None",
        audience_model_path(root, "nobody") is None,
    )

    d1 = comp.new(
        root,
        brand="acme",
        objective="o",
        fmt="proposal-pdf",
        session="s1",
        audience="vp-eng",
    )
    check("reader: audience stored", d1["audience"] == "vp-eng")
    check(
        "reader: valid with audience", comp.validate(d1) == [], str(comp.validate(d1))
    )
    check(
        "reader: plan-new note carries audience",
        "audience=vp-eng" in d1["history"][0]["note"],
    )

    # brief is reader-aware when bound
    comp.add_section(root, section_id="exec", title="Exec")
    bp, _ = brief_mod.write_brief(
        root,
        section_id="exec",
        title="Exec",
        objective="o",
        brand="acme",
        fmt="proposal-pdf",
        audience="vp-eng",
        audience_ref=audience_model_path(root, "vp-eng"),
    )
    brief_text = bp.read_text()
    check("reader: brief names the reader", "Reader: `vp-eng`" in brief_text)
    check(
        "reader: brief has Reader fit section + model ref",
        "## Reader fit" in brief_text and "_audience.yml" in brief_text,
    )

    # brand-only brief falls back cleanly
    bp2, _ = brief_mod.write_brief(
        root,
        section_id="exec",
        title="Exec",
        objective="o",
        brand="acme",
        fmt="proposal-pdf",
    )
    check("reader: brand-only brief notes no reader", "brand-only" in bp2.read_text())

    # --- per-section reader-fit gate (#48) -----------------------------------
    check(
        "gate: new section starts with no reader_fit",
        comp.read(root)["sections"][0]["reader_fit"] is None,
    )
    # approving without a recorded fit is blocked when a reader is bound
    check(
        "gate: approve blocked without reader-fit",
        raises(
            lambda: comp.set_section(root, section_id="exec", status="approved"),
            ValueError,
        ),
    )
    # a failing fit (gate need unmet) still blocks; --force overrides
    comp.record_fit(
        root,
        section_id="exec",
        verdict="fail",
        overall=30,
        gates_failed=["proof-at-scale"],
    )
    check(
        "gate: approve blocked on failing fit",
        raises(
            lambda: comp.set_section(root, section_id="exec", status="approved"),
            ValueError,
        ),
    )
    forced = comp.set_section(root, section_id="exec", status="approved", force=True)
    check(
        "gate: --force overrides",
        forced["sections"][0]["status"] == "approved"
        and forced["history"][-1].get("forced") is True,
    )
    # a passing fit lets approval through normally
    comp.set_section(root, section_id="exec", status="drafted")
    comp.record_fit(
        root,
        section_id="exec",
        verdict="pass",
        overall=88,
        source="review/v1.0.0/scorecard.json",
    )
    d2 = comp.set_section(root, section_id="exec", status="approved")
    check(
        "gate: approve allowed after passing fit",
        d2["sections"][0]["status"] == "approved",
    )
    check(
        "gate: reader_fit recorded + valid",
        comp.validate(d2) == [],
        str(comp.validate(d2)),
    )

with tempfile.TemporaryDirectory() as td:
    # no reader bound → approval is NOT gated (unchanged behaviour)
    root = Path(td)
    comp.new(root, brand="acme", objective="o", fmt="proposal-pdf", session="s")
    comp.add_section(root, section_id="x", title="X")
    ungated = comp.set_section(root, section_id="x", status="approved")
    check(
        "gate: no reader → approval ungated",
        ungated["sections"][0]["status"] == "approved",
    )


if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print(
    "PASS: planner (composition CRUD + rollup + ordering + assemble + reader binding + reader-fit gate)"
)
