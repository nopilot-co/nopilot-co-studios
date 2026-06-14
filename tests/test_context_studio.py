#!/usr/bin/env python3
"""context studio (#83) — store + manifest + tool-bridge + pipeline degradation.

Standalone; run any venv with pyyaml + jsonschema:
  nitpicker/.venv/bin/python tests/test_context_studio.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "context-studio" / "scripts"))

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
    os.environ["STUDIOS_DOCKET_ROOT"] = td

    from context import TOOLS, context_root  # noqa: E402
    from context import store, bridge, pipeline  # noqa: E402
    from context import deps as deps_mod  # noqa: E402

    check(
        "context_root resolves",
        context_root() == (Path(td).resolve() / "context"),
        f"got {context_root()}",
    )

    # 1. scaffold
    store.scaffold("demo")
    check("engagement scaffolded", store.engagement_exists("demo"))
    check("sources/ dir present", store.sources_dir("demo").is_dir())
    check("themes/ dir present", store.themes_dir("demo").is_dir())
    check("manifest.json validates", store.manifest_path("demo").is_file())
    check(
        "scaffold rejects duplicate",
        raises(lambda: store.scaffold("demo"), ValueError),
    )

    # 2. manifest contents
    m = store.read_manifest("demo")
    check("manifest engagement matches", m["engagement"] == "demo")
    check("manifest runs[] starts empty", m["runs"] == [])

    # 3. record a run + verify it shows
    store.record_run(
        "demo",
        tool="notion-sources",
        action="extract",
        args=["--database", "abc"],
        exit_code=0,
        note="smoke",
    )
    m = store.read_manifest("demo")
    check("run recorded", len(m["runs"]) == 1)
    check("run captures tool", m["runs"][0]["tool"] == "notion-sources")
    check("run captures args", m["runs"][0]["args"] == ["--database", "abc"])

    # 4. ingest a local file source (no tool needed)
    f = Path(td) / "doc.md"
    f.write_text("# Doc\n")
    out = pipeline.ingest_source("demo", source=str(f), kind="file")
    check("ingest-source ok", out["ok"])
    check("file landed in sources/", Path(out["dest"]).is_file())
    m = store.read_manifest("demo")
    check(
        "ingest-source run recorded", any(r["action"] == "add-file" for r in m["runs"])
    )

    # ingest a URL stub
    out = pipeline.ingest_source("demo", source="https://example.com/a", kind="url")
    check("ingest-url ok", out["ok"])
    check("URL stub written", Path(out["dest"]).is_file())

    # invalid kind raises
    check(
        "ingest-source invalid kind raises",
        raises(
            lambda: pipeline.ingest_source("demo", source=str(f), kind="bogus"),
            ValueError,
        ),
    )

    # 5. bridge reachability — TOOLS map covers 7 tools
    check("TOOLS covers 7 tools", len(TOOLS) == 7)
    report = bridge.reachability_report()
    check("reachability report has all 7 entries", len(report) == 7)

    # 6. bridge.run on a missing tool raises FileNotFoundError
    # Use a tool name that's definitely not on PATH:
    check(
        "bridge.run raises when tool absent",
        raises(lambda: bridge.run("nonexistent-tool-xyz", []), FileNotFoundError),
    )

    # 7. pipeline.ingest_enrich degrades cleanly when source-enrich isn't installed
    if not bridge.reachable("source-enrich"):
        check(
            "pipeline.ingest_enrich degrades when tool absent",
            raises(lambda: pipeline.ingest_enrich("demo"), FileNotFoundError),
        )

    # 8. doctor report shape
    rep = deps_mod.doctor()
    check("doctor reports engagement_count", rep["engagement_count"] == 1)
    check("doctor reports tools_reachable map", len(rep["tools_reachable"]) == 7)
    check("doctor reports tools_missing list", isinstance(rep["tools_missing"], list))

    # 9. status transitions
    store.set_status("demo", "ingesting")
    check("status transition", store.read_version("demo")["status"] == "ingesting")
    check(
        "invalid status rejected",
        raises(lambda: store.set_status("demo", "bogus"), ValueError),
    )

    # 10. file-source rejects missing file
    check(
        "missing file raises FileNotFoundError",
        raises(
            lambda: pipeline.ingest_source(
                "demo", source=str(Path(td) / "missing.md"), kind="file"
            ),
            FileNotFoundError,
        ),
    )

if failures:
    print("FAIL:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(
    "PASS: context-studio (store + manifest + 7-tool bridge + pipeline + degradation + status)"
)
