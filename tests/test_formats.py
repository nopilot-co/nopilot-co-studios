#!/usr/bin/env python3
"""Formats build-out (slice 1) — schema load + (later) aggregate validation.
Standalone; run: design/.venv/bin/python tests/test_formats.py
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCHEMAS = REPO / "design" / "scripts" / "studio" / "schemas"
failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


# 1. Both schemas are valid JSON and declare the 2020-12 dialect.
for s in ("asset.schema.json", "format.schema.json"):
    data = json.loads((SCHEMAS / s).read_text())
    check(f"{s} is 2020-12", data.get("$schema", "").endswith("2020-12/schema"), s)

check(
    "format schema has assets",
    "assets" in json.loads((SCHEMAS / "format.schema.json").read_text())["properties"],
)
asset_schema = json.loads((SCHEMAS / "asset.schema.json").read_text())
check(
    "asset schema requires core fields",
    set(asset_schema.get("required", [])) >= {"asset", "name", "buckets", "exports"},
)

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: test_formats (schemas)")
