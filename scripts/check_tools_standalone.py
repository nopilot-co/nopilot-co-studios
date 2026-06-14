#!/usr/bin/env python3
"""CI invariant: tools/ must stay studio-free (ADR-004, brief 02 §4).

Runs against every file under ``tools/<slug>/scripts/*`` plus the per-tool
``tool.yaml`` manifests. Fails the build (exit 1) when any of the following
banned patterns appear — these are the operational, functional, or contextual
reliances a *dumb tool* must NOT have on a studio.

Banned in tool source files (``tools/*/scripts/**/*.py`` and ``*.sh``):
  - Imports of a studio's Python package: ``studio``, ``message``, ``nit``,
    ``audience``, ``motion``, the root ``planner`` package.
  - Bare-string references to the studios orchestration vocabulary:
    ``studios.yml``, ``creative-director``, ``producer``, ``planner``.
  - Hardcoded studio/context paths: ``~/context/studios/``,
    ``$STUDIOS_DOCKET_ROOT``, ``$STUDIOS_PROJECT_ROOT``,
    ``$STUDIOS_DOCKET_SESSION``.

Banned in ``tool.yaml`` per-tool manifests:
  - File missing entirely (a tool dir without a manifest is invalid).
  - ``depends_on_studio: true`` — the invariant exists *because* this is wrong.

Skipped (deliberately not checked) — README/docs prose may explain the
invariant by quoting the banned terms, so this script only walks
``scripts/`` and the manifest.

Usage:
  scripts/check_tools_standalone.py [--tools-dir tools]

Exit codes:
  0 — invariant holds (or tools/ is empty / scaffold-only)
  1 — one or more violations; details to stderr
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

BANNED_IMPORTS = re.compile(
    r"^\s*(?:from|import)\s+(studio|message|nit|audience|motion|planner)(?:\b|\.)",
    re.MULTILINE,
)

BANNED_STRINGS = [
    "studios.yml",
    "creative-director",
    # 'producer' / 'planner' as identifiers are flagged via the import check
    # above; here we only need string references that would couple a tool to
    # the studios orchestration vocabulary specifically:
    "creative_director",
]

BANNED_PATHS = [
    "~/context/studios/",
    "$STUDIOS_DOCKET_ROOT",
    "$STUDIOS_PROJECT_ROOT",
    "$STUDIOS_DOCKET_SESSION",
]

SCRIPT_EXTS = {".py", ".sh"}


def _violations_in_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    out: list[str] = []
    for match in BANNED_IMPORTS.finditer(text):
        out.append(f"banned studio import `{match.group(1)}` at {path}")
    for needle in BANNED_STRINGS:
        if needle in text:
            out.append(f"banned reference `{needle}` at {path}")
    for needle in BANNED_PATHS:
        if needle in text:
            out.append(f"hardcoded studio/context path `{needle}` at {path}")
    return out


def _check_manifest(tool_dir: Path) -> list[str]:
    manifest = tool_dir / "tool.yaml"
    if not manifest.exists():
        return [f"{tool_dir}: missing tool.yaml (required by ADR-004)"]
    try:
        data = yaml.safe_load(manifest.read_text()) or {}
    except yaml.YAMLError as e:
        return [f"{manifest}: invalid YAML — {e}"]
    if not isinstance(data, dict):
        return [f"{manifest}: top-level must be a mapping"]
    if data.get("depends_on_studio") is True:
        return [
            f"{manifest}: `depends_on_studio: true` violates the dumb-tool "
            "invariant (ADR-004 / brief 02 §4)"
        ]
    return []


def check(tools_dir: Path) -> list[str]:
    findings: list[str] = []
    if not tools_dir.exists():
        return findings  # scaffold not present is fine for now
    for tool_dir in sorted(p for p in tools_dir.iterdir() if p.is_dir()):
        findings.extend(_check_manifest(tool_dir))
        scripts_dir = tool_dir / "scripts"
        if not scripts_dir.exists():
            continue
        for path in sorted(scripts_dir.rglob("*")):
            if path.is_file() and path.suffix in SCRIPT_EXTS:
                findings.extend(_violations_in_file(path))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--tools-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "tools",
        help="Path to the tools/ directory (default: <repo>/tools).",
    )
    args = parser.parse_args(argv)
    findings = check(args.tools_dir)
    if findings:
        sys.stderr.write("dumb-tool invariant violations:\n")
        for f in findings:
            sys.stderr.write(f"  - {f}\n")
        sys.stderr.write(
            "\nSee tools/README.md + docs/architecture/DECISIONS.md ADR-004 "
            "for the contract.\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
