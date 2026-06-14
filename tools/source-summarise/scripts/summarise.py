#!/usr/bin/env python3
# Part of the nopilot-co-studios tool-bench (tools/source-summarise).
# Invoked by skills/source-summarise/SKILL.md via
# $CLAUDE_PLUGIN_ROOT/scripts/summarise.py. Also runnable standalone.
"""Summarise each source in an enriched notion-sources batch.

The mechanical I/O is implemented here (reads the manifest; writes a
`## Core summary` block + front-matter fields into each NNNN-*.md). The semantic
step — reading the enriched body + comments and producing the summary — is
delegated to the model via a JSON contract and fed back with --summary-json.
caller via a JSON contract (--summary-json). The dumb-tool contract per ADR-004.

Per source it captures:
  summary          neutral 2-4 sentence digest of the piece
  position         the overall stance / argument the author takes
  core_arguments   the key claims, as bullets
  comment_reaction assessment of the reaction in the comments section

--summary-json schema (keys are a source id, filename, or row number):
  { "<id|file|n>": { "summary": "...", "precis": "...", "position": "...",
                     "core_arguments": ["...", "..."], "comment_reaction": "..." } }

Usage:
  summarise.py --batch DIR [--only N|id|file ...] [--limit N]
               [--summary-json FILE] [--quiet]

Exit codes: 0 ok · 2 bad invocation (missing batch/manifest) · 3 error
"""

import argparse
import json
import os
import sys

SECTION = "## Core summary"


def load_yaml():
    try:
        import yaml

        return yaml
    except ImportError:
        sys.stderr.write(
            "error: PyYAML not installed — run install.sh or `pip install pyyaml`\n"
        )
        sys.exit(3)


def read_md(path):
    yaml = load_yaml()
    with open(path, "r", encoding="utf-8") as fh:
        t = fh.read()
    if t.startswith("---\n"):
        p = t.split("---\n", 2)
        if len(p) == 3:
            return yaml.safe_load(p[1]) or {}, p[2].lstrip("\n")
    return {}, t


def write_md(path, fm, body):
    yaml = load_yaml()
    front = yaml.safe_dump(
        fm, sort_keys=False, allow_unicode=True, default_flow_style=False, width=4096
    ).rstrip("\n")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("---\n" + front + "\n---\n\n" + body.strip() + "\n")


def apply_summary(path, s):
    fm, body = read_md(path)
    fm["summary"] = s.get("summary")
    fm["position"] = s.get("position")
    fm["core_arguments"] = s.get("core_arguments", [])
    fm["comment_reaction"] = s.get("comment_reaction")
    if s.get("precis") and not fm.get("precis"):
        fm["precis"] = s["precis"]
    fm["summarised"] = True
    # drop any prior Core summary section, then append a fresh one
    cut = body.find("\n" + SECTION)
    if cut != -1:
        body = body[:cut].rstrip()
    lines = [SECTION, "", s.get("summary") or "_TODO: summary_", ""]
    if s.get("position"):
        lines += [f"**Position:** {s['position']}", ""]
    if s.get("core_arguments"):
        lines += (
            ["**Core arguments:**", ""] + [f"- {a}" for a in s["core_arguments"]] + [""]
        )
    if s.get("comment_reaction"):
        lines += [f"**Comment reaction:** {s['comment_reaction']}", ""]
    write_md(path, fm, body.rstrip() + "\n\n" + "\n".join(lines))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Materialise caller-supplied summaries into an enriched batch."
    )
    ap.add_argument("--batch", required=True)
    ap.add_argument("--manifest", default="sources.json")
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument(
        "--summary-json",
        help="model-produced summaries (schema in the docstring/SKILL)",
    )
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    mpath = os.path.join(a.batch, a.manifest)
    if not os.path.isfile(mpath):
        sys.stderr.write(f"error: manifest not found: {mpath}\n")
        return 2
    with open(mpath, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    sel = set(map(str, a.only))

    def match(e):
        return (
            not sel
            or str(e.get("n")) in sel
            or e.get("id") in sel
            or os.path.splitext(e["file"])[0] in sel
            or e["file"] in sel
        )

    if not a.summary_json:
        print(
            "source-summarise: no --summary-json supplied (the caller must produce them)."
        )
        print(
            "Provide model-produced summaries via --summary-json. Schema (keys = id|file|n):"
        )
        print(
            '  {"<id|file|n>": {"summary","precis","position","core_arguments":[],"comment_reaction"}}'
        )
        print(f"Manifest has {len(manifest['sources'])} source(s) ready to summarise.")
        return 0

    with open(a.summary_json, "r", encoding="utf-8") as fh:
        smap = json.load(fh)

    n = 0
    for e in manifest["sources"]:
        if a.limit and n >= a.limit:
            break
        if not match(e):
            continue
        key = next(
            (k for k in (e.get("id"), e.get("file"), str(e.get("n"))) if k in smap),
            None,
        )
        if not key:
            continue
        apply_summary(os.path.join(a.batch, e["file"]), smap[key])
        e["summarised"] = True
        n += 1
        if not a.quiet:
            print(f"  ✓ summarised {e['file']}")

    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"\nsummarised {n} source(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
