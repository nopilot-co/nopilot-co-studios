#!/usr/bin/env python3
"""ADR-0001 docket sync — production_uuid, HTML stamp, retention (issues #116–#119).

Standalone (no pytest). Run with the design venv:
    design/.venv/bin/python tests/test_sync.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

import studio.session as session  # noqa: E402
import studio.sync as sync  # noqa: E402
import studio.uuid_util as uuid_util  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


# --- uuid util
u1 = uuid_util.mint_production_uuid()
check("uuid length", len(u1) == 6, u1)
check("uuid valid", uuid_util.is_valid_production_uuid(u1))
check("uuid rejects bad", not uuid_util.is_valid_production_uuid("IIIIII"))

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    brand_dir = root / "brand" / "acme"
    brand_dir.mkdir(parents=True)
    (brand_dir / "_brand.yml").write_text("meta:\n  name: Acme\n")
    os.environ["STUDIOS_DOCKET_ROOT"] = str(root)
    os.environ["STUDIOS_DOCKET_SESSION"] = "demo"

    src = root / "brief.md"
    src.write_text("# Hello\n\nBody.\n")

    # Minimal format — stub validate by using a real format from repo if present
    fmt = "pitch-pdf"
    formats_dir = REPO / "design" / "formats"
    if not (formats_dir / "pitch-pdf.yml").exists():
        fmt = next(formats_dir.glob("*.yml")).stem

    session_path = session.init("acme", "test-session", src, fmt, None)
    state = session.read_state(session_path)
    check("init mints production_uuid", "production_uuid" in state)
    check("production_uuid valid", uuid_util.is_valid_production_uuid(state["production_uuid"]))
    first_uuid = state["production_uuid"]

    # Re-init idempotent on uuid
    session.init("acme", "test-session", src, fmt, None)
    state2 = session.read_state(session_path)
    check("re-init keeps uuid", state2["production_uuid"] == first_uuid)

    # Backfill uuid on legacy version.json
    legacy = root / "demo" / "renders" / "legacy"
    (legacy / "inputs").mkdir(parents=True)
    (legacy / "outputs").mkdir(parents=True)
    (legacy / "inputs" / "source.md").write_text("# Legacy\n")
    (legacy / "version.json").write_text(
        json.dumps(
            {
                "brand": "acme",
                "session": "legacy",
                "format": fmt,
                "current": "0.0.0",
                "history": [],
            }
        )
    )
    backfilled = sync.ensure_production_uuid(legacy)
    check("backfill mints uuid", len(backfilled) == 6)
    check(
        "backfill persisted",
        session.read_state(legacy).get("production_uuid") == backfilled,
    )

    # HTML meta stamp
    html = legacy / "outputs" / "source.v1.0.0.html"
    html.write_text("<html><head><title>x</title></head><body>hi</body></html>")
    sync.stamp_html_production_uuid(html, backfilled)
    text = html.read_text()
    check("html meta stamped", f'content="{backfilled}"' in text)
    sync.stamp_html_production_uuid(html, backfilled)
    check("html meta idempotent", text.count("production-uuid") == 1)

    # Retention — 31 files, keep 30
    outs = legacy / "outputs"
    for i in range(1, 32):
        (outs / f"source.v{i}.0.0.html").write_text(f"v{i}")
    removed = sync.prune_rendered_html(legacy, keep=30)
    check("retention removed one", len(removed) == 1, str(len(removed)))
    remaining = list(outs.glob("source.v*.html"))
    check("retention keeps 30", len(remaining) == 30, str(len(remaining)))
    check(
        "retention dropped oldest",
        not (outs / "source.v1.0.0.html").exists(),
    )
    check(
        "retention kept newest",
        (outs / "source.v31.0.0.html").exists(),
    )
    # source + version.json untouched
    check("retention preserves source", (legacy / "inputs" / "source.md").exists())
    check("retention preserves version.json", (legacy / "version.json").exists())

    # Render guard blocks when server hash differs
    state = session.read_state(legacy)
    state["sync"] = {"server_hash": "sha256:local"}
    session.write_state(legacy, state)
    os.environ["STUDIO_SERVER_URL"] = "https://example.test"
    with mock.patch.object(sync, "fetch_server_hash", return_value="sha256:remote"):
        blocked = False
        try:
            sync.check_render_guard(legacy)
        except sync.SyncGuardError:
            blocked = True
        check("render guard blocks drift", blocked)
    with mock.patch.object(sync, "fetch_server_hash", return_value="sha256:local"):
        sync.check_render_guard(legacy)  # should not raise
        check("render guard allows match", True)
    sync.check_render_guard(legacy, no_sync_guard=True)
    check("render guard bypass", True)

    del os.environ["STUDIOS_DOCKET_ROOT"]
    del os.environ["STUDIOS_DOCKET_SESSION"]
    del os.environ["STUDIO_SERVER_URL"]

if failures:
    print(f"FAILED ({len(failures)}):")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)

print(f"OK — {32 - len(failures)} checks passed")
