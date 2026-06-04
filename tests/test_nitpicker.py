#!/usr/bin/env python3
"""nitpicker (#53) — consume the audience studio's structured reader model.
Standalone; run: design/.venv/bin/python tests/test_nitpicker.py

Covers `nit new --audience <slug>`: resolving an `_audience.yml`, projecting it
into `inputs/icp.md`, and recording the slug — so the existing audience-fit skill
reads one shared reader model. Env is set before importing nit so CONTEXT_ROOT and
the audience resolver both land in temp dirs.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Redirect session outputs + audience resolution into temp dirs *before* import.
_proj = tempfile.mkdtemp()
_docket = tempfile.mkdtemp()
os.environ["STUDIOS_PROJECT_ROOT"] = _proj
os.environ["STUDIOS_DOCKET_ROOT"] = _docket

sys.path.insert(0, str(REPO / "nitpicker" / "scripts"))
from nit import audience as aud  # noqa: E402
from nit import session as sess  # noqa: E402

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


# A docket-local reader model.
MODEL_YML = """\
audience: vp-eng
name: VP Eng at a scaleup
status: validated
persona: {role: VP of Engineering, one_line: Owns delivery + reliability.}
psychographics:
  values: [engineering rigor]
  motivations: [ship reliably at 2x scale]
need_state:
  stage: evaluating
  needs:
    - {id: reliability-at-scale, statement: Keep p99 as load doubles, priority: critical}
    - {id: reduce-toil, statement: Cut on-call, priority: high}
  objections:
    - {objection: yet another tool, counter_needed: low-ops story}
  decision_factors: [proof-at-scale]
communication:
  register: peer-technical
  avoid: [hype superlatives]
"""

model_dir = Path(_docket) / "audience" / "vp-eng"
model_dir.mkdir(parents=True)
(model_dir / "_audience.yml").write_text(MODEL_YML)

# --- resolution ---------------------------------------------------------------
check(
    "resolve: docket-local model found",
    aud.model_path("vp-eng") == model_dir / "_audience.yml",
)
check("resolve: unknown slug → None", aud.model_path("nobody") is None)

# --- projection ---------------------------------------------------------------
icp = aud.render_icp(aud.load(model_dir / "_audience.yml"))
check("project: names the reader", "VP Eng at a scaleup" in icp)
check(
    "project: carries need + priority",
    "reliability-at-scale" in icp and "critical" in icp,
)
check("project: carries objection", "yet another tool" in icp)
check(
    "project: carries comms prefs",
    "peer-technical" in icp and "hype superlatives" in icp,
)
check("project: marks provenance (don't hand-edit)", "do not hand-edit" in icp)

# --- session wiring -----------------------------------------------------------
target = str(REPO / "README.md")
root = sess.new("demo-aud", target, audience="vp-eng")
icp_file = root / "inputs" / "icp.md"
check(
    "session: icp.md is the projection",
    icp_file.is_file() and "VP Eng at a scaleup" in icp_file.read_text(),
)
state = sess.read_state(root)
check("session: audience recorded in version.json", state.get("audience") == "vp-eng")

# unknown slug → clear error
check(
    "session: unknown audience errors",
    raises(lambda: sess.new("demo-ghost", target, audience="ghost"), ValueError),
)

# no audience → freetext stub (unchanged behaviour)
root2 = sess.new("demo-stub", target)
stub = (root2 / "inputs" / "icp.md").read_text()
check("session: no audience → stub icp", "describe the target audience" in stub)
check(
    "session: no audience → audience null",
    sess.read_state(root2).get("audience") is None,
)


if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: nitpicker (reader-model resolve + project to icp.md + session wiring)")
