#!/usr/bin/env python3
"""tools standalone invariant (#71, ADR-004) — dumb-tool CI check.

Standalone; run: nitpicker/.venv/bin/python tests/test_tools_standalone.py
(any venv with PyYAML works; the script under test has no studio deps.)

Exercises scripts/check_tools_standalone.py against synthetic tools/ trees so
we know it flags every banned pattern AND lets a clean tool through.
"""

from __future__ import annotations

import sys
import tempfile
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import check_tools_standalone as ct  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


def _write_manifest(d: Path, *, depends: bool = False) -> None:
    body = "tool: t\nname: T\nsummary: t\n"
    if depends:
        body += "depends_on_studio: true\n"
    (d / "tool.yaml").write_text(body)


def _write_script(d: Path, name: str, body: str) -> None:
    (d / "scripts").mkdir(parents=True, exist_ok=True)
    (d / "scripts" / name).write_text(textwrap.dedent(body).lstrip())


# 1. Empty / missing tools dir is fine — scaffold-only state must not fail CI.
with tempfile.TemporaryDirectory() as td:
    root = Path(td) / "tools"
    check("empty tools dir → no findings", ct.check(root) == [])
    root.mkdir()
    check("present-but-empty tools dir → no findings", ct.check(root) == [])

# 2. A clean tool with a manifest + studio-free script passes.
with tempfile.TemporaryDirectory() as td:
    tools = Path(td) / "tools"
    t = tools / "clean-tool"
    t.mkdir(parents=True)
    _write_manifest(t)
    _write_script(
        t,
        "clean.py",
        """
        import json
        import sys
        from pathlib import Path

        def main(argv):
            data = json.loads(Path(argv[1]).read_text())
            print(json.dumps(data))

        if __name__ == "__main__":
            main(sys.argv)
        """,
    )
    out = ct.check(tools)
    check("clean tool → no findings", out == [], f"got {out!r}")

# 3. Missing tool.yaml — flagged.
with tempfile.TemporaryDirectory() as td:
    tools = Path(td) / "tools"
    t = tools / "no-manifest"
    t.mkdir(parents=True)
    _write_script(t, "x.py", "print('hi')\n")
    out = ct.check(tools)
    check(
        "missing tool.yaml flagged",
        any("missing tool.yaml" in f for f in out),
        f"got {out!r}",
    )

# 4. depends_on_studio: true — flagged.
with tempfile.TemporaryDirectory() as td:
    tools = Path(td) / "tools"
    t = tools / "studio-dependent"
    t.mkdir(parents=True)
    _write_manifest(t, depends=True)
    _write_script(t, "x.py", "print('hi')\n")
    out = ct.check(tools)
    check(
        "depends_on_studio:true flagged",
        any("depends_on_studio" in f for f in out),
        f"got {out!r}",
    )

# 5. Banned studio import — flagged.
with tempfile.TemporaryDirectory() as td:
    tools = Path(td) / "tools"
    t = tools / "bad-imports"
    t.mkdir(parents=True)
    _write_manifest(t)
    _write_script(
        t,
        "bad.py",
        """
        from planner import composition
        from studio import brand
        import nit.tests
        """,
    )
    out = ct.check(tools)
    check(
        "studio import `planner` flagged",
        any("planner" in f and "banned studio import" in f for f in out),
        f"got {out!r}",
    )
    check(
        "studio import `studio` flagged",
        any("studio" in f and "banned studio import" in f for f in out),
        f"got {out!r}",
    )
    check(
        "studio import `nit` flagged",
        any("nit" in f and "banned studio import" in f for f in out),
        f"got {out!r}",
    )

# 6. Banned string `studios.yml` — flagged.
with tempfile.TemporaryDirectory() as td:
    tools = Path(td) / "tools"
    t = tools / "bad-strings"
    t.mkdir(parents=True)
    _write_manifest(t)
    _write_script(
        t,
        "bad.py",
        """
        registry_path = "studios.yml"
        legacy_role = "creative-director"
        """,
    )
    out = ct.check(tools)
    check(
        "string `studios.yml` flagged",
        any("studios.yml" in f for f in out),
        f"got {out!r}",
    )
    check(
        "string `creative-director` flagged",
        any("creative-director" in f for f in out),
        f"got {out!r}",
    )

# 7. Hardcoded studio/context path — flagged.
with tempfile.TemporaryDirectory() as td:
    tools = Path(td) / "tools"
    t = tools / "bad-paths"
    t.mkdir(parents=True)
    _write_manifest(t)
    _write_script(
        t,
        "bad.py",
        """
        OUT = "~/context/studios/something/foo"
        ENV = "$STUDIOS_DOCKET_ROOT"
        """,
    )
    out = ct.check(tools)
    check(
        "hardcoded studios path flagged",
        any("~/context/studios/" in f for f in out),
        f"got {out!r}",
    )
    check(
        "hardcoded $STUDIOS_DOCKET_ROOT flagged",
        any("STUDIOS_DOCKET_ROOT" in f for f in out),
        f"got {out!r}",
    )

# 8. Shell script + invalid YAML are also covered.
with tempfile.TemporaryDirectory() as td:
    tools = Path(td) / "tools"
    t = tools / "shell-tool"
    t.mkdir(parents=True)
    _write_manifest(t)
    _write_script(t, "install.sh", "#!/bin/bash\nfrom studio import x\n")
    out = ct.check(tools)
    check(
        "banned import in .sh flagged",
        any("install.sh" in f for f in out),
        f"got {out!r}",
    )

with tempfile.TemporaryDirectory() as td:
    tools = Path(td) / "tools"
    t = tools / "bad-yaml"
    t.mkdir(parents=True)
    (t / "tool.yaml").write_text(":\n  bad indent\n  - nope\n")
    out = ct.check(tools)
    check(
        "invalid YAML manifest flagged",
        any("invalid YAML" in f for f in out),
        f"got {out!r}",
    )

if failures:
    print("FAIL:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("PASS: tools standalone invariant (8 scenarios, 14 assertions)")
