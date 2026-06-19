"""Native Google Slides execution pipeline (ADR-006 — the gslide serialiser).

Dynamic pipeline: the *same* docket source + the resolved nopilot UDS tokens →
**native Google Slides** via the Slides REST API (``presentations.batchUpdate``).
Not a PPTX import and not an HTML proxy — real, editable native slides, faithful
to the studio source/data, styled from the UDS (crimson/graphite/yellow,
Newsreader/Inter/IBM Plex Mono — the Workspace mono fallback).

Three layers, so it runs with or without Google auth:
- ``slide_specs``  — docket → a deck of plain slide specs (the IR; reuses the
  uds_html docket parser, so HTML and Slides render from one source).
- ``build_requests`` / ``payload`` — IR → Slides API ``batchUpdate`` requests
  (the executable spec). ``payload`` is the **dry-run** — inspectable, no creds.
- ``execute`` — creates the presentation and applies the requests via
  ``google-api-python-client`` (lazy import). Needs OAuth creds with the
  ``presentations`` scope; the live deck is an account write (confirm first).

CLI:  python -m studio.gslide <manifest> [--out payload.json]              # dry-run (no creds)
      python -m studio.gslide --authorize --client-secret npt.json --token-out token.json  # one-time OAuth (personal @gmail)
      python -m studio.gslide --execute --account npt --payload deck.gslide.json            # push a pre-built payload
      python -m studio.gslide <manifest> --execute --account coh                            # build + push (configured)
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

from . import archetype_ir
from . import uds as uds_mod
from . import uds_html

# 16:9 page (Slides default): 10in × 5.625in, in EMU (1in = 914400).
PAGE_W, PAGE_H = 9_144_000, 5_143_500
MARGIN = 457_200  # 0.5in
PT = 12700  # 1pt in EMU

# Google Slides mono fallback (the UDS Workspace fallback for Geist Mono).
_GSLIDE_MONO = "IBM Plex Mono"


# ----------------------------------------------------------------- helpers
def _rgb(hex_color: str) -> dict[str, float]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}


def _palette(brand: str) -> dict[str, Any]:
    u = uds_mod.resolve_uds(brand)
    light = u["semantic"]["light"]
    fam = u["font"]["family"]
    display = (fam.get("display") or ["Newsreader"])[0]
    body = (fam.get("body") or ["Inter"])[0]
    mono_fam = (fam.get("mono") or ["Geist Mono"])[0]
    mono = _GSLIDE_MONO if "geist" in mono_fam.lower() else mono_fam  # Geist Mono → Workspace fallback; else the brand's own face
    return {
        "ink": light.get("text", "#1C2022"),
        "muted": light.get("text-muted", "#6E747A"),
        "primary": light.get("primary", "#C3094A"),
        "secondary": light.get("secondary", light.get("primary", "#C3094A")),  # warm accent on DARK tone; falls back to primary
        "active": light.get("active", "#FFC10E"),
        "on_active": light.get("on-active", "#1C2022"),
        "surface": light.get("surface", "#FFFFFF"),
        "paper": light.get("bg", "#F1F1F4"),
        "line": light.get("line", "#E5E5E5"),
        "on_primary": light.get("on-primary", "#FFFFFF"),
        "display": display, "body": body, "mono": mono,
        "eyebrow": light.get("eyebrow", light.get("primary", "#C3094A")),  # overline colour (Coherence: dark raspberry)
        "heading_weight": u["font"].get("weight", {}).get("heading"),       # e.g. 600 = semibold; None → bold boolean
        "dataviz": u.get("dataviz") or [light.get("primary", "#C3094A")],   # chart series ramp (crimson-led)
    }


# ----------------------------------------------------------------- IR (docket → slides)
def _clean(text: str) -> str:
    """Plain text for a slide: strip markdown emphasis, links, editorial markers."""
    t = re.sub(r"\[\[[^\]]+\]\]", "", text)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"\*(.+?)\*", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def _topic_body(content_dir: Path, topic: dict[str, Any]) -> tuple[list[str], str]:
    """A topic's body as marked slide lines (``§`` subhead · ``•`` bullet · ``❝`` hero quote ·
    ``‼`` callout · ``❞`` pull-quote). Pull-quotes are authored one statement per raw line under a
    ``Pullquotes`` heading (markdown would merge them into one paragraph), so pull them out by line."""
    try:
        md = uds_html._read_ref(content_dir, topic["section_md"])
    except OSError:
        return [], ""
    pulls: list[str] = []                                        # extract the Pullquotes block, raw, line by line
    keep: list[str] = []
    in_pq = False
    for ln in md.splitlines():
        s = ln.strip()
        if re.match(r"^#{2,4}\s+Pullquotes\s*$", s):
            in_pq = True; keep.append(ln); continue
        if in_pq:
            if re.match(r"^#{1,4}\s", s):
                in_pq = False; keep.append(ln)
            elif not s:
                continue
            elif " -- " in s or len(s) <= 130:                   # a punchy pull-quote line
                pulls.append(s)
            else:
                keep.append(ln)                                  # a long closing paragraph stays in the flow
        else:
            keep.append(ln)
    md = "\n".join(keep)
    lines: list[str] = []
    for b in uds_html._blocks(md):
        if b[0] == "h" and b[1] == 1:
            continue
        if b[0] == "h":
            htext = _clean(b[2]).replace("Detail: ", "")
            lines.append("§ " + htext)
            if htext.lower() == "pullquotes":                    # emit the pulled-out statements after the heading
                lines += ["❞ " + pq for pq in pulls]
        elif b[0] == "p":
            lines.append(_clean(b[1]))
        elif b[0] == "list":
            lines += ["• " + _clean(it) for it in b[1]]
        elif b[0] == "quote":
            q = _clean(b[1])
            if q.lstrip().startswith("!"):                       # `> ! …` → an insert / callout box
                lines.append("‼ " + q.lstrip("! ").strip())
            else:
                lines.append("❝ " + q)                            # plain `> …` → inline hero quote
    return [ln for ln in lines if ln], ""


# ----------------------------------------------------------------- IR (flat HTML-laced source → slides)
def _strip_html(md: str) -> str:
    """Flatten HTML-laced markdown: drop <style>/<script>/<svg>/comments, then strip tags.
    Block-level closes become paragraph breaks and remaining tags become a space, so adjacent
    fragments don't run together (``TedstoneStrategy`` / ``FirstA`` / ``MinoltaYou``)."""
    md = re.sub(r"<style\b[^>]*>.*?</style>", "", md, flags=re.S | re.I)
    md = re.sub(r"<script\b[^>]*>.*?</script>", "", md, flags=re.S | re.I)
    md = re.sub(r"<svg\b[\s\S]*?</svg>", "", md, flags=re.I)
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    md = re.sub(r"<br\s*/?>", "\n", md, flags=re.I)
    md = re.sub(r"</(?:p|div|h[1-6]|li|tr|section|article|header|figure)>", "\n\n", md, flags=re.I)
    return re.sub(r"<[^>]+>", " ", md)


def _split_anchor(heading: str) -> tuple[str, str]:
    """'Title {#anchor}' → ('Title', 'anchor')."""
    m = re.match(r"^(.*?)\s*\{#([^}]+)\}\s*$", heading)
    return (m.group(1).strip(), m.group(2)) if m else (heading.strip(), "")


def _flat_lines(blocks: list[tuple]) -> list[str]:
    """Body blocks → slide lines (sub-heads as '§', list items '•', tables/quotes flattened)."""
    lines: list[str] = []
    for b in blocks:
        if b[0] == "h":
            lines.append("§ " + _clean(_split_anchor(b[2])[0]))
        elif b[0] == "p":
            lines.append(_clean(b[1]))
        elif b[0] == "list":
            lines += ["• " + _clean(it) for it in b[1]]
        elif b[0] == "quote":
            lines.append("“" + _clean(b[1]) + "”")
    return [ln for ln in lines if ln]


# --- branded archetypes from the flat source: callout + table (native, not flattened) ---
def _div_block(body: str, open_start: int) -> tuple[str, int]:
    """Inner HTML of the <div> opening at open_start + the index past its matching </div>
    (depth-balanced, so nested divs inside a callout are handled)."""
    open_end = body.find(">", open_start) + 1
    depth = 1
    for m in re.finditer(r"<(/?)div\b", body[open_end:], re.I):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return body[open_end:open_end + m.start()], body.find(">", open_end + m.end()) + 1
    return body[open_end:], len(body)


def _parse_callout(inner: str) -> dict[str, str]:
    """A callout div's inner HTML → {heading, body}: first heading-ish element + the prose.
    Tags strip to a space so adjacent fragments don't run together (``direction``+``Getting``)."""
    head = re.search(r"<(?:div|h[1-6])[^>]*>(.*?)</(?:div|h[1-6])>", inner, re.S | re.I)
    heading = _clean(re.sub(r"<[^>]+>", " ", head.group(1))) if head else ""
    paras = re.findall(r"<p[^>]*>(.*?)</p>", inner, re.S | re.I)
    body = " ".join(_clean(re.sub(r"<[^>]+>", " ", p)) for p in paras)
    if not (heading or body):
        body = _clean(re.sub(r"<[^>]+>", " ", inner))
    return {"heading": heading, "body": body}


