#!/usr/bin/env python3
"""Formats build-out (slice 1) — schema load + (later) aggregate validation.
Standalone; run: design/.venv/bin/python tests/test_formats.py
"""

from __future__ import annotations

import importlib
import json
import sys
import tempfile
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

# 2. assets.py API (operates on a temp fixture library).
sys.path.insert(0, str(REPO / "design" / "scripts"))
assets = importlib.import_module("studio.assets")

with tempfile.TemporaryDirectory() as td:
    adir = Path(td) / "assets"
    adir.mkdir()
    (adir / "pullquote.yml").write_text(
        "asset: pullquote\nname: Pull quote\ndescription: x\n"
        "buckets: [editorial, documents]\nexports: [html, pdf]\n"
        "authoring: {syntax: '::: pullquote'}\n"
    )
    (adir / "bad.yml").write_text("asset: bad\nname: Bad\n")  # missing required
    check("list_assets", assets.list_assets(adir) == ["bad", "pullquote"])
    check("load_asset", assets.load_asset(adir, "pullquote")["name"] == "Pull quote")
    check("validate good asset", assets.validate_asset(adir, "pullquote") == [])
    check("validate bad asset", len(assets.validate_asset(adir, "bad")) > 0)
    check(
        "asset supports export",
        assets.supports_export(assets.load_asset(adir, "pullquote"), "html"),
    )
    check(
        "asset rejects export",
        not assets.supports_export(assets.load_asset(adir, "pullquote"), "pptx"),
    )

# 3. render output-stem de-versioning (fixes …-v1.0.0.v1.1.0 compounding).
render_mod = importlib.import_module("studio.render")
check(
    "strip versioned stem",
    render_mod._strip_version_label("client-proposition-pitch-pdf-v1.0.0")
    == "client-proposition-pitch-pdf",
)
check(
    "leave unversioned stem",
    render_mod._strip_version_label("client-proposition") == "client-proposition",
)
check(
    "only trailing label stripped",
    render_mod._strip_version_label("v1.2.3-notes") == "v1.2.3-notes",
)

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: test_formats (schemas)")
