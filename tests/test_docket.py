#!/usr/bin/env python3
"""Docket stack (issues #8–#12) — metacontent strip/history, content bump,
docket scaffolding + manifest validation, and brand-import provenance.

Standalone (no pytest). Run with the design venv:
    design/.venv/bin/python tests/test_docket.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

import studio.content as content  # noqa: E402
import studio.docket as docket  # noqa: E402
import studio.ingest as ingest  # noqa: E402
import studio.metacontent as mc  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


SAMPLE = """\
---
version: 1.0.0
status: approved
author: JT
---

<!-- nopilot:guidance
Lead with the value proposition. Cap to max_slides.
-->

# Client Proposition

The real, client-facing body text.

<!-- nopilot:comment author=user
Tighten this before approval.
-->

More body text.

<!-- nopilot:history   (append-only — newest last)
- 2026-05-30 v1.0.0 author=JT status=approved note="initial"
-->
"""

# 1. metacontent.strip removes front-matter + every nopilot region; keeps body.
stripped = mc.strip(SAMPLE)
check("strip: no nopilot leak", not mc.has_meta_leak(stripped), stripped)
check("strip: no front-matter", "version: 1.0.0" not in stripped)
check("strip: keeps body", "The real, client-facing body text." in stripped)
check("strip: keeps heading", "# Client Proposition" in stripped)
check("strip: drops guidance prose", "Lead with the value proposition" not in stripped)
check("strip: drops internal comment", "Tighten this before approval" not in stripped)
check("leak detector positive", mc.has_meta_leak(SAMPLE))

# 2. read_meta parses front-matter.
meta = mc.read_meta(SAMPLE)
check("read_meta version", meta.get("version") == "1.0.0", str(meta))
check("read_meta status", meta.get("status") == "approved")

# 3. append_history creates + appends (newest last), no front-matter required.
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "note.md"
    p.write_text("# Body\n\nText.\n")
    mc.append_history(p, version="0.1.0", author="JT", status="draft", note="first")
    mc.append_history(p, version="1.0.0", author="JT", status="approved", note="ship")
    t = p.read_text()
    check("history: one block", t.count("nopilot:history") == 1, t)
    check("history: both entries", "v0.1.0" in t and "v1.0.0" in t)
    check("history: newest last", t.index("v0.1.0") < t.index("v1.0.0"))
    check("history: body intact", "# Body" in t)

# 4. content.bump stamps filename + front-matter + history.
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "client-proposition-primary-v1.0.0.md"
    p.write_text("---\nversion: 1.0.0\nstatus: draft\n---\n\n# Body\n")
    check("content: current_version", content.current_version(p) == "1.0.0")
    new_path, new_ver = content.bump(
        p, "minor", author="JT", status="approved", note="rev"
    )
    check("content: minor bump", new_ver == "1.1.0", new_ver)
    check(
        "content: filename stamped", new_path.name.endswith("-v1.1.0.md"), new_path.name
    )
    check("content: old file gone", not p.exists())
    nt = new_path.read_text()
    check("content: front-matter updated", "version: 1.1.0" in nt, nt)
    check("content: status updated", "status: approved" in nt)
    check("content: history appended", "v1.1.0" in nt and "nopilot:history" in nt)
    # stamping a name with no label adds one
    check(
        "content: add label", content.stamped_name("foo.md", "2.0.0") == "foo-v2.0.0.md"
    )

# 5. docket.init_docket builds the tree; manifests validate.
with tempfile.TemporaryDirectory() as td:
    root = Path(td) / "prod_root"
    docket.init_docket(root, brand="360", session="360-proposition-definition")
    for rel in (
        "CLAUDE.md",
        "README.md",
        "nopilot-co-studios-plugin.md",
        ".gitignore",
        "production-manifest.json",
        "specs/content-defaults.yaml",
        "specs/formats",
        "assets",
        "brand",
        "360-proposition-definition/inputs/brief.md",
        "360-proposition-definition/content",
        "360-proposition-definition/outputs",
        "360-proposition-definition/logs",
        "360-proposition-definition/session-manifest.json",
    ):
        check(f"docket: {rel} exists", (root / rel).exists(), str(root / rel))
    pm = docket.read_manifest(root / "production-manifest.json")
    check(
        "docket: production-manifest valid",
        docket.validate_manifest("production", pm) == [],
    )
    check("docket: session listed", "360-proposition-definition" in pm["sessions"])
    sm = docket.read_manifest(
        root / "360-proposition-definition" / "session-manifest.json"
    )
    check(
        "docket: session-manifest valid", docket.validate_manifest("session", sm) == []
    )
    check(
        ".gitignore ignores outputs", "**/outputs/" in (root / ".gitignore").read_text()
    )

    # idempotent re-init
    docket.init_docket(root, session="360-proposition-definition")
    pm2 = docket.read_manifest(root / "production-manifest.json")
    check(
        "docket: idempotent sessions",
        pm2["sessions"].count("360-proposition-definition") == 1,
    )

# 6. validate_manifest catches a bad manifest.
errs = docket.validate_manifest("session", {"schema_version": "1.0"})
check("validate: catches missing required", len(errs) > 0, str(errs))

# 7. ingest.import_from copies a Brand Docket into the docket + records provenance.
with tempfile.TemporaryDirectory() as td:
    root = Path(td) / "prod_root"
    docket.init_docket(root, session="s1")
    # a fake upstream Brand Docket
    upstream = Path(td) / "upstream-brand" / "acme"
    upstream.mkdir(parents=True)
    (upstream / "_brand.yml").write_text(
        "meta: {name: Acme}\ncolor: {primary: '#ff0000'}\n"
    )
    (upstream / "tone-of-voice.md").write_text("Be bold.\n")

    os.environ["STUDIOS_DOCKET_ROOT"] = str(root)
    try:
        report = ingest.import_from("acme", upstream)
    finally:
        os.environ.pop("STUDIOS_DOCKET_ROOT", None)
    dest = root / "brand" / "acme"
    check("import: brand copied", (dest / "_brand.yml").exists(), report)
    check("import: tov copied", (dest / "tone-of-voice.md").exists())
    pm = docket.read_manifest(root / "production-manifest.json")
    entry = next((d for d in pm["brand_dockets"] if d["slug"] == "acme"), None)
    check(
        "import: provenance recorded", entry is not None, str(pm.get("brand_dockets"))
    )
    check("import: origin noted", entry and entry.get("imported_from") == str(upstream))
    check(
        "import: content hash",
        entry and entry.get("content_hash", "").startswith("sha256:"),
    )
    check(
        "import: manifest still valid", docket.validate_manifest("production", pm) == []
    )

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: docket stack (metacontent + content + docket + import)")
