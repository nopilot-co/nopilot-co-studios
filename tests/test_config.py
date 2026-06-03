#!/usr/bin/env python3
"""Per-slug working-folder setting (#32). Standalone; run:
    design/.venv/bin/python tests/test_config.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


with tempfile.TemporaryDirectory() as _tmp:
    tmp = Path(_tmp)
    cfg = tmp / "cfg" / "slugs.yml"
    wf = tmp / "context-message-360" / "assets" / "documents"

    # Isolate: point config at a temp file, clear any docket/project env.
    os.environ["STUDIOS_CONFIG"] = str(cfg)
    for var in ("STUDIOS_DOCKET_ROOT", "STUDIOS_DOCKET_SESSION", "STUDIOS_PROJECT_ROOT"):
        os.environ.pop(var, None)

    from studio import brand as brand_mod  # noqa: E402
    from studio import config as cfg_mod  # noqa: E402
    from studio import session as session_mod  # noqa: E402

    # Unset → None; brand falls back to the shared studios store.
    check("unset → None", cfg_mod.working_folder("360") is None)
    check("no config file yet", not cfg.exists())
    check(
        "fallback to studios store",
        "studios/brand/360" in str(brand_mod.brand_root("360")),
        str(brand_mod.brand_root("360")),
    )

    # Set the working folder.
    resolved = cfg_mod.set_working_folder("360", wf)
    check("set returns resolved", resolved == wf.resolve(), str(resolved))
    check("config file written", cfg.is_file())
    check("round-trips", cfg_mod.working_folder("360") == wf.resolve(), str(cfg_mod.working_folder("360")))

    # Brand + session resolve under the working folder.
    check(
        "brand → <wf>/brand/<slug>",
        brand_mod.brand_root("360") == wf.resolve() / "brand" / "360",
        str(brand_mod.brand_root("360")),
    )
    check(
        "session → <wf>/<name>",
        session_mod.session_root("360", "my-session") == wf.resolve() / "my-session",
        str(session_mod.session_root("360", "my-session")),
    )

    # An unconfigured slug is unaffected.
    check("other slug unset", cfg_mod.working_folder("acme") is None)

    # Precedence: an explicit docket env wins over the per-slug working folder.
    droot = tmp / "docket"
    os.environ["STUDIOS_DOCKET_ROOT"] = str(droot)
    os.environ["STUDIOS_DOCKET_SESSION"] = "prod-session"
    check(
        "docket env wins (brand)",
        brand_mod.brand_root("360") == droot.resolve() / "brand" / "360",
        str(brand_mod.brand_root("360")),
    )
    check(
        "docket env wins (session)",
        session_mod.session_root("360", "r1") == droot.resolve() / "prod-session" / "renders" / "r1",
        str(session_mod.session_root("360", "r1")),
    )
    for var in ("STUDIOS_DOCKET_ROOT", "STUDIOS_DOCKET_SESSION"):
        os.environ.pop(var, None)

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: per-slug working folder")
