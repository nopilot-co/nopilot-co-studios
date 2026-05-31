#!/usr/bin/env python3
"""Storage-root abstraction (issue #7) — verifies both studios resolve roots
identically: docket override repoints context + brand, defaults preserve legacy
behaviour, and resolution is call-time (not frozen at import).

Standalone (no pytest dependency). Run with a venv that can import both packages:
    design/.venv/bin/python tests/test_storage_root.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))
sys.path.insert(0, str(REPO / "messaging" / "scripts"))

import message  # noqa: E402
import studio  # noqa: E402

HOME = Path.home()
STUDIOS = HOME / "context" / "studios"
failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}\n      got:  {got}\n      want: {want}")


def clear(*keys: str) -> None:
    for k in keys:
        os.environ.pop(k, None)


for mod, sname in ((studio, "design"), (message, "messaging")):
    # 1. Defaults (no overrides), from a neutral cwd with no .wip ancestor.
    with tempfile.TemporaryDirectory() as td:
        os.chdir(td)
        clear("STUDIOS_DOCKET_ROOT", "STUDIOS_PROJECT_ROOT")
        check(f"{sname} default docket is None", mod.docket_root(), None)
        check(
            f"{sname} default context", mod.resolve_context_root(sname), STUDIOS / sname
        )
        check(f"{sname} default brand", mod.brand_root_base(), STUDIOS / "brand")

        # 2. Docket override repoints BOTH context and brand under the docket.
        dk = Path(td) / "prod_root"
        os.environ["STUDIOS_DOCKET_ROOT"] = str(dk)
        check(f"{sname} docket context", mod.resolve_context_root(sname), dk.resolve())
        check(f"{sname} docket brand", mod.brand_root_base(), dk.resolve() / "brand")

        # 3. Call-time resolution: changing env AFTER import takes effect.
        dk2 = Path(td) / "switched"
        os.environ["STUDIOS_DOCKET_ROOT"] = str(dk2)
        check(
            f"{sname} docket call-time switch",
            mod.resolve_context_root(sname),
            dk2.resolve(),
        )
        clear("STUDIOS_DOCKET_ROOT")

        # 4. Back-compat: STUDIOS_PROJECT_ROOT still maps to the outbox layout,
        #    and brand stays the shared store (project root is not docket-local).
        proj = Path(td) / "proj"
        os.environ["STUDIOS_PROJECT_ROOT"] = str(proj)
        check(
            f"{sname} project context",
            mod.resolve_context_root(sname),
            proj / "agents" / "claude" / "outbox" / sname,
        )
        check(
            f"{sname} project brand stays shared",
            mod.brand_root_base(),
            STUDIOS / "brand",
        )
        clear("STUDIOS_PROJECT_ROOT")

os.chdir(REPO)

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: storage-root abstraction (design + messaging)")
