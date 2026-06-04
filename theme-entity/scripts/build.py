#!/usr/bin/env python3
# Part of the nopilot-co-utilities Claude Code plugin (utilities:theme-entity).
# STUB — scaffolding only. Invoked by skills/theme-entity/SKILL.md via
# $CLAUDE_PLUGIN_ROOT/scripts/build.py. Also runnable standalone.
"""Build a theme entity document per theme — the thematic sourced evidence base.

STUB. The mechanical assembly is implemented: for each theme in themes.json it
renders themes/<slug>.md with backlinks to contributing sources, grouped by
author and by timeline, pulling metadata from the theme members. The semantic
fields (summary, precis, notable contributions, key disagreements, comment
reaction assessment) come from a model-produced --spec; without it those
sections render as TODO placeholders.

--spec schema (keys are theme ids):
  { "<theme id>": { "summary": "...", "precis": "...",
                    "notable": ["..."], "disagreements": ["..."],
                    "comment_assessment": "..." } }

Usage:
  build.py --batch DIR [--themes themes.json] [--spec spec.json]
           [--only THEME_ID ...] [--out themes] [--quiet]

Exit codes: 0 ok · 2 bad invocation (missing themes.json) · 3 error
"""
import argparse
import json
import os
import re
import sys


def load_yaml():
    try:
        import yaml
        return yaml
    except ImportError:
        sys.stderr.write("error: PyYAML not installed — run install.sh or `pip install pyyaml`\n")
        sys.exit(3)


def slugify(s):
    s = re.sub(r"[^A-Za-z0-9]+", "-", (s or "theme").lower()).strip("-")
    return s[:60] or "theme"


def _link(member, out_dir, batch_dir):
    # relative link from the theme doc (in out_dir) back to the source .md (in batch_dir)
    rel = os.path.relpath(os.path.join(batch_dir, member["file"]), out_dir)
    title = (member.get("title") or member["file"]).replace("|", "\\|")
    return f"[{title}]({rel})"


def render_theme(theme, spec, out_dir, batch_dir):
    yaml = load_yaml()
    members = theme.get("members", [])
    authors = sorted({(m.get("author") or "Unknown") for m in members})
    dates = sorted([m.get("created") for m in members if m.get("created")])
    fm = {
        "type": "theme",
        "id": theme.get("id"),
        "label": theme.get("label"),
        "description": theme.get("description"),
        "source_count": len(members),
        "authors": authors,
        "date_range": (f"{dates[0]} … {dates[-1]}" if dates else None),
    }
    s = (spec or {}).get(theme.get("id"), {})
    out = ["## Summary", "", s.get("summary") or "_TODO: thematic summary (model-supplied via --spec)_", ""]
    if s.get("precis"):
        out += [f"**Precis:** {s['precis']}", ""]
    out += ["## Notable contributions", ""]
    out += ([f"- {x}" for x in s["notable"]] if s.get("notable")
            else ["_TODO: notable contributions_"]) + [""]
    out += ["## Key disagreements", ""]
    out += ([f"- {x}" for x in s["disagreements"]] if s.get("disagreements")
            else ["_TODO: highlight key disagreement_"]) + [""]
    out += ["## Comment-reaction assessment", "",
            s.get("comment_assessment") or "_TODO: assess the reaction across comment sections_", ""]

    # mechanical: contributing sources grouped by author
    out += ["## Contributing sources — by author", ""]
    by_author = {}
    for m in members:
        by_author.setdefault(m.get("author") or "Unknown", []).append(m)
    for author in sorted(by_author):
        out.append(f"### {author}")
        for m in by_author[author]:
            when = f" ({m['created']})" if m.get("created") else ""
            out.append(f"- {_link(m, out_dir, batch_dir)}{when} — {m.get('url','')}")
        out.append("")

    # mechanical: timeline
    out += ["## Timeline", ""]
    timeline = sorted(members, key=lambda m: (m.get("created") or "9999"))
    for m in timeline:
        when = m.get("created") or "undated"
        out.append(f"- **{when}** — {_link(m, out_dir, batch_dir)} · {m.get('author') or 'Unknown'}")
    out.append("")

    front = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True,
                           default_flow_style=False, width=4096).rstrip("\n")
    body = f"# {theme.get('label') or theme.get('id')}\n\n" + "\n".join(out)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{slugify(theme.get('id') or theme.get('label'))}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("---\n" + front + "\n---\n\n" + body.strip() + "\n")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build theme entity docs (STUB).")
    ap.add_argument("--batch", required=True)
    ap.add_argument("--themes", default="themes.json", help="themes.json within --batch (from theme-cluster)")
    ap.add_argument("--spec", help="model-produced synthesis per theme (schema in docstring/SKILL)")
    ap.add_argument("--only", action="append", default=[], help="only these theme ids")
    ap.add_argument("--out", default="themes", help="output dir within --batch")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    tpath = os.path.join(a.batch, a.themes)
    if not os.path.isfile(tpath):
        sys.stderr.write(f"error: themes file not found: {tpath} (run theme-cluster first)\n")
        return 2
    with open(tpath, "r", encoding="utf-8") as fh:
        themes = json.load(fh).get("themes", [])
    spec = {}
    if a.spec:
        with open(a.spec, "r", encoding="utf-8") as fh:
            spec = json.load(fh)

    out_dir = os.path.join(a.batch, a.out)
    sel = set(a.only)
    written = []
    for th in themes:
        if sel and th.get("id") not in sel:
            continue
        p = render_theme(th, spec, out_dir, a.batch)
        written.append(p)
        if not a.quiet:
            print(f"  ✓ {os.path.relpath(p, a.batch)}  ({th.get('source_count', len(th.get('members', [])))} sources)")

    print(f"\nbuilt {len(written)} theme entity doc(s) -> {out_dir}/")
    if not a.spec:
        print("  note: STUB — semantic sections are TODO placeholders; pass --spec (model-produced) to fill them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
