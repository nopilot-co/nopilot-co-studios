#!/usr/bin/env python3
"""Contract provenance & fail-closed validation (#101).

Verifies:
- contract_hash is stable across runs and ignores identity-only fields
- resolve_for_session returns scope=global for vanilla sessions
- A session/contract.lock.yml flips scope=local and uses the frozen contract
- A render against a malformed contract raises (fail-closed)
- record_render stamps built_against onto state + history entry

Run: design/.venv/bin/python tests/test_provenance.py
"""

from __future__ import annotations

import copy
import importlib
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

formats = importlib.import_module("studio.formats")
render = importlib.import_module("studio.render")
session_mod = importlib.import_module("studio.session")

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


# 1. contract_hash is stable + key-order independent.
r1 = formats.resolve("showcase-html")
r2 = formats.resolve("showcase-html")
h1 = formats.contract_hash(r1)
h2 = formats.contract_hash(r2)
check("contract_hash stable across calls", h1 == h2, f"{h1[:8]} != {h2[:8]}")
check("contract_hash is 64 hex chars", len(h1) == 64 and all(c in "0123456789abcdef" for c in h1))

# 2. Identity-only fields don't affect the hash (so renaming a slug doesn't
#    invalidate the governance hash of an unchanged contract).
r_renamed = copy.deepcopy(r1)
r_renamed["name"] = "Some Other Display Name"
r_renamed["purpose_name"] = "Different Display Purpose"
check(
    "contract_hash ignores display fields (name/*_name)",
    formats.contract_hash(r_renamed) == h1,
)

# 3. Changing a governance term DOES change the hash.
r_changed = copy.deepcopy(r1)
r_changed["ruleset"]["structure"] = "single-axis"  # would be a real divergence
check(
    "contract_hash flips on governance change",
    formats.contract_hash(r_changed) != h1,
)

# 4. resolve_for_session: no lock = global scope.
with tempfile.TemporaryDirectory() as td:
    session = Path(td)
    resolved, ba = formats.resolve_for_session("showcase-html", session)
    check("global scope when no lock", ba["scope"] == "global")
    check("global scope: derived_from is null", ba["derived_from"] is None)
    check("global scope: id is slug", ba["id"] == "showcase-html")
    check("global scope: hash matches direct contract_hash",
          ba["hash"] == formats.contract_hash(resolved))

# 5. resolve_for_session: with a lock = local scope, lock wins.
with tempfile.TemporaryDirectory() as td:
    session = Path(td)
    base = formats.resolve("showcase-html")
    forked = copy.deepcopy(base)
    forked["ruleset"]["max_scroll_screens"] = 99  # non-sealed, plausibly forkable
    lock_path = formats.freeze_local_lock(session, forked, derived_from="showcase-html")
    check("freeze_local_lock writes contract.lock.yml", lock_path.exists())
    resolved, ba = formats.resolve_for_session("showcase-html", session)
    check("local scope when lock present", ba["scope"] == "local")
    check("local scope: derived_from records parent",
          ba["derived_from"] == "showcase-html")
    check("local scope: lock is authoritative (forked value wins)",
          resolved["ruleset"]["max_scroll_screens"] == 99)
    check("local scope: hash is over the frozen contract, not the global resolve",
          ba["hash"] == formats.contract_hash(resolved))
    check("local scope: hash differs from global",
          ba["hash"] != formats.contract_hash(base))

# 6. Malformed lock raises ValueError.
with tempfile.TemporaryDirectory() as td:
    session = Path(td)
    (session / "contract.lock.yml").write_text("scope: nonsense\n")
    try:
        formats.load_local_lock(session)
        failures.append("malformed local lock should raise ValueError")
    except ValueError as e:
        check("malformed lock error mentions scope/contract", "scope" in str(e).lower())

# 7. validate_resolved catches a broken contract.
broken = {"slug": "x", "purpose": "x", "export": "x"}  # missing layout, asset_type, etc.
errs = formats.validate_resolved(broken)
check("validate_resolved flags missing required fields", len(errs) > 0)

# 8. record_render stamps built_against onto state + history entry.
with tempfile.TemporaryDirectory() as td:
    session = Path(td)
    (session / "version.json").write_text(json.dumps({
        "brand": "nopilot", "session": "test", "format": "showcase-html",
        "source_filename": "source.md", "created": "2026-06-10",
        "current": "0.0.0", "history": [],
    }))
    ba = {"id": "showcase-html", "hash": h1, "scope": "global",
          "derived_from": None, "locked_at": None}
    session_mod.record_render(
        session, "1.0.0", ["html"], {"html": session / "outputs" / "x.html"},
        built_against=ba,
    )
    state = json.loads((session / "version.json").read_text())
    check("state.built_against stamped", state.get("built_against") == ba)
    check("history entry has built_against", state["history"][0].get("built_against") == ba)
    check("state.current = new version", state["current"] == "1.0.0")

# 9. Fail-closed at render: a session with a deliberately-broken lock raises.
with tempfile.TemporaryDirectory() as td:
    session = Path(td)
    (session / "inputs").mkdir()
    (session / "outputs").mkdir()
    (session / "inputs" / "source.md").write_text("# x\n")
    (session / "version.json").write_text(json.dumps({
        "brand": "nopilot", "session": "test", "format": "showcase-html",
        "source_filename": "source.md", "created": "2026-06-10",
        "current": "0.0.0", "history": [],
    }))
    broken_contract = {"slug": "showcase-html", "purpose": "showcase",
                       "export": "html"}  # missing everything else
    formats.freeze_local_lock(session, broken_contract, derived_from="showcase-html")
    try:
        render.render(session, "minor")
        failures.append("render against malformed local lock should raise")
    except RuntimeError as e:
        check("render error explains schema fail-closed",
              "failed schema validation" in str(e), str(e)[:200])

if failures:
    print(f"FAIL ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(f"OK — provenance stamp + fail-closed validation verified")
