#!/usr/bin/env python3
# Part of the nopilot-co-studios tool-bench (tools/theme-cluster).
# Invoked by skills/theme-cluster/SKILL.md via
# $CLAUDE_PLUGIN_ROOT/scripts/cluster.py. Also runnable standalone.
"""Group sources into themes — 'contributions to a consistent core discussion thread'.

The mechanical I/O is implemented: reads the manifest and, given a
model-produced assignment (--assignments), materialises a themes.json in the
batch (resolving each member to its manifest entry) and optionally tags each
source's front matter with its theme(s). The semantic step — deciding which
sources belong to the same discussion thread — is delegated to the model
(see SKILL.md). A future version may add a standalone embedding/keyword baseline.

--assignments schema (themes.json in; members are id | file | row number):
  { "themes": [ { "id": "agentic-gtm", "label": "Agentic GTM",
                  "description": "...", "members": ["<id|file|n>", ...] }, ... ] }

Usage:
  cluster.py --batch DIR [--assignments FILE] [--out themes.json]
             [--write-tags] [--quiet]

Exit codes: 0 ok · 2 bad invocation · 3 error
"""

import argparse
import json
import os
import sys


def load_yaml():
    try:
        import yaml

        return yaml
    except ImportError:
        sys.stderr.write(
            "error: PyYAML not installed — run install.sh or `pip install pyyaml`\n"
        )
        sys.exit(3)


def tag_source(path, labels):
    yaml = load_yaml()
    with open(path, "r", encoding="utf-8") as fh:
        t = fh.read()
    if not t.startswith("---\n"):
        return
    _, fm_text, body = t.split("---\n", 2)
    fm = yaml.safe_load(fm_text) or {}
    fm["themes"] = sorted(set(fm.get("themes", []) + labels))
    front = yaml.safe_dump(
        fm, sort_keys=False, allow_unicode=True, default_flow_style=False, width=4096
    ).rstrip("\n")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("---\n" + front + "\n---\n\n" + body.lstrip("\n").strip() + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Group sources into themes.")
    ap.add_argument("--batch", required=True)
    ap.add_argument("--manifest", default="sources.json")
    ap.add_argument(
        "--assignments", help="model-produced themes.json (schema in docstring/SKILL)"
    )
    ap.add_argument(
        "--out", default="themes.json", help="output filename within --batch"
    )
    ap.add_argument(
        "--write-tags",
        action="store_true",
        help="also write themes[] into each source front matter",
    )
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    mpath = os.path.join(a.batch, a.manifest)
    if not os.path.isfile(mpath):
        sys.stderr.write(f"error: manifest not found: {mpath}\n")
        return 2
    with open(mpath, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    by_key = {}
    for e in manifest["sources"]:
        for k in (e.get("id"), e.get("file"), str(e.get("n"))):
            if k:
                by_key[k] = e

    if not a.assignments:
        print(
            "theme-cluster: no --assignments supplied (the caller must produce them)."
        )
        print("Provide model-produced theme assignments via --assignments. Schema:")
        print(
            '  {"themes":[{"id","label","description","members":["<id|file|n>", ...]}]}'
        )
        print(f"Manifest has {len(manifest['sources'])} source(s) to group.")
        return 0

    with open(a.assignments, "r", encoding="utf-8") as fh:
        spec = json.load(fh)

    themes_out = []
    label_by_file = {}
    for th in spec.get("themes", []):
        members = []
        for m in th.get("members", []):
            e = by_key.get(str(m))
            if not e:
                if not a.quiet:
                    print(
                        f"  · unknown member '{m}' in theme '{th.get('id')}' — skipped"
                    )
                continue
            members.append(
                {
                    k: e.get(k)
                    for k in ("n", "id", "file", "title", "author", "url", "created")
                }
            )
            label_by_file.setdefault(e["file"], []).append(
                th.get("label") or th.get("id")
            )
        themes_out.append(
            {
                "id": th.get("id"),
                "label": th.get("label"),
                "description": th.get("description"),
                "source_count": len(members),
                "members": members,
            }
        )

    out_path = os.path.join(a.batch, a.out)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(
            {"themes": themes_out, "theme_count": len(themes_out)},
            fh,
            ensure_ascii=False,
            indent=2,
        )
        fh.write("\n")

    if a.write_tags:
        for fname, labels in label_by_file.items():
            tag_source(os.path.join(a.batch, fname), labels)

    print(f"\nwrote {len(themes_out)} theme(s) -> {out_path}")
    for t in themes_out:
        print(f"  · {t['id']}: {t['source_count']} source(s)")
    if a.write_tags:
        print(f"  tagged {len(label_by_file)} source file(s) with themes[]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