def _parse_html_table(html: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
        cells = [_clean(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S | re.I)]
        if any(cells):
            rows.append(cells)
    return rows


def _pipe_rows(rows: list[str]) -> list[list[str]]:
    """Markdown ``| a | b |`` rows → list-of-lists (the |---| separator dropped)."""
    out: list[list[str]] = []
    for r in rows:
        if re.match(r"^\s*\|?[\s:|-]+\|?\s*$", r):
            continue
        out.append([c.strip() for c in r.strip().strip("|").split("|")])
    return out


def _flat_blocks(body: str) -> list[tuple]:
    """Ordered blocks from HTML-laced markdown: markdown via uds_html._blocks, plus the
    native branded archetypes — ``<table>`` → ('table', rows) and a callout ``<div>`` →
    ('callout', {heading, body}). Markdown tables (``| … |``) are normalised to the same
    ('table', rows) shape. So both canonical and HTML-laced sources reach the serialiser
    as archetypes, not flattened text."""
    callout_open = re.compile(r'<div[^>]*class="[^"]*\bcallout\b[^"]*"[^>]*>', re.I)
    table_re = re.compile(r"<table\b[\s\S]*?</table>", re.I)
    out: list[tuple] = []
    i = 0
    while i <= len(body):
        c = callout_open.search(body, i)
        t = table_re.search(body, i)
        cands = [m.start() for m in (c, t) if m]
        nxt = min(cands) if cands else len(body)
        md = body[i:nxt]
        if md.strip():
            for b in uds_html._blocks(_strip_html(md)):
                if b[0] == "table":
                    out.append(("table", _pipe_rows(b[1])))
                elif b[0] == "fence" and b[1] in ("swimlane", "timeline", "diagram"):
                    try:
                        spec = yaml.safe_load(b[2]) or {}
                    except Exception:
                        spec = {}
                    if isinstance(spec, dict):
                        spec.setdefault("type", b[1])
                        out.append(("diagram", spec))
                elif b[0] == "fence" and b[1] in ("cards", "panel", "flow", "process", "chart", "stat-panel", "stats", "bullseye", "hype-cycle", "hype", "image", "figure", "asset-embed"):
                    try:
                        spec = yaml.safe_load(b[2])
                        kind = {"process": "flow", "stats": "stat-panel", "hype": "hype-cycle", "figure": "image", "asset-embed": "image"}.get(b[1], b[1])
                        out.append((kind, spec))
                    except Exception:
                        out.append(("p", _clean(b[2])))
                elif b[0] == "fence" and b[1] in ("pullquote", "cta"):
                    out.append((b[1], b[2]))   # free text — normalised at render
                else:
                    out.append(b)
        if not cands:
            break
        if c and c.start() == nxt:
            inner, end = _div_block(body, c.start())
            out.append(("callout", _parse_callout(inner)))
            i = end
        else:
            out.append(("table", _parse_html_table(t.group(0))))
            i = t.end()
    return out


def slide_specs_flat(src_path: Path, *, brand: str = "nopilot", lines_per_slide: int = 6, group_lead: int = 0, table_rows: int = 0) -> tuple[str, list[dict]]:
    """Flat HTML-laced markdown (front-matter + ``## {#anchor}`` sections) → the slide IR.
    The cover comes from front-matter; each H2 → a section divider; its lead-in prose
    and each H3 subsection → content slides (paginated). A ``{#hero}`` H2 is dropped
    (the cover already carries it)."""
    text = Path(src_path).read_text(encoding="utf-8")
    meta, body = uds_html.split_frontmatter(text)
    blocks = _flat_blocks(body)              # markdown + native callout/table archetypes, in order
    title = _clean(str(meta.get("title", "Document")))
    deck: list[dict] = [{"kind": "cover", "eyebrow": _clean(str(meta.get("eyebrow", "") or "Proposal")),
                         "title": title, "sub": "", "standfirst": _clean(str(meta.get("description", "")))}]
    groups: list[dict] = []
    cur: dict | None = None
    for b in blocks:
        if b[0] == "h" and b[1] == 2:
            htext, anchor = _split_anchor(b[2])
            cur = {"title": _clean(htext), "anchor": anchor, "blocks": []}
            groups.append(cur)
        elif cur is not None:
            cur["blocks"].append(b)
    for g in groups:
        if g["anchor"] == "hero":            # the cover already carries the hero
            continue
        deck.append({"kind": "section", "eyebrow": "Section", "title": g["title"]})
        gtitle = g["title"]
        pending: list[str] = []

        def _emit(lines: list[str], sub_title: str) -> None:
            chunks = [lines[i:i + lines_per_slide] for i in range(0, len(lines), lines_per_slide)]
            for nch, chunk in enumerate(chunks):
                deck.append({"kind": "content", "eyebrow": gtitle,
                             "title": sub_title + ("" if nch == 0 else f" (cont. {nch + 1})"), "body": chunk})

        sub_title = gtitle                   # lead-in prose under the H2, then each H3 subsection
        for b in g["blocks"]:
            if b[0] == "h" and b[1] == 3:
                _emit(pending, sub_title); pending = []
                sub_title = _clean(_split_anchor(b[2])[0])
            elif b[0] == "callout":          # branded callout → its own slide
                _emit(pending, sub_title); pending = []
                deck.append({"kind": "callout", "eyebrow": (b[1].get("heading") or gtitle),
                             "heading": b[1].get("heading", ""), "body": b[1].get("body", "")})
            elif b[0] == "table":            # data table → its own slide(s); long tables paginate (header repeats)
                head, lead = (pending[:-group_lead], pending[-group_lead:]) if group_lead else (pending, [])
                _emit(head, sub_title); pending = []
                rows = b[1] or []
                if rows:
                    header, bodyrows = rows[0], rows[1:]
                    cap = table_rows if table_rows else (len(bodyrows) or 1)
                    chunks = [bodyrows[k:k + cap] for k in range(0, len(bodyrows), cap)] or [[]]
                    for ci, chunk in enumerate(chunks):
                        deck.append({"kind": "table", "eyebrow": gtitle,
                                     "title": sub_title + ("" if ci == 0 else " (cont.)"),
                                     "rows": [header] + chunk, "lead": lead if ci == 0 else []})
                elif lead:
                    _emit(lead, sub_title)
            elif b[0] == "diagram":          # timeline / swimlane → its own slide, grouping the lead-in prose
                head, lead = (pending[:-group_lead], pending[-group_lead:]) if group_lead else (pending, [])
                _emit(head, sub_title); pending = []
                deck.append({"kind": "diagram", "eyebrow": gtitle, "title": sub_title, "spec": b[1], "lead": lead})
            elif b[0] == "cards":            # icon/feature card grid
                head, lead = (pending[:-group_lead], pending[-group_lead:]) if group_lead else (pending, [])
                _emit(head, sub_title); pending = []
                cards = b[1] if isinstance(b[1], list) else ((b[1] or {}).get("cards") or [])
                if cards:
                    deck.append({"kind": "cards", "eyebrow": gtitle, "title": sub_title, "cards": cards, "lead": lead})
                elif lead:
                    _emit(lead, sub_title)
            elif b[0] == "panel":            # feature panel (dark/light) + optional nested cards
                head, lead = (pending[:-group_lead], pending[-group_lead:]) if group_lead else (pending, [])
                _emit(head, sub_title); pending = []
                deck.append({"kind": "panel", "eyebrow": gtitle, "title": sub_title, "spec": b[1] or {}, "lead": lead})
            elif b[0] == "flow":             # process / flow → its own slide, every stage (wraps)
                head, lead = (pending[:-group_lead], pending[-group_lead:]) if group_lead else (pending, [])
                _emit(head, sub_title); pending = []
                steps = b[1] if isinstance(b[1], list) else ((b[1] or {}).get("steps") or [])
                if steps:
                    deck.append({"kind": "flow", "eyebrow": gtitle, "title": sub_title, "steps": steps, "lead": lead})
                elif lead:
                    _emit(lead, sub_title)
            elif b[0] == "chart":            # native chart → its own slide
                head, lead = (pending[:-group_lead], pending[-group_lead:]) if group_lead else (pending, [])
                _emit(head, sub_title); pending = []
                deck.append({"kind": "chart", "eyebrow": gtitle, "title": sub_title, "spec": b[1] or {}, "lead": lead})
            elif b[0] in ("stat-panel", "bullseye", "hype-cycle", "image"):  # viz / figure → its own slide
                head, lead = (pending[:-group_lead], pending[-group_lead:]) if group_lead else (pending, [])
                _emit(head, sub_title); pending = []
                deck.append({"kind": b[0], "eyebrow": gtitle, "title": sub_title, "spec": b[1], "lead": lead})
            elif b[0] == "pullquote":        # pull-quote band
                _emit(pending, sub_title); pending = []
                deck.append({"kind": "pullquote", "eyebrow": gtitle, "spec": b[1]})
            elif b[0] == "cta":              # call-to-action banner
                _emit(pending, sub_title); pending = []
                deck.append({"kind": "cta", "spec": b[1]})
            else:
                pending += _flat_lines([b])
        _emit(pending, sub_title)
    return title, deck


def slide_specs(manifest_path: Path, *, brand: str = "nopilot", lines_per_slide: int = 6, group_lead: int = 0, table_rows: int = 0, viz: dict[str, Any] | None = None) -> tuple[str, list[dict]]:
    """Docket manifest → an ordered deck of plain slide specs (the IR). A ``.md`` path
    is treated as a flat HTML-laced source (``slide_specs_flat``)."""
    manifest_path = Path(manifest_path)
    if manifest_path.suffix.lower() in (".md", ".markdown"):
        return slide_specs_flat(manifest_path, brand=brand, lines_per_slide=lines_per_slide, group_lead=group_lead, table_rows=table_rows)
    content_dir = manifest_path.parent.parent
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    meta = manifest.get("meta", {})
    topics = manifest.get("topics", [])
    viz = viz or {}

    def _listed(tp: dict) -> bool:                  # topics that appear in the contents index
        return tp.get("type", "content") == "content" and tp.get("id") not in ("cover", "intro") and bool(tp.get("section_md"))

    contents = [{"n": i + 1, "title": _clean(tp.get("title", "")), "desc": _clean(tp.get("eyebrow", "")), "anchor": tp.get("id")}
                for i, tp in enumerate([tp for tp in topics if _listed(tp)])]
    deck: list[dict] = []
    embeds: list[tuple[str, str]] = []
    for t in topics:
        tid = t.get("id")
        ttype = t.get("type", "content")
        tone = t.get("tone")                        # None when unset → build_requests applies a kind-aware default (sections dark)
        eyebrow, title = _clean(t.get("eyebrow", "")), _clean(t.get("title", ""))
        if ttype == "embed":                        # reference docket → Related-documents appendix, never embedded
            embeds.append((tid, title or tid))
            continue
        if ttype == "index":                        # the contents page, built from the listed topics
            deck.append({"kind": "contents", "tone": tone, "eyebrow": eyebrow or "Contents", "title": title or "Contents", "entries": contents})
            continue
        if tid == "cover":
            try:
                body = uds_html._read_ref(content_dir, t["section_md"]) if t.get("section_md") else ""
            except OSError:
                body = ""
            wm = uds_html._labelled(body, "Wordmark") or "360°"
            m = re.match(r"^(.*?°)\s*(.*)$", wm, re.DOTALL)
            wtitle, sub = (m.group(1), _clean(m.group(2))) if m else (wm, "")
            foot = _clean(uds_html._labelled(body, "Footer"))      # _clean flattens newlines → truncate at the draft cruft
            for _cut in ("Version 0.", "Confidential", "---"):
                foot = foot.split(_cut)[0].strip()
            deck.append({"kind": "cover", "tone": tone,
                         "eyebrow": uds_html._labelled(body, "Eyebrow") or eyebrow or "A partnership proposition",
                         "title": wtitle, "sub": sub or "Working title. The name comes later.",
                         "standfirst": _clean(uds_html._labelled(body, "Standfirst")) or "A business we can build together over three years, and hand on in good shape.",
                         "footer": foot})
            continue
        if ttype == "interstitial" or not t.get("section_md"):   # a part divider — full-bleed, tone-coloured
            deck.append({"kind": "section", "tone": tone, "eyebrow": eyebrow or "Section", "title": title})
            continue
        lines, _q = _topic_body(content_dir, t)                  # a content topic (hero quotes inline)
        deck.append({"kind": "content", "tone": tone, "eyebrow": eyebrow, "title": title,
                     "sections": _split_sections(lines)})        # build_requests flows sections into columns by measured height
        for tbl in (t.get("tables") or []):                      # the manifest's data tables (pricing ladder, financials, scoring)
            rows = _csv_table(content_dir, tbl)
            if rows:
                deck.append({"kind": "table", "tone": tone, "eyebrow": eyebrow,
                             "title": _clean(tbl.get("caption", "")) or title, "rows": rows, "lead": []})
        if tid in viz:                                           # native viz for this topic (chart/bullseye/swimlane/hype/image; one or many)
            blocks = viz[tid] if isinstance(viz[tid], list) else [viz[tid]]
            for v in blocks:
                deck.append({"kind": v["kind"], "tone": tone, "eyebrow": eyebrow,
                             "title": _clean(v.get("title", title)), "spec": v.get("spec", {}), "lead": v.get("lead", [])})
    if embeds:
        deck.append({"kind": "content", "tone": "dark", "eyebrow": "Appendix", "title": "Related documents",
                     "sections": _split_sections(["Maintained as separate standalone documents (linked, not embedded):"]
                             + [f"• **{label}** — docket: {tid}" for tid, label in embeds])})
    return str(meta.get("doc_title", "360 proposition")), deck


# ----------------------------------------------------------------- IR → Slides API requests
def _text_box(slide_id: str, box_id: str, x: int, y: int, w: int, h: int) -> dict:
    return {"createShape": {"objectId": box_id, "shapeType": "TEXT_BOX",
            "elementProperties": {"pageObjectId": slide_id,
                "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": h, "unit": "EMU"}},
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"}}}}


def _style(box_id: str, *, font: str, size: int, color: dict, bold: bool = False,
           align: str | None = None, weight: int | None = None,
           line_spacing: float | None = None, space_after: float | None = None) -> list[dict]:
    style: dict = {"fontSize": {"magnitude": size, "unit": "PT"},
                   "foregroundColor": {"opaqueColor": {"rgbColor": color}}}
    if weight:  # a true weighted face (e.g. Roboto Light 300) — "never bold"; beats the bold boolean
        style["weightedFontFamily"] = {"fontFamily": font, "weight": weight}
        fields = "fontSize,foregroundColor,weightedFontFamily"
    else:
        style.update({"fontFamily": font, "bold": bold})
        fields = "fontFamily,fontSize,foregroundColor,bold"
    reqs = [{"updateTextStyle": {"objectId": box_id, "textRange": {"type": "ALL"},
             "style": style, "fields": fields}}]
    pstyle: dict = {}
    pfields: list[str] = []
    if align:
        pstyle["alignment"] = align; pfields.append("alignment")
    if line_spacing:
        pstyle["lineSpacing"] = line_spacing; pfields.append("lineSpacing")  # percent (115 = 1.15)
    if space_after:
        pstyle["spaceBelow"] = {"magnitude": space_after, "unit": "PT"}; pfields.append("spaceBelow")
    if pstyle:
        reqs.append({"updateParagraphStyle": {"objectId": box_id, "textRange": {"type": "ALL"},
                     "style": pstyle, "fields": ",".join(pfields)}})
    return reqs


def _bg(slide_id: str, hex_color: str) -> dict:
    return {"updatePageProperties": {"objectId": slide_id,
            "pageProperties": {"pageBackgroundFill": {"solidFill": {"color": {"rgbColor": _rgb(hex_color)}}}},
            "fields": "pageBackgroundFill.solidFill.color"}}


def _mix(a: str, b: str, t: float) -> str:
    """Blend hex a→b by t (0..1). Used for the callout tint = primary washed into white."""
    ca, cb = _rgb(a), _rgb(b)
    return "#" + "".join(f"{round((ca[k] * (1 - t) + cb[k] * t) * 255):02X}" for k in ("red", "green", "blue"))


def _shape(slide_id: str, box_id: str, shape_type: str, x: int, y: int, w: int, h: int, fill_hex: str) -> list[dict]:
    """A filled shape (no outline) — the callout box (ROUND_RECTANGLE) + its accent edge (RECTANGLE)."""
    return [
        {"createShape": {"objectId": box_id, "shapeType": shape_type,
            "elementProperties": {"pageObjectId": slide_id,
                "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": h, "unit": "EMU"}},
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"}}}},
        {"updateShapeProperties": {"objectId": box_id,
            "shapeProperties": {"shapeBackgroundFill": {"solidFill": {"color": {"rgbColor": _rgb(fill_hex)}}},
                                "outline": {"propertyState": "NOT_RENDERED"}},
            "fields": "shapeBackgroundFill.solidFill.color,outline.propertyState"}},
    ]


def _table_reqs(slide_id: str, tid: str, rows: list[list[str]], x: int, y: int, w: int, p: dict, cell_size: int = 10) -> list[dict]:
    """A native Slides table — header row in the brand primary (uppercase), body in ink."""
    nrows = len(rows)
    ncols = max((len(r) for r in rows), default=1)
    out: list[dict] = [{"createTable": {"objectId": tid,
        "elementProperties": {"pageObjectId": slide_id,
            "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": min(3_000_000, 340_000 * nrows), "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"}},
        "rows": nrows, "columns": ncols}}]
    out.append({"updateTableCellProperties": {"objectId": tid,          # header row → brand grey fill
        "tableRange": {"location": {"rowIndex": 0, "columnIndex": 0}, "rowSpan": 1, "columnSpan": ncols},
        "tableCellProperties": {"tableCellBackgroundFill": {"solidFill": {"color": {"rgbColor": _rgb(p.get("paper", "#F1F1F4"))}}}},
        "fields": "tableCellBackgroundFill.solidFill.color"}})
    for r, row in enumerate(rows):
        for c in range(ncols):
            txt = row[c] if c < len(row) else ""
            if not txt:
                continue
            head = r == 0
            out.append({"insertText": {"objectId": tid, "cellLocation": {"rowIndex": r, "columnIndex": c}, "text": txt.upper() if head else txt, "insertionIndex": 0}})
            out.append({"updateTextStyle": {"objectId": tid, "cellLocation": {"rowIndex": r, "columnIndex": c},
                "textRange": {"type": "ALL"},
                "style": {"fontFamily": p["body"], "fontSize": {"magnitude": cell_size, "unit": "PT"},
                          "foregroundColor": {"opaqueColor": {"rgbColor": _rgb(p["primary"] if head else p["ink"])}}, "bold": head},
                "fields": "fontFamily,fontSize,foregroundColor,bold"}})
    return out


def _swimlane_reqs(slide_id: str, node, x: int, y: int, w: int, h: int, p: dict) -> list[dict]:
    """A native swimlane / timeline from a SwimlaneNode: a month axis, lane rows with span
    bars (primary tint), and milestone diamonds. All native shapes — editable, crisp,
    on-brand, no image upload."""
    months = node.months
    lanes = node.lanes
    milestones = node.milestones
    if not months or not lanes:
        return []
    label_w = 1_150_000
    track_x = x + label_w
    col_w = (w - label_w) / len(months)
    tint = _mix(p["primary"], "#FFFFFF", 0.86)

    def mx(name):
        return track_x + (months.index(name) if name in months else len(months)) * col_w

    out: list[dict] = []
    for i, m in enumerate(months):                       # month axis
        b = f"{slide_id}_mo{i}"
        out.append(_text_box(slide_id, b, int(track_x + i * col_w), int(y), int(col_w), 280_000))
        out.append({"insertText": {"objectId": b, "text": str(m), "insertionIndex": 0}})
        out += _style(b, font=p["body"], size=8, color=_rgb(p["muted"]), align="CENTER")
    top, lane_h = int(y + 340_000), 520_000
    for li, lane in enumerate(lanes):                    # lane rows + span bars
        ly = top + li * (lane_h + 36_000)
        ln = f"{slide_id}_ln{li}"
        out.append(_text_box(slide_id, ln, int(x), ly, int(label_w - 40_000), lane_h))
        out.append({"insertText": {"objectId": ln, "text": str(lane.name), "insertionIndex": 0}})
        out += _style(ln, font=p["body"], size=9, color=_rgb(p["ink"]), weight=600)
        if lane.stages:                                  # multi-stage roadmap: equal segments
            ns = len(lane.stages)
            seg_w = (w - label_w) / ns
            for si2, stg in enumerate(lane.stages):
                sxx = track_x + si2 * seg_w
                bw2 = int(seg_w - 60_000)
                bid = f"{slide_id}_bar{li}_{si2}"
                out += _shape(slide_id, f"{bid}r", "ROUND_RECTANGLE", int(sxx), ly, bw2, int(lane_h * 0.6), tint)
                out.append(_text_box(slide_id, f"{bid}t", int(sxx + 60_000), ly + 20_000, bw2 - 100_000, int(lane_h * 0.6)))
                out.append({"insertText": {"objectId": f"{bid}t", "text": str(stg.label), "insertionIndex": 0}})
                out += _style(f"{bid}t", font=p["body"], size=7, color=_rgb(p["ink"]))
        else:                                            # single span bar
            sx, ex = mx(lane.start), mx(lane.end)
            bw = max(int(ex - sx), 240_000)
            bar = f"{slide_id}_bar{li}"
            out += _shape(slide_id, f"{bar}r", "ROUND_RECTANGLE", int(sx), ly, bw, int(lane_h * 0.6), tint)
            out.append(_text_box(slide_id, f"{bar}t", int(sx + 70_000), ly + 24_000, bw - 120_000, int(lane_h * 0.6)))
            out.append({"insertText": {"objectId": f"{bar}t", "text": str(lane.label), "insertionIndex": 0}})
            out += _style(f"{bar}t", font=p["body"], size=8, color=_rgb(p["ink"]))
    my = top + len(lanes) * (lane_h + 36_000) + 30_000   # milestone diamonds
    for mi, ms in enumerate(milestones):
        dx = int(mx(ms.at) - 66_000)
        d = f"{slide_id}_ms{mi}"
        out += _shape(slide_id, f"{d}d", "DIAMOND", dx, my, 132_000, 132_000, p["primary"])
        out.append(_text_box(slide_id, f"{d}t", dx - 520_000, my + 150_000, 1_180_000, 280_000))
        out.append({"insertText": {"objectId": f"{d}t", "text": str(ms.label), "insertionIndex": 0}})
        out += _style(f"{d}t", font=p["body"], size=8, color=_rgb(p["primary"]), align="CENTER", weight=600)
    return out


def _card_grid_reqs(slide_id: str, cards: list, x: int, y: int, w: int, h: int, p: dict, *, dark: bool = False, idbase: str = "card") -> list[dict]:
    """Cards (eyebrow? + title + body), WRAPPING to balanced rows (≤3 wide) so every card
    shows. Light (grey, ink) or dark (on a panel)."""
    n = max(1, len(cards))
    rows = max(1, -(-n // 3))            # ceil(n/3) rows
    per_row = -(-n // rows)              # balanced across them
    gap = row_gap = 200_000
    cwc = (w - gap * (per_row - 1)) // per_row
    rh = min(int((h - (rows - 1) * row_gap) / rows), 2_400_000)
    fill = _mix(p["ink"], "#FFFFFF", 0.10) if dark else p["paper"]
    title_col = p["surface"] if dark else p["ink"]
    body_col = _mix(p["surface"], p["ink"], 0.40) if dark else p["muted"]
    eb_col = p["active"] if dark else p["primary"]
    out: list[dict] = []
    for i, c in enumerate(cards):
        r, cc = divmod(i, per_row)
        cx0, cy0 = x + cc * (cwc + gap), y + r * (rh + row_gap)
        cid = f"{slide_id}_{idbase}{i}"
        out += _shape(slide_id, f"{cid}r", "ROUND_RECTANGLE", cx0, cy0, cwc, rh, fill)
        pad, tw, ty = 220_000, cwc - 440_000, cy0 + 200_000
        if c.eyebrow:
            out.append(_text_box(slide_id, f"{cid}e", cx0 + pad, ty, tw, 230_000))
            out.append({"insertText": {"objectId": f"{cid}e", "text": str(c.eyebrow).upper(), "insertionIndex": 0}})
            out += _style(f"{cid}e", font=p["body"], size=8, color=_rgb(eb_col), weight=600)
            ty += 300_000
        out.append(_text_box(slide_id, f"{cid}t", cx0 + pad, ty, tw, 360_000))
        out.append({"insertText": {"objectId": f"{cid}t", "text": str(c.title), "insertionIndex": 0}})
        out += _style(f"{cid}t", font=p["body"], size=11, color=_rgb(title_col), weight=600)
        ty += 420_000
        out.append(_text_box(slide_id, f"{cid}b", cx0 + pad, ty, tw, max(cy0 + rh - ty - 150_000, 250_000)))
        out.append({"insertText": {"objectId": f"{cid}b", "text": str(c.body), "insertionIndex": 0}})
        out += _style(f"{cid}b", font=p["body"], size=8, color=_rgb(body_col))
    return out


def _panel_reqs(slide_id: str, spec: dict, x: int, y: int, w: int, h: int, p: dict) -> list[dict]:
    """A feature panel: a box (dark or light) with eyebrow + body + optional nested cards."""
    dark = bool(spec.get("dark"))
    out = _shape(slide_id, f"{slide_id}_pnl", "ROUND_RECTANGLE", x, y, w, h, p["ink"] if dark else p["paper"])
    pad = 340_000
    ix, iw, iy = x + pad, w - 2 * pad, y + 300_000
    eb_col = p["active"] if dark else p["primary"]
    body_col = _mix(p["surface"], p["ink"], 0.20) if dark else p["ink"]
    if spec.get("eyebrow"):
        out.append(_text_box(slide_id, f"{slide_id}_pe", ix, iy, iw, 250_000))
        out.append({"insertText": {"objectId": f"{slide_id}_pe", "text": str(spec["eyebrow"]).upper(), "insertionIndex": 0}})
        out += _style(f"{slide_id}_pe", font=p["body"], size=9, color=_rgb(eb_col), weight=600)
        iy += 350_000
    cards = archetype_ir.normalise_cards({"cards": spec.get("cards") or []}).cards
    body = str(spec.get("body", "")).strip()
    if body:
        bh = 1_350_000 if cards else max(h - (iy - y) - 300_000, 400_000)
        out.append(_text_box(slide_id, f"{slide_id}_pb", ix, iy, iw, bh))
        out.append({"insertText": {"objectId": f"{slide_id}_pb", "text": body, "insertionIndex": 0}})
        out += _style(f"{slide_id}_pb", font=p["body"], size=9, color=_rgb(body_col))
        iy += bh + 150_000
    if cards:
        out += _card_grid_reqs(slide_id, cards, ix, iy, iw, max(y + h - iy - pad, 800_000), p, dark=dark, idbase="pc")
    return out


def _flow_reqs(slide_id: str, node, x: int, y: int, w: int, h: int, p: dict) -> list[dict]:
    """A process/flow from a FlowNode: numbered step chips + arrows, WRAPPING to multiple
    rows so every stage shows (never truncated to fit one row)."""
    steps = node.steps
    n = len(steps)
    if not n:
        return []
    rows = max(1, -(-n // 4))            # ceil(n/4) rows…
    per_row = -(-n // rows)              # …balanced across them
    arrow_w, row_gap = 200_000, 280_000
    chip_w = (w - (per_row - 1) * arrow_w) // per_row
    row_h = min(int((h - (rows - 1) * row_gap) / rows), 1_300_000)   # hug content — don't float in a tall card
    out: list[dict] = []
    for i, st in enumerate(steps):
        r, c = divmod(i, per_row)
        cx0, cy0 = x + c * (chip_w + arrow_w), y + r * (row_h + row_gap)
        cid = f"{slide_id}_fs{i}"
        out += _shape(slide_id, f"{cid}c", "ROUND_RECTANGLE", cx0, cy0, chip_w, row_h, p["paper"])
        out += _shape(slide_id, f"{cid}n", "ROUND_RECTANGLE", cx0 + 150_000, cy0 + 150_000, 320_000, 320_000, p["primary"])
        out.append(_text_box(slide_id, f"{cid}ni", cx0 + 150_000, cy0 + 185_000, 320_000, 250_000))
        out.append({"insertText": {"objectId": f"{cid}ni", "text": str(i + 1), "insertionIndex": 0}})
        out += _style(f"{cid}ni", font=p["body"], size=11, color=_rgb(p["on_primary"]), align="CENTER", weight=600)
        tw = chip_w - 300_000
        out.append(_text_box(slide_id, f"{cid}t", cx0 + 150_000, cy0 + 500_000, tw, 250_000))   # title hugs the number (unit)
        out.append({"insertText": {"objectId": f"{cid}t", "text": str(st.title), "insertionIndex": 0}})
        out += _style(f"{cid}t", font=p["body"], size=10, color=_rgb(p["ink"]), weight=600)
        out.append(_text_box(slide_id, f"{cid}cap", cx0 + 150_000, cy0 + 820_000, tw, max(row_h - 950_000, 250_000)))   # clearer gap before the caption
        out.append({"insertText": {"objectId": f"{cid}cap", "text": str(st.caption), "insertionIndex": 0}})
        out += _style(f"{cid}cap", font=p["body"], size=8, color=_rgb(p["muted"]))
        if c < per_row - 1 and i < n - 1:   # arrow to the next chip in the row
            aid = f"{slide_id}_fa{i}"
            out.append(_text_box(slide_id, aid, cx0 + chip_w - 95_000, cy0 + row_h // 2 - 170_000, arrow_w, 340_000))   # optical centre: nudge ~10px left (→ glyph mass sits on the arrowhead)
            out.append({"insertText": {"objectId": aid, "text": "→", "insertionIndex": 0}})
            out += _style(aid, font=p["body"], size=14, color=_rgb(p["primary"]), align="CENTER")
    return out


def _chart_reqs(slide_id: str, node, x: int, y: int, w: int, h: int, p: dict) -> list[dict]:
    """A native bar chart from a ChartNode. Single series → labelled bars; multiple series
    → grouped bars (one dataviz colour per series) + a legend. Native shapes, every bar
    shown, coloured from the brand's dataviz tokens."""
    series = [s for s in node.series if s.values]
    if not series:
        return []
    cats = node.categories
    ncat = max(len(s.values) for s in series)
    nser = len(series)
    mx = max((v for s in series for v in s.values), default=1.0) or 1.0
    ramp = p.get("dataviz") or [p["primary"]]
    gap = 200_000
    legend_h = 360_000 if nser > 1 else 0
    group_w = (w - gap * (ncat - 1)) // max(ncat, 1)
    bar_gap = 24_000 if nser > 1 else 0
    bar_w = (group_w - bar_gap * (nser - 1)) // nser
    base_y = y + h - 560_000 - legend_h    # baseline; room for category labels (+ legend)
    maxbar = h - 900_000 - legend_h
    out: list[dict] = [{"createShape": {"objectId": f"{slide_id}_axis", "shapeType": "RECTANGLE",
        "elementProperties": {"pageObjectId": slide_id,
            "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": 12_000, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": base_y, "unit": "EMU"}}}},
        {"updateShapeProperties": {"objectId": f"{slide_id}_axis",
            "shapeProperties": {"shapeBackgroundFill": {"solidFill": {"color": {"rgbColor": _rgb(p["line"])}}}, "outline": {"propertyState": "NOT_RENDERED"}},
            "fields": "shapeBackgroundFill.solidFill.color,outline.propertyState"}}]
    for ci in range(ncat):
        gx = x + ci * (group_w + gap)
        for si, s in enumerate(series):
            val = s.values[ci] if ci < len(s.values) else 0.0
            bh = max(int(maxbar * val / mx), 20_000)
            bx, by = gx + si * (bar_w + bar_gap), base_y - bh
            out += _shape(slide_id, f"{slide_id}_bar{ci}_{si}", "ROUND_RECTANGLE", bx, by, bar_w, bh, ramp[(si if nser > 1 else ci) % len(ramp)])
            disp = s.displays[ci] if ci < len(s.displays) else str(int(val) if float(val).is_integer() else val)
            lw = bar_w + (160_000 if nser > 1 else 0)          # value label on EVERY bar — the numbers must be readable
            out.append(_text_box(slide_id, f"{slide_id}_bv{ci}_{si}", bx - (lw - bar_w) // 2, by - 250_000, lw, 230_000))
            out.append({"insertText": {"objectId": f"{slide_id}_bv{ci}_{si}", "text": str(disp), "insertionIndex": 0}})
            out += _style(f"{slide_id}_bv{ci}_{si}", font=p["body"], size=(9 if nser == 1 else 7), color=_rgb(p["ink"]), align="CENTER", weight=600)
        cat = cats[ci] if ci < len(cats) else ""
        out.append(_text_box(slide_id, f"{slide_id}_bc{ci}", gx, base_y + 40_000, group_w, 480_000))
        out.append({"insertText": {"objectId": f"{slide_id}_bc{ci}", "text": str(cat), "insertionIndex": 0}})
        out += _style(f"{slide_id}_bc{ci}", font=p["body"], size=8, color=_rgb(p["muted"]), align="CENTER")
    if nser > 1:                            # legend — swatch + series name
        ly, lx = y + h - legend_h + 60_000, x
        for si, s in enumerate(series):
            name = s.name or f"Series {si + 1}"
            out += _shape(slide_id, f"{slide_id}_lg{si}", "ROUND_RECTANGLE", lx, ly, 150_000, 150_000, ramp[si % len(ramp)])
            out.append(_text_box(slide_id, f"{slide_id}_lgt{si}", lx + 190_000, ly - 30_000, 2_400_000, 240_000))
            out.append({"insertText": {"objectId": f"{slide_id}_lgt{si}", "text": name, "insertionIndex": 0}})
            out += _style(f"{slide_id}_lgt{si}", font=p["body"], size=8, color=_rgb(p["ink"]))
            lx += 190_000 + len(name) * 88_000 + 360_000
    return out


def _stat_reqs(slide_id: str, node, x: int, y: int, w: int, h: int, p: dict) -> list[dict]:
    """A stat panel: a row of tiles (big value + label + optional delta). Native shapes."""
    stats = node.items
    n = len(stats)
    if not n:
        return []
    gap = 200_000
    tw = (w - gap * (n - 1)) // n
    th = min(h, 2_000_000)                                   # taller tiles so long labels do not overflow
    out: list[dict] = []
    for i, st in enumerate(stats):
        tx = x + i * (tw + gap)
        cid = f"{slide_id}_st{i}"
        out += _shape(slide_id, f"{cid}b", "ROUND_RECTANGLE", tx, y, tw, th, p["paper"])
        out.append(_text_box(slide_id, f"{cid}v", tx + 200_000, y + 200_000, tw - 400_000, 620_000))
        out.append({"insertText": {"objectId": f"{cid}v", "text": str(st.value), "insertionIndex": 0}})
        out += _style(f"{cid}v", font=p["display"], size=24, color=_rgb(p["primary"]), weight=600)
        out.append(_text_box(slide_id, f"{cid}l", tx + 200_000, y + 880_000, tw - 400_000, 1_000_000))
        out.append({"insertText": {"objectId": f"{cid}l", "text": str(st.label), "insertionIndex": 0}})
        out += _style(f"{cid}l", font=p["body"], size=9, color=_rgb(p["muted"]))
        if st.delta:
            out.append(_text_box(slide_id, f"{cid}d", tx + 200_000, y + th - 320_000, tw - 400_000, 250_000))
            out.append({"insertText": {"objectId": f"{cid}d", "text": str(st.delta), "insertionIndex": 0}})
            out += _style(f"{cid}d", font=p["body"], size=8, color=_rgb(p["primary"]), weight=600)
    return out


def _pullquote_reqs(slide_id: str, node, x: int, y: int, w: int, h: int, p: dict) -> list[dict]:
    """A pull-quote: large display quote + an em-dash attribution."""
    if node.is_empty:
        return []
    out: list[dict] = [_text_box(slide_id, f"{slide_id}_pq", x, y, w, max(h - 500_000, 700_000))]
    out.append({"insertText": {"objectId": f"{slide_id}_pq", "text": "“" + node.body + "”", "insertionIndex": 0}})
    out += _style(f"{slide_id}_pq", font=p["display"], size=20, color=_rgb(p["ink"]))
    if node.attribution:
        out.append(_text_box(slide_id, f"{slide_id}_pqa", x, y + max(h - 420_000, 750_000), w, 320_000))
        out.append({"insertText": {"objectId": f"{slide_id}_pqa", "text": "— " + node.attribution, "insertionIndex": 0}})
        out += _style(f"{slide_id}_pqa", font=p["body"], size=10, color=_rgb(p["primary"]), weight=600)
    return out


def _cta_reqs(slide_id: str, node, x: int, y: int, w: int, h: int, p: dict) -> list[dict]:
    """A call-to-action banner: tinted box + accent edge + text + a primary button."""
    if node.is_empty:
        return []
    bh = min(h, 1_150_000)
    out = _shape(slide_id, f"{slide_id}_cta", "ROUND_RECTANGLE", x, y, w, bh, _mix(p["primary"], "#FFFFFF", 0.90))
    out += _shape(slide_id, f"{slide_id}_ctae", "RECTANGLE", x, y, 46_000, bh, p["primary"])
    bw = 2_000_000
    out.append(_text_box(slide_id, f"{slide_id}_ctat", x + 340_000, y + 220_000, w - bw - 900_000, bh - 440_000))
    out.append({"insertText": {"objectId": f"{slide_id}_ctat", "text": str(node.text), "insertionIndex": 0}})
    out += _style(f"{slide_id}_ctat", font=p["body"], size=11, color=_rgb(p["ink"]), weight=600)
    by = y + (bh - 440_000) // 2
    out += _shape(slide_id, f"{slide_id}_ctab", "ROUND_RECTANGLE", x + w - bw - 340_000, by, bw, 440_000, p["primary"])
    out.append(_text_box(slide_id, f"{slide_id}_ctabt", x + w - bw - 340_000, by + 90_000, bw, 280_000))
    out.append({"insertText": {"objectId": f"{slide_id}_ctabt", "text": node.button or "Get in touch", "insertionIndex": 0}})
    out += _style(f"{slide_id}_ctabt", font=p["body"], size=10, color=_rgb(p["on_primary"]), align="CENTER", weight=600)
    return out


def _bullseye_reqs(slide_id: str, node, x: int, y: int, w: int, h: int, p: dict) -> list[dict]:
    """Concentric rings (native ELLIPSE shapes), outermost first so inner rings sit on top;
    each ring labelled at its mid-radius. rings[0] = the core (centre)."""
    rings = node.rings
    n = len(rings)
    if not n:
        return []
    R = min(w, h) // 2 - 120_000
    cx, cy = x + w // 2, y + h // 2
    ramp = p.get("dataviz") or [p["primary"]]
    out: list[dict] = []
    for j in range(n - 1, -1, -1):
        r = int(R * (j + 1) / n)
        out += _shape(slide_id, f"{slide_id}_be{j}", "ELLIPSE", cx - r, cy - r, 2 * r, 2 * r, ramp[j % len(ramp)])
    for j, ring in enumerate(rings):
        midr = int(R * (2 * j + 1) / (2 * n))
        txt = (ring.label + ": " if ring.label and ring.items else ring.label) + ", ".join(ring.items)
        lid = f"{slide_id}_bel{j}"
        out.append(_text_box(slide_id, lid, cx - R, cy - midr - 130_000, 2 * R, 280_000))
        out.append({"insertText": {"objectId": lid, "text": txt, "insertionIndex": 0}})
        out += _style(lid, font=p["body"], size=8, color=_rgb(p["on_primary"]), align="CENTER", weight=600)
    return out


def _hype_reqs(slide_id: str, node, x: int, y: int, w: int, h: int, p: dict) -> list[dict]:
    """A native hype-cycle: the S-curve as a row of small dots, plotted data points as
    labelled dots, a phase axis, and the tooltips surfaced as a visible note block (a
    non-interactive deck can't hover). Dynamic — driven entirely by the node's data."""
    pts = node.points
    if not pts:
        return []
    ramp = p.get("dataviz") or [p["primary"]]
    pad = 200_000
    plot_w = w - 2 * pad
    plot_h = h - 1_000_000        # room for the phase axis + the notes block

    def px(fx):
        return x + pad + int(fx * plot_w)

    def py(fy):
        return y + plot_h - int(fy * (plot_h - 200_000))

    out: list[dict] = []
    for k in range(41):                       # the curve, drawn as a dotted line
        fx = k / 40.0
        d = 56_000
        out += _shape(slide_id, f"{slide_id}_hc{k}", "ELLIPSE", px(fx) - d // 2, py(archetype_ir.hype_y(fx)) - d // 2, d, d, p["line"])
    for i, pt in enumerate(pts):              # plotted data points + labels
        cxp, cyp = px(pt.x), py(archetype_ir.hype_y(pt.x))
        out += _shape(slide_id, f"{slide_id}_hp{i}", "ELLIPSE", cxp - 90_000, cyp - 90_000, 180_000, 180_000, ramp[i % len(ramp)])
        out.append(_text_box(slide_id, f"{slide_id}_hl{i}", cxp - 1_000_000, cyp - 440_000, 2_000_000, 300_000))
        out.append({"insertText": {"objectId": f"{slide_id}_hl{i}", "text": str(pt.label), "insertionIndex": 0}})
        out += _style(f"{slide_id}_hl{i}", font=p["body"], size=8, color=_rgb(p["ink"]), align="CENTER", weight=600)
    nph = len(node.phases)                    # phase axis
    for i, ph in enumerate(node.phases):
        ax = px((i + 0.5) / nph) if nph else px(0.5)
        out.append(_text_box(slide_id, f"{slide_id}_hx{i}", ax - 1_000_000, y + plot_h + 40_000, 2_000_000, 260_000))
        out.append({"insertText": {"objectId": f"{slide_id}_hx{i}", "text": str(ph), "insertionIndex": 0}})
        out += _style(f"{slide_id}_hx{i}", font=p["body"], size=7, color=_rgb(p["muted"]), align="CENTER")
    ny = y + plot_h + 400_000                 # tooltips → a visible note block
    for i, pt in enumerate(pts):
        if not pt.tooltip:
            continue
        out.append(_text_box(slide_id, f"{slide_id}_hn{i}", x + pad, ny, w - 2 * pad, 240_000))
        out.append({"insertText": {"objectId": f"{slide_id}_hn{i}", "text": f"{pt.label} — {pt.tooltip}", "insertionIndex": 0}})
        out += _style(f"{slide_id}_hn{i}", font=p["body"], size=7, color=_rgb(p["muted"]))
        ny += 250_000
    return out


def _image_reqs(slide_id: str, node, x: int, y: int, w: int, h: int, p: dict) -> list[dict]:
    """A bespoke graphic. With a rasterised ``url`` → a real native image fit to the box; else a
    FIGURE card (accent edge + caption) referencing the SVG that lives in the high-fidelity doc."""
    if node.is_empty:
        return []
    if node.url:                              # rasterised figure → native image, proportional + centred
        a = node.aspect or 2.0
        iw, ih = w, w / a
        if ih > h:
            ih, iw = h, h * a
        ix, iy = x + (w - iw) // 2, y + (h - ih) // 2
        return [{"createImage": {"objectId": f"{slide_id}_img", "url": node.url,
                 "elementProperties": {"pageObjectId": slide_id,
                     "size": {"width": {"magnitude": int(iw), "unit": "EMU"}, "height": {"magnitude": int(ih), "unit": "EMU"}},
                     "transform": {"scaleX": 1, "scaleY": 1, "translateX": int(ix), "translateY": int(iy), "unit": "EMU"}}}}]
    bh = min(h, 2_800_000)
    out = _shape(slide_id, f"{slide_id}_fig", "ROUND_RECTANGLE", x, y, w, bh, p["paper"])
    out += _shape(slide_id, f"{slide_id}_fige2", "RECTANGLE", x, y, 46_000, bh, p["primary"])
    out.append(_text_box(slide_id, f"{slide_id}_fige", x + 340_000, y + 260_000, w - 680_000, 280_000))
    out.append({"insertText": {"objectId": f"{slide_id}_fige", "text": "FIGURE", "insertionIndex": 0}})
    out += _style(f"{slide_id}_fige", font=p["body"], size=8, color=_rgb(p["primary"]), weight=600)
    cap = node.caption or node.alt or node.src
    out.append(_text_box(slide_id, f"{slide_id}_figc", x + 340_000, y + 620_000, w - 680_000, bh - 920_000))
    out.append({"insertText": {"objectId": f"{slide_id}_figc", "text": str(cap), "insertionIndex": 0}})
    out += _style(f"{slide_id}_figc", font=p["display"], size=14, color=_rgb(p["ink"]))
    return out


def _md_bold_spans(s: str) -> tuple[str, list[tuple[int, int]]]:
    """Strip ``**bold**`` markers, returning the clean text + the bold char ranges.
    Leftover (unpaired) ``**`` markers — stray footnote/verification marks in the source —
    are removed, with the bold ranges shifted to stay correct."""
    out, spans = "", []
    for part in re.split(r"(\*\*.+?\*\*)", s):
        if len(part) >= 4 and part.startswith("**") and part.endswith("**"):
            t = part[2:-2]
            spans.append((len(out), len(out) + len(t)))
            out += t
        else:
            out += part
    while "**" in out:                                   # drop unpaired markers, keep spans correct
        i = out.index("**")
        out = out[:i] + out[i + 2:]
        spans = [(a - 2 if a > i else a, b - 2 if b > i else b) for a, b in spans]
    return out, spans


def _rich_text_box(sid: str, box_id: str, lines: list[str], x: int, y: int, w: int, h: int,
                   *, font: str, size: float, color: str, acc: str, serif: str,
                   weight: int | None = None, line_spacing: float | None = None, space_after: float | None = None,
                   subhead_size: float | None = None) -> list[dict]:
    """A reading column with structure: ``§`` → larger reading-font subhead (major point),
    ``❝`` → inline serif hero quote, ``• `` → native bullet, ``**lead**`` → bold run. One text box;
    styling applied by char range so prose wraps. ``weight`` sets a true face (e.g. Roboto Light 300)."""
    paras = []  # (clean, kind, bold_spans)
    for ln in lines:
        if ln.startswith("§ "):
            clean, spans = _md_bold_spans(ln[2:]); paras.append((clean, "head", spans))
        elif ln.startswith("❝ "):
            clean, spans = _md_bold_spans(ln[2:]); paras.append((clean, "quote", spans))
        elif ln.startswith("❞ "):
            clean, spans = _md_bold_spans(ln[2:].replace(" -- ", " — ")); paras.append((clean, "pullq", spans))
        elif ln.startswith("• "):
            clean, spans = _md_bold_spans(ln[2:]); paras.append((clean, "bullet", spans))
        else:
            clean, spans = _md_bold_spans(ln); paras.append((clean, "para", spans))
    text = "\n".join(p[0] for p in paras)
    if not text:
        return []
    if weight:
        base_style = {"weightedFontFamily": {"fontFamily": font, "weight": weight},
                      "fontSize": {"magnitude": size, "unit": "PT"}, "foregroundColor": {"opaqueColor": {"rgbColor": _rgb(color)}}}
        base_fields = "weightedFontFamily,fontSize,foregroundColor"
    else:
        base_style = {"fontFamily": font, "fontSize": {"magnitude": size, "unit": "PT"},
                      "foregroundColor": {"opaqueColor": {"rgbColor": _rgb(color)}}, "bold": False}
        base_fields = "fontFamily,fontSize,foregroundColor,bold"
    reqs: list[dict] = [_text_box(sid, box_id, x, y, w, h),
                        {"insertText": {"objectId": box_id, "text": text, "insertionIndex": 0}},
                        {"updateTextStyle": {"objectId": box_id, "textRange": {"type": "ALL"}, "style": base_style, "fields": base_fields}}]
    if line_spacing or space_after:
        ps: dict = {}; pf: list[str] = []
        if line_spacing: ps["lineSpacing"] = line_spacing; pf.append("lineSpacing")
        if space_after: ps["spaceBelow"] = {"magnitude": space_after, "unit": "PT"}; pf.append("spaceBelow")
        reqs.append({"updateParagraphStyle": {"objectId": box_id, "textRange": {"type": "ALL"}, "style": ps, "fields": ",".join(pf)}})

    def _rng(a: int, b: int, style: dict, fields: str) -> None:
        reqs.append({"updateTextStyle": {"objectId": box_id,
                     "textRange": {"type": "FIXED_RANGE", "startIndex": a, "endIndex": b},
                     "style": style, "fields": fields}})

    off, runs, run = 0, [], None
    for clean, kind, spans in paras:
        start, end = off, off + len(clean)
        for bs, be in spans:                       # bold lead-ins / emphasis
            if be > bs:
                _rng(start + bs, start + be, {"bold": True}, "bold")
        if kind == "head" and end > start:         # major-point subhead → larger + accent colour (matches the reference)
            _rng(start, end, {"fontSize": {"magnitude": (subhead_size or size + 2.5), "unit": "PT"},
                              "foregroundColor": {"opaqueColor": {"rgbColor": _rgb(acc)}}}, "fontSize,foregroundColor")
        elif kind == "quote" and end > start:      # inline hero quote → IBM Plex Serif, larger
            _rng(start, end, {"fontFamily": serif, "fontSize": {"magnitude": (subhead_size or size) + 4.5, "unit": "PT"},
                              "foregroundColor": {"opaqueColor": {"rgbColor": _rgb(color)}}},
                 "fontFamily,fontSize,foregroundColor")
        elif kind == "pullq" and end > start:      # pull-quote statement → IBM Plex Serif, slightly larger
            _rng(start, end, {"fontFamily": serif, "fontSize": {"magnitude": size + 3, "unit": "PT"}}, "fontFamily,fontSize")
        if kind == "bullet":
            run = [start, end] if run is None else [run[0], end]
        elif run is not None:
            runs.append(run); run = None
        off = end + 1
    if run is not None:
        runs.append(run)
    for a, b in runs:
        reqs.append({"createParagraphBullets": {"objectId": box_id,
                     "textRange": {"type": "FIXED_RANGE", "startIndex": a, "endIndex": b},
                     "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"}})
    return reqs


def _csv_table(content_dir: Path, spec: dict, *, max_cols: int = 6) -> list[list[str]]:
    """Read a docket table CSV → rows for a native slide table, dropping noise columns
    (modelled / note / source / fee_basis / role_in_path) and prettifying headers."""
    import csv as _csv
    p = content_dir / str(spec.get("csv", ""))
    try:
        rows = [r for r in _csv.reader(p.open(encoding="utf-8")) if any(c.strip() for c in r)]
    except OSError:
        return []
    if not rows:
        return []
    drop = {"modelled", "note", "notes", "source", "confidence", "fee_basis", "role_in_path"}
    keep = [i for i, h in enumerate(rows[0]) if h.strip().lower() not in drop][:max_cols]
    pretty = lambda h: h.replace("price_", "").replace("_", " ").strip().title()
    return [[pretty(rows[0][i]) for i in keep]] + [[(r[i] if i < len(r) else "") for i in keep] for r in rows[1:]]


# ----------------------------------------------------------------- content flow (sections → columns)
def _is_stepped(sections: list[dict]) -> bool:
    """A numbered-step sequence (``§ 1. …`` / ``§ 2. …``) → render one step per slide."""
    return sum(1 for s in sections if s.get("type") == "prose" and s["lines"]
               and re.match(r"§ \d+[.)]\s", s["lines"][0])) >= 3


def _split_sections(lines: list[str]) -> list[dict]:
    """Group body lines into whole sections — a ``§`` subhead + its prose/bullets, a ``❝`` hero
    quote, or a ``‼`` insert/callout — so a section is never split across a column boundary."""
    sections: list[dict] = []
    cur: dict | None = None
    for ln in lines:
        if ln.startswith("❝ "):
            if cur:
                sections.append(cur); cur = None
            sections.append({"type": "quote", "lines": [ln]})
        elif ln.startswith("❞ "):
            if cur and cur["type"] == "pullquotes":
                cur["lines"].append(ln)
            else:
                if cur:
                    sections.append(cur)
                cur = {"type": "pullquotes", "lines": [ln]}
        elif ln.startswith("‼ "):
            if cur and cur["type"] == "callout":
                cur["lines"].append(ln)
            else:
                if cur:
                    sections.append(cur)
                cur = {"type": "callout", "lines": [ln]}
        elif ln.startswith("§ "):
            if cur:
                sections.append(cur)
            cur = {"type": "prose", "lines": [ln]}
        else:
            if cur and cur["type"] == "prose":
                cur["lines"].append(ln)
            else:
                if cur:
                    sections.append(cur)
                cur = {"type": "prose", "lines": [ln]}
    if cur:
        sections.append(cur)
    return sections


def _est_lines(text: str, sz: float, colw_emu: int) -> int:
    cpl = max(8, int((colw_emu / 914400.0) * 142.0 / max(sz, 1)))    # ~chars per line at this size + width
    return max(1, -(-len(text) // cpl))


def _section_h(section: dict, colw: int, body_sz: float, sub_sz: float) -> float:
    """Estimated rendered height (pt) of a section, for the column-flow + overflow guard."""
    h = 0.0
    for ln in section["lines"]:
        if ln.startswith("§ "):
            h += _est_lines(ln[2:], sub_sz, colw) * sub_sz * 1.2 + 7
        elif ln.startswith("❝ "):
            qz = sub_sz + 4.5                                     # must match the render size (subhead+4.5)
            h += _est_lines(ln[2:], qz, colw) * qz * 1.3 + 12
        elif ln.startswith("❞ "):
            pz = body_sz + 3
            h += _est_lines(ln[2:], pz, colw) * pz * 1.25 + 8
        elif ln.startswith("‼ ") or ln.startswith("• "):
            h += _est_lines(ln[2:], body_sz, colw) * body_sz * 1.15 + 6
        else:
            h += _est_lines(ln, body_sz, colw) * body_sz * 1.15 + 6
    if section["type"] == "callout":
        h += 26
    return h


def _flow_sections(sections: list[dict], colw: int, col_h_pt: float, body_sz: float, sub_sz: float) -> list[tuple[list, list]]:
    """Flow whole sections into (col1, col2) per slide: fill column 1 to the bottom margin, then
    column 2, then a new slide. A section is never split; overflow goes to the next column/slide."""
    pages: list[tuple[list, list]] = []
    cols: list[list] = [[], []]
    hs = [0.0, 0.0]
    ci = 0
    for sec in sections:
        sh = _section_h(sec, colw, body_sz, sub_sz)
        if hs[ci] > 0 and hs[ci] + sh > col_h_pt:      # current column full → next column
            ci += 1
            if ci > 1:                                  # both columns full → new slide
                pages.append((cols[0], cols[1])); cols = [[], []]; hs = [0.0, 0.0]; ci = 0
        cols[ci].append(sec); hs[ci] += sh
    if cols[0] or cols[1]:
        pages.append((cols[0], cols[1]))
    return pages or [([], [])]


def _callout_box(sid: str, bid: str, x: int, y: int, w: int, h: int, lines: list[str], *,
                 acc: str, bgc: str, txt: str, sans: str, weight: int | None) -> list[dict]:
    """An inset / callout box: tinted fill + accent left edge + the items inside (reading font)."""
    out = _shape(sid, f"{bid}_bx", "ROUND_RECTANGLE", x, y, w, h, _mix(acc, bgc, 0.86))
    out += _shape(sid, f"{bid}_eg", "RECTANGLE", x, y, 42_000, h, acc)
    pad = 200_000
    body = [ln[2:] if ln.startswith("‼ ") else ln for ln in lines]
    out += _rich_text_box(sid, f"{bid}_tx", body, x + pad + 40_000, y + pad // 2, w - 2 * pad - 40_000, h - pad,
                          font=sans, size=8, color=txt, acc=acc, serif=sans, weight=weight, line_spacing=115, space_after=4)
    return out


def _contents_reqs(sid: str, entries: list[dict], x: int, y: int, w: int, h: int,
                   *, acc: str, txt: str, mut: str, sans: str) -> list[dict]:
    """Numbered contents in two columns — all in the reading sans (Roboto): accent number +
    reading-font title + muted descriptor. (Only page titles keep the serif.)"""
    if not entries:
        return []
    out: list[dict] = []
    gutter = 520_000
    colw = (w - gutter) // 2
    per_col = (len(entries) + 1) // 2
    row_h = min(430_000, h // max(per_col, 1))
    for i, e in enumerate(entries):
        col = 0 if i < per_col else 1
        row = i - (0 if col == 0 else per_col)
        ex, ey = x + col * (colw + gutter), y + row * row_h
        nb, tb = f"{sid}_cn{i}", f"{sid}_ct{i}"
        out.append(_text_box(sid, nb, ex, ey, 520_000, row_h))
        out.append({"insertText": {"objectId": nb, "text": f"{e['n']:02d}", "insertionIndex": 0}})
        out += _style(nb, font=sans, size=10, color=_rgb(acc), weight=500)
        title, desc = e.get("title", ""), e.get("desc", "")
        text = title + (("\n" + desc) if desc else "")
        out.append(_text_box(sid, tb, ex + 560_000, ey, colw - 560_000, row_h))
        out.append({"insertText": {"objectId": tb, "text": text, "insertionIndex": 0}})
        out.append({"updateTextStyle": {"objectId": tb, "textRange": {"type": "ALL"},
                    "style": {"weightedFontFamily": {"fontFamily": sans, "weight": 300}, "fontSize": {"magnitude": 12, "unit": "PT"},
                              "foregroundColor": {"opaqueColor": {"rgbColor": _rgb(txt)}}},
                    "fields": "weightedFontFamily,fontSize,foregroundColor"}})
        if desc:
            ds = len(title) + 1
            out.append({"updateTextStyle": {"objectId": tb,
                        "textRange": {"type": "FIXED_RANGE", "startIndex": ds, "endIndex": ds + len(desc)},
                        "style": {"weightedFontFamily": {"fontFamily": sans, "weight": 400}, "fontSize": {"magnitude": 8.5, "unit": "PT"},
                                  "foregroundColor": {"opaqueColor": {"rgbColor": _rgb(mut)}}},
                        "fields": "weightedFontFamily,fontSize,foregroundColor"}})
    return out


def build_requests(manifest_path: Path, *, brand: str = "nopilot", profile: str | None = None, viz: dict[str, Any] | None = None) -> tuple[str, list[dict]]:
    """IR → Slides API batchUpdate requests (cover, contents, section, quote, content). A render
    ``profile`` (e.g. 'proposal') sets the reading sizes + column count from the UDS. ``viz`` maps
    a topic id → a native archetype block ({kind, spec, title}) appended after that topic's prose."""
    prof = uds_mod.profile_spec(profile)
    columns = int(prof.get("columns", 1))
    tsize = int(prof.get("table_size") or 9)
    title, deck = slide_specs(manifest_path, brand=brand, lines_per_slide=int(prof.get("lines_per_slide", 6)), group_lead=int(prof.get("group_lead", 0)), table_rows=int(prof.get("table_rows", 0)), viz=viz)
    p = _palette(brand)
    reqs: list[dict] = []
    cx, cw = MARGIN, PAGE_W - 2 * MARGIN

    def add_text(slide_id: str, n: int, text: str, y: int, h: int, *, font, size, color, bold=False, align=None, weight=None, x=None, w=None, line_spacing=None, space_after=None) -> None:
        box = f"{slide_id}_t{n}"
        reqs.append(_text_box(slide_id, box, cx if x is None else x, y, cw if w is None else w, h))
        reqs.append({"insertText": {"objectId": box, "text": text, "insertionIndex": 0}})
        reqs.extend(_style(box, font=font, size=size, color=color, bold=bold, align=align, weight=weight, line_spacing=line_spacing, space_after=space_after))

    R = uds_mod.render_contract(brand, "slide", profile=prof)   # role → resolved {family,size,weight,transform,align,colour}
    _AL = {"center": "CENTER", "right": "END", "justify": "JUSTIFIED"}  # left == default → no paragraph request
    bodysize = float((R.get("body") or {}).get("size", 11))     # reading size for rich body columns
    BASEY = {"table": 1_550_000, "diagram": 1_950_000, "chart": 1_950_000}  # data-heavy slides → tighter header
    # Format typography (proposal longform): Roboto Light reading body, IBM Plex Serif Bold titles, 1.15 line + space-after.
    typo = prof.get("typography", {}) or {}
    eyebrow_family, eyebrow_weight = typo.get("eyebrow_family"), typo.get("eyebrow_weight")
    body_family, body_weight = typo.get("body_family"), typo.get("body_weight")
    subhead_size = typo.get("subhead_size")
    title_family, title_weight = typo.get("title_family"), typo.get("title_weight")
    line_sp = round(float(typo["line_height"]) * 100) if typo.get("line_height") else None
    space_aft = typo.get("space_after_pt")
    _TITLE_ROLES = {"cover-title", "section-title", "topic-title", "quote"}
    if body_family:
        p = {**p, "body": body_family}    # the format reading face reaches every component (tables, charts, stat tiles, labels) — no brand-body leakage

    def add_role(slide_id: str, n: int, text: str, y: int, h: int, role: str, *, colour=None, align=None, x=None, w=None) -> None:
        st = R.get(role) or {}
        s = text.upper() if st.get("transform") == "upper" else text
        fam = (st.get("family") or "Inter").split(",")[0].strip()
        wt = st.get("weight")
        if role in _TITLE_ROLES and title_family:            # format titles → IBM Plex Serif (only titles keep the serif)
            fam, wt = title_family, (title_weight or wt)
        elif role.startswith("eyebrow") and eyebrow_family:  # format eyebrows → Roboto Medium caps
            fam, wt = eyebrow_family, (eyebrow_weight or wt)
        elif role == "body" and body_family:                 # format reading body → Roboto Light
            fam, wt = body_family, (body_weight or wt)
        if "geist" in fam.lower():            # Google Workspace has no Geist Mono → the UDS fallback
            fam = _GSLIDE_MONO
        add_text(slide_id, n, s, y, h, font=fam, size=round(st.get("size", 12)),
                 color=_rgb(colour or st.get("colour", "#1C2022")),
                 align=align or _AL.get(st.get("align")), bold=(wt is None), weight=wt, x=x, w=w,
                 line_spacing=(line_sp if role == "body" else None), space_after=(space_aft if role == "body" else None))

    def _lead_band(sid: str, lead, base_y: int, *, colour=None) -> int:
        """Grouped supporting prose (two columns) above a table/diagram; returns the y to start the data at."""
        if not lead:
            return base_y
        lh, gutter = 1_000_000, 360_000
        colw = (cw - gutter) // 2
        mid = (len(lead) + 1) // 2
        add_role(sid, 8, "\n\n".join(lead[:mid]), base_y, lh, "body", colour=colour, x=MARGIN, w=colw)
        if lead[mid:]:
            add_role(sid, 9, "\n\n".join(lead[mid:]), base_y, lh, "body", colour=colour, x=MARGIN + colw + gutter, w=colw)
        return base_y + lh + 200_000

    # Column-flow: expand each content topic into per-slide (col1, col2) by measured section height,
    # keeping every section whole and reserving a bottom margin so nothing overflows the canvas.
    CONTENT_TOP, BOTTOM_MARGIN, GUTTER = 1_700_000, 520_000, 360_000
    _colw = (cw - GUTTER) // 2
    _col_h_pt = (PAGE_H - CONTENT_TOP - MARGIN - BOTTOM_MARGIN) / PT
    _sub = subhead_size or 12
    _flowed: list[dict] = []
    for s in deck:
        if s.get("kind") == "content" and "sections" in s:
            _base = {k: s[k] for k in ("kind", "tone", "eyebrow", "title")}
            secs = s["sections"]
            groups = [[sec] for sec in secs] if _is_stepped(secs) else [secs]   # stepped sequence → one step per slide
            for grp in groups:
                for c1, c2 in _flow_sections(grp, _colw, _col_h_pt, bodysize, _sub):
                    _flowed.append({**_base, "col1": c1, "col2": c2})
        else:
            _flowed.append(s)
    deck = _flowed

    for i, s in enumerate(deck):
        sid = f"slide{i:03d}"  # Slides object IDs must be >= 5 chars
        reqs.append({"createSlide": {"objectId": sid, "insertionIndex": i,
                     "slideLayoutReference": {"predefinedLayout": "BLANK"}}})
        kind = s["kind"]
        tone = s.get("tone") or ("dark" if kind == "section" else "light")  # tone-less decks keep dark dividers
        dark = tone == "dark"
        bgc = p["ink"] if dark else (p["surface"] if kind == "cover" else p["paper"])  # cover=white; light ground=paper; dark=ink
        txt = p["paper"] if dark else p["ink"]                  # heading/body ink↔paper
        mut = _mix(p["paper"], p["ink"], 0.42) if dark else p["muted"]
        acc = p["secondary"] if dark else p["primary"]          # eyebrow + accent colour-split (indigo light / terracotta dark)
        pv = {**p, "ink": txt, "muted": mut}                    # tone-adjusted palette for native viz text
        reqs.append(_bg(sid, bgc))
        if kind == "cover":
            add_role(sid, 0, s["eyebrow"], 1_350_000, 360_000, "eyebrow", colour=acc, align="CENTER")
            add_role(sid, 1, s["title"], 1_760_000, 1_300_000, "cover-title", colour=txt)
            if (s.get("title") or "").endswith("°"):            # degree mark in the primary accent
                tl = len(s["title"])
                reqs.append({"updateTextStyle": {"objectId": f"{sid}_t1",
                    "textRange": {"type": "FIXED_RANGE", "startIndex": tl - 1, "endIndex": tl},
                    "style": {"foregroundColor": {"opaqueColor": {"rgbColor": _rgb(p["primary"])}}},
                    "fields": "foregroundColor"}})
            if s.get("sub"):
                add_role(sid, 2, s["sub"], 3_150_000, 340_000, "eyebrow", colour=mut, align="CENTER")
            if s.get("standfirst"):
                add_role(sid, 3, s["standfirst"], 3_560_000, 1_000_000, "standfirst", colour=txt)
            if s.get("footer"):
                add_text(sid, 4, s["footer"], 4_560_000, 340_000, font=p["body"], size=9, color=_rgb(mut), align="CENTER", weight=body_weight)
        elif kind == "contents":
            add_role(sid, 0, s["eyebrow"], 470_000, 320_000, "eyebrow", colour=acc)
            add_role(sid, 1, s["title"], 800_000, 700_000, "section-title", colour=txt)
            reqs += _contents_reqs(sid, s.get("entries", []), MARGIN, 1_560_000, cw, PAGE_H - 1_560_000 - MARGIN,
                                   acc=acc, txt=txt, mut=mut, sans=p["body"])
        elif kind == "section":            # part divider — full-bleed, tone-coloured
            add_role(sid, 0, s["eyebrow"], 1_950_000, 360_000, "eyebrow", colour=acc, align="CENTER")
            add_role(sid, 1, s["title"], 2_350_000, 1_600_000, "section-title", colour=txt, align="CENTER")
        elif kind == "quote":
            add_role(sid, 0, s.get("eyebrow", ""), 700_000, 320_000, "eyebrow", colour=acc)
            add_role(sid, 1, "“" + s["quote"] + "”", 1_300_000, 3_000_000, "quote", colour=txt)
        elif kind == "callout":            # branded callout box: tint fill + accent edge
            box_x, box_y, box_h = MARGIN, 1_450_000, 2_300_000
            reqs += _shape(sid, f"{sid}_box", "ROUND_RECTANGLE", box_x, box_y, cw, box_h, _mix(acc, bgc, 0.90))
            reqs += _shape(sid, f"{sid}_edge", "RECTANGLE", box_x, box_y, 46_000, box_h, acc)  # ~3.6pt accent edge
            pad, tx, tw = 300_000, box_x + 300_000, cw - 600_000
            if s.get("heading"):
                add_role(sid, 0, s["heading"], box_y + pad, 380_000, "eyebrow", colour=acc, x=tx, w=tw)
            add_role(sid, 1, s.get("body", ""), box_y + pad + 480_000, box_h - pad - 700_000, "body", colour=txt, x=tx, w=tw)
        elif kind in ("table", "diagram", "cards", "panel", "flow", "chart", "stat-panel", "bullseye", "hype-cycle"):
            add_role(sid, 0, s["eyebrow"], 520_000, 300_000, "eyebrow", colour=acc)
            add_role(sid, 1, s.get("title", ""), 850_000, 620_000, "topic-title", colour=txt)
            y0 = _lead_band(sid, s.get("lead"), BASEY.get(kind, 1_650_000), colour=txt)
            avail = PAGE_H - y0 - MARGIN
            if kind == "table":
                reqs += _table_reqs(sid, f"{sid}_tbl", s["rows"], MARGIN, max(y0, 1_550_000), cw, pv, tsize)
            elif kind == "diagram":
                reqs += _swimlane_reqs(sid, archetype_ir.normalise_swimlane(s.get("spec", {})), MARGIN, y0, cw, avail, pv)
            elif kind == "cards":
                reqs += _card_grid_reqs(sid, archetype_ir.normalise_cards(s["cards"]).cards, MARGIN, y0, cw, min(avail, 2_400_000), pv)
            elif kind == "panel":
                reqs += _panel_reqs(sid, s.get("spec", {}), MARGIN, y0, cw, avail, pv)
            elif kind == "flow":
                reqs += _flow_reqs(sid, archetype_ir.normalise_flow(s["steps"]), MARGIN, y0, cw, avail, pv)
            elif kind == "chart":
                reqs += _chart_reqs(sid, archetype_ir.normalise_chart(s.get("spec", {})), MARGIN, y0, cw, avail, pv)
            elif kind == "stat-panel":
                reqs += _stat_reqs(sid, archetype_ir.normalise_stats(s.get("spec")), MARGIN, y0, cw, avail, pv)
            elif kind == "bullseye":
                reqs += _bullseye_reqs(sid, archetype_ir.normalise_bullseye(s.get("spec")), MARGIN, y0, cw, avail, pv)
            else:  # hype-cycle
                reqs += _hype_reqs(sid, archetype_ir.normalise_hype(s.get("spec")), MARGIN, y0, cw, avail, pv)
        elif kind == "image":              # bespoke figure: a rasterised image is full-bleed (it carries its own header); else a figure card with chrome
            node = archetype_ir.normalise_image(s.get("spec"))
            if node.url:
                reqs += _image_reqs(sid, node, MARGIN, 560_000, cw, PAGE_H - 560_000 - MARGIN, pv)
            else:
                add_role(sid, 0, s["eyebrow"], 520_000, 300_000, "eyebrow", colour=acc)
                add_role(sid, 1, s.get("title", ""), 850_000, 620_000, "topic-title", colour=txt)
                reqs += _image_reqs(sid, node, MARGIN, 1_650_000, cw, PAGE_H - 1_650_000 - MARGIN, pv)
        elif kind == "pullquote":          # native pull-quote
            add_role(sid, 0, s.get("eyebrow", ""), 700_000, 320_000, "eyebrow", colour=acc)
            reqs += _pullquote_reqs(sid, archetype_ir.normalise_pullquote(s.get("spec")), MARGIN, 1_300_000, cw, 2_800_000, pv)
        elif kind == "cta":                # native CTA banner
            reqs += _cta_reqs(sid, archetype_ir.normalise_cta(s.get("spec")), MARGIN, 2_000_000, cw, 1_150_000, pv)
        else:  # content — sections flowed into two columns, each a stack of positioned boxes
            add_role(sid, 0, s["eyebrow"], 520_000, 300_000, "eyebrow", colour=acc)
            add_role(sid, 1, s["title"], 850_000, 760_000, "topic-title", colour=txt)
            for ci, col in enumerate((s.get("col1", []), s.get("col2", []))):
                cx0 = MARGIN + ci * (_colw + GUTTER)
                yy = CONTENT_TOP
                for si, sec in enumerate(col):
                    sh = round(_section_h(sec, _colw, bodysize, _sub) * PT) + 70_000
                    bid = f"{sid}_c{ci}s{si}"
                    if sec["type"] == "callout":
                        reqs += _callout_box(sid, bid, cx0, yy, _colw, sh, sec["lines"], acc=acc, bgc=bgc, txt=txt, sans=p["body"], weight=body_weight)
                    else:
                        reqs += _rich_text_box(sid, bid, sec["lines"], cx0, yy, _colw, sh,
                                               font=(body_family or p["body"]), size=bodysize, color=txt, acc=acc, serif=p["display"],
                                               weight=body_weight, line_spacing=line_sp, space_after=space_aft, subhead_size=subhead_size)
                    yy += sh + 90_000
    return title, reqs


def payload(manifest_path: Path, *, brand: str = "nopilot", profile: str | None = None) -> dict[str, Any]:
    """The dry-run: the full native-slide spec (title + batchUpdate requests), no creds."""
    title, reqs = build_requests(manifest_path, brand=brand, profile=profile)
    return {"title": title, "slides": sum(1 for r in reqs if "createSlide" in r), "requests": reqs}


# ----------------------------------------------------------------- delivery config
_SCOPES = ["https://www.googleapis.com/auth/presentations", "https://www.googleapis.com/auth/drive"]


def load_delivery() -> dict[str, Any]:
    """Per-account delivery config — from $STUDIOS_DELIVERY_CONFIG or
    ~/context/studios/delivery.yml. Credentials are env-var *names* (paths to the
    SA key), never inline; folder IDs are Shared-Drive destinations."""
    path = os.environ.get("STUDIOS_DELIVERY_CONFIG") or str(Path.home() / "context" / "studios" / "delivery.yml")
    p = Path(path)
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


def resolve_account(account: str, destination: str | None = None) -> tuple[str, str, str | None, str | None]:
    """account (+ optional destination) → (creds_path, drive_folder_id, impersonate, asset_path).

    ``creds_path`` is whatever ``credential_env`` points at — a service-account key
    *or* an OAuth authorized-user token (``_load_creds`` auto-detects which). ``asset_path``
    is an optional ``/``-separated sub-path find-or-created under the destination folder.
    """
    cfg = (load_delivery().get("accounts", {}) or {}).get(account)
    if not cfg:
        raise SystemExit(f"no delivery config for '{account}' — set STUDIOS_DELIVERY_CONFIG or ~/context/studios/delivery.yml")
    key = os.environ.get(cfg.get("credential_env", ""))
    if not key:
        raise SystemExit(f"credential env {cfg.get('credential_env')!r} is unset (point it at the creds JSON — SA key or OAuth token)")
    dest = (cfg.get("destinations", {}) or {}).get(destination or cfg.get("default_destination"))
    if not dest:
        raise SystemExit(f"no destination {destination!r} for account '{account}'")
    return key, dest["drive_folder_id"], dest.get("impersonate") or cfg.get("impersonate"), dest.get("asset_path")


# ----------------------------------------------------------------- live execution
def _load_creds(creds_file: str, impersonate: str | None = None):
    """Credentials from either a service-account key OR an OAuth authorized-user
    token (auto-detected by the JSON's `type`).

    Use OAuth for a personal @gmail.com destination: a service account can't write
    to a consumer My Drive (no storage quota; no Workspace → no Shared Drive and no
    domain-wide delegation). OAuth acts AS the user, so files are owned by them.
    """
    import json
    info = json.loads(Path(creds_file).read_text(encoding="utf-8"))
    if info.get("type") == "service_account":
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(creds_file, scopes=_SCOPES)
        if impersonate:  # domain-wide delegation (Workspace only)
            creds = creds.with_subject(impersonate)
        return creds
    from google.oauth2.credentials import Credentials  # authorized_user (OAuth)
    return Credentials.from_authorized_user_file(creds_file, _SCOPES)


def _services(creds_file: str, impersonate: str | None = None):
    from googleapiclient.discovery import build
    creds = _load_creds(creds_file, impersonate)
    return build("drive", "v3", credentials=creds), build("slides", "v1", credentials=creds)


def rasterize_svg(svg_path, *, scale: int = 2) -> tuple[bytes, float]:
    """Render an SVG file → (PNG bytes, aspect=w/h) via headless Chromium (playwright).
    Used to turn the docket's bespoke figures into real images for the Slides deck."""
    from playwright.sync_api import sync_playwright
    svg = Path(svg_path).read_text(encoding="utf-8")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(device_scale_factor=scale)
        pg.set_content(f'<!doctype html><html><body style="margin:0;background:transparent">{svg}</body></html>', wait_until="networkidle")
        el = pg.query_selector("svg")
        box = el.bounding_box() if el else None
        png = el.screenshot(omit_background=True) if el else pg.screenshot()
        b.close()
    aspect = (box["width"] / box["height"]) if box and box.get("height") else 2.0
    return png, aspect


def upload_drive_image(drive, data: bytes, name: str, *, folder_id: str | None = None) -> tuple[str, str]:
    """Upload PNG bytes to Drive, make it link-readable, return (file_id, fetchable url for createImage)."""
    import io
    from googleapiclient.http import MediaIoBaseUpload
    meta = {"name": name, "mimeType": "image/png"}
    if folder_id:
        meta["parents"] = [folder_id]
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype="image/png", resumable=False)
    f = drive.files().create(body=meta, media_body=media, fields="id").execute()
    fid = f["id"]
    drive.permissions().create(fileId=fid, body={"role": "reader", "type": "anyone"}).execute()
    return fid, f"https://lh3.googleusercontent.com/d/{fid}"


def authorize(client_secret_file: str, token_out: str, *, redirect_uri: str | None = None) -> str:
    """Run the OAuth consent flow (opens a browser) and save an authorized-user token.
    The signed-in user IS the owner of everything the pipeline then creates — the route
    for personal @gmail.com destinations. The user runs this (it's their login).

    ``redirect_uri`` None → a **Desktop-app** client (loopback on a random port via
    ``run_local_server``). For a **Web** client, pass one of its already-whitelisted
    loopback redirects (e.g. ``http://127.0.0.1:3010/api/auth/google/callback``): a
    one-shot local server on that host/port/path captures the code, so the production
    web client is reused untouched and no Desktop client is needed.
    """
    if not redirect_uri:
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, _SCOPES)
        creds = flow.run_local_server(port=0)
        Path(token_out).write_text(creds.to_json(), encoding="utf-8")
        return token_out

    import http.server
    import webbrowser
    from urllib.parse import parse_qs, urlparse

    from google_auth_oauthlib.flow import Flow

    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")   # tolerate Google reordering/expanding granted scopes
    u = urlparse(redirect_uri)
    host, port, want_path = (u.hostname or "127.0.0.1"), (u.port or 80), (u.path or "/")
    flow = Flow.from_client_secrets_file(client_secret_file, scopes=_SCOPES, redirect_uri=redirect_uri)
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    captured: dict[str, str] = {}

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parts = urlparse(self.path)
            q = parse_qs(parts.query)
            if parts.path == want_path and ("code" in q or "error" in q):
                captured.update({k: v[0] for k, v in q.items()})
                body = ("Authorized — close this tab and return to the terminal."
                        if "code" in q else f"OAuth error: {q.get('error')}")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):  # keep the consent flow quiet
            pass

    try:
        httpd = http.server.HTTPServer((host, port), _Handler)
    except OSError as e:
        raise SystemExit(f"can't bind {host}:{port} for the OAuth redirect ({e}); "
                         "free the port or pass a different whitelisted --redirect-uri")
    print(f"Opening your browser to authorize as the signed-in Google user.\n"
          f"If it doesn't open, visit:\n{auth_url}\n")
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass
    try:
        while "code" not in captured and "error" not in captured:
            httpd.handle_request()
    finally:
        httpd.server_close()
    if "error" in captured:
        raise SystemExit(f"OAuth consent failed: {captured['error']}")
    flow.fetch_token(code=captured["code"])
    Path(token_out).write_text(flow.credentials.to_json(), encoding="utf-8")
    return token_out


def _ensure_subfolder(drive, parent_id: str, name: str) -> str:
    """Find-or-create a subfolder `name` under `parent_id` (Shared-Drive aware)."""
    safe = name.replace("'", "\\'")
    q = (f"name = '{safe}' and '{parent_id}' in parents and "
         "mimeType = 'application/vnd.google-apps.folder' and trashed = false")
    res = drive.files().list(q=q, fields="files(id)", supportsAllDrives=True,
                             includeItemsFromAllDrives=True).execute()
    if res.get("files"):
        return res["files"][0]["id"]
    return drive.files().create(
        body={"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]},
        fields="id", supportsAllDrives=True).execute()["id"]


def _ensure_path(drive, parent_id: str, path: str) -> str:
    """Find-or-create each ``/``-separated segment of ``path`` under ``parent_id``;
    return the leaf folder id. ``'360/360-proposition'`` nests both levels."""
    cur = parent_id
    for seg in (s.strip() for s in path.split("/")):
        if seg:
            cur = _ensure_subfolder(drive, cur, seg)
    return cur


def execute(manifest_path: Path | None, *, brand: str = "nopilot", creds_file: str,
            drive_folder_id: str | None = None, asset_name: str | None = None,
            presentation_id: str | None = None, impersonate: str | None = None,
            profile: str | None = None, prebuilt: tuple[str, list[dict]] | None = None) -> str:
    """Create (or update in place) the native deck via the Slides + Drive APIs.

    Creds may be a **service account** (Shared-Drive / domain-wide delegation) or an
    **OAuth authorized-user token** — the route for a personal @gmail.com My Drive, where
    a service account has no storage quota (see ``_load_creds`` / ``authorize``). Places
    the deck under ``drive_folder_id`` (``asset_name`` may be a ``/``-separated sub-path,
    find-or-created), or updates ``presentation_id`` in place. ``prebuilt`` pushes an
    already-rendered ``(title, requests)`` payload instead of rebuilding from
    ``manifest_path``. This is an account write — confirm first. Returns the URL.
    """
    drive, slides = _services(creds_file, impersonate=impersonate)
    title, reqs = prebuilt if prebuilt is not None else build_requests(manifest_path, brand=brand, profile=profile)

    if presentation_id:                                          # update in place (re-render)
        pid = presentation_id
        cur = slides.presentations().get(presentationId=pid, fields="slides(objectId)").execute().get("slides", [])
        batch = [{"deleteObject": {"objectId": s["objectId"]}} for s in cur] + reqs
    else:
        parent = drive_folder_id
        if parent and asset_name:
            parent = _ensure_path(drive, parent, asset_name)     # nested sub-path under the destination
        if parent:                                               # create inside the destination folder
            pid = drive.files().create(
                body={"name": title, "mimeType": "application/vnd.google-apps.presentation", "parents": [parent]},
                fields="id", supportsAllDrives=True).execute()["id"]
        else:                                                    # fallback: the account's own Drive root
            pid = slides.presentations().create(body={"title": title}).execute()["presentationId"]
        default = slides.presentations().get(presentationId=pid, fields="slides(objectId)").execute().get("slides", [])
        batch = reqs + [{"deleteObject": {"objectId": s["objectId"]}} for s in default]

    slides.presentations().batchUpdate(presentationId=pid, body={"requests": batch}).execute()
    return f"https://docs.google.com/presentation/d/{pid}/edit"


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m studio.gslide", description="Native Google Slides from a UDS docket (ADR-006).")
    ap.add_argument("manifest", nargs="?", help="docket manifest or flat .md source (omit with --payload / --authorize)")
    ap.add_argument("--brand", default="nopilot")
    ap.add_argument("--profile", help="render profile (presentation | proposal) — sets sizes + column count")
    ap.add_argument("--out", help="write the dry-run payload JSON here")
    ap.add_argument("--execute", action="store_true", help="create/update the live deck (an account write)")
    ap.add_argument("--payload", help="push a pre-built .gslide.json {title,requests} instead of rebuilding from a manifest")
    ap.add_argument("--account", help="delivery account (e.g. coh/npt) — resolves creds + folder + asset_path from the delivery config")
    ap.add_argument("--destination", help="named destination within the account (else its default)")
    ap.add_argument("--asset-name", help="sub-path under the destination (may be /-nested, e.g. 360/360-proposition); overrides the account's asset_path")
    ap.add_argument("--creds", help="explicit creds JSON — SA key OR OAuth token (overrides --account)")
    ap.add_argument("--folder", help="explicit Drive folder id (overrides --account)")
    ap.add_argument("--impersonate", help="Workspace user to act as (domain-wide delegation) — Workspace only, not consumer @gmail")
    ap.add_argument("--presentation-id", help="update this deck in place instead of creating a new one")
    ap.add_argument("--authorize", action="store_true", help="run the OAuth consent flow and write an authorized-user token (personal @gmail destinations)")
    ap.add_argument("--client-secret", help="OAuth client-secret JSON (with --authorize)")
    ap.add_argument("--token-out", help="where to write the authorized-user token (with --authorize)")
    ap.add_argument("--redirect-uri", help="exact whitelisted loopback redirect for a Web OAuth client (with --authorize); omit for a Desktop-app client")
    args = ap.parse_args(argv)

    if args.authorize:
        if not (args.client_secret and args.token_out):
            ap.error("--authorize needs --client-secret and --token-out")
        print(authorize(args.client_secret, args.token_out, redirect_uri=args.redirect_uri))
        return 0

    if args.execute:
        creds, folder, impersonate, asset_name = args.creds, args.folder, args.impersonate, args.asset_name
        if args.account and not creds:
            creds, folder, cfg_imp, cfg_asset = resolve_account(args.account, args.destination)
            impersonate = impersonate or cfg_imp
            asset_name = asset_name or cfg_asset
        if not creds:
            ap.error("--execute needs --account (configured) or --creds")
        prebuilt = None
        if args.payload:
            data = json.loads(Path(args.payload).read_text(encoding="utf-8"))
            prebuilt = (data["title"], data["requests"])
        elif not args.manifest:
            ap.error("--execute needs a manifest or --payload")
        print(execute(Path(args.manifest) if args.manifest else None, brand=args.brand, creds_file=creds,
                       drive_folder_id=folder, asset_name=asset_name,
                       presentation_id=args.presentation_id, impersonate=impersonate, prebuilt=prebuilt))
        return 0

    if not args.manifest:
        ap.error("a manifest is required for a dry-run (or use --execute --payload, or --authorize)")
    pl = payload(Path(args.manifest), brand=args.brand, profile=args.profile)
    if args.out:
        Path(args.out).write_text(json.dumps(pl, indent=2), encoding="utf-8")
        print(f"wrote {args.out} — {pl['slides']} slides, {len(pl['requests'])} requests")
    else:
        print(json.dumps(pl, indent=2)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
