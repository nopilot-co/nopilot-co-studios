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
        "active": light.get("active", "#FFC10E"),
        "on_active": light.get("on-active", "#1C2022"),
        "surface": light.get("surface", "#FFFFFF"),
        "paper": light.get("bg", "#F1F1F4"),
        "on_primary": light.get("on-primary", "#FFFFFF"),
        "display": display, "body": body, "mono": mono,
        "eyebrow": light.get("eyebrow", light.get("primary", "#C3094A")),  # overline colour (Coherence: dark raspberry)
        "heading_weight": u["font"].get("weight", {}).get("heading"),       # e.g. 600 = semibold; None → bold boolean
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
    """A topic's body as slide lines + the first pull-quote (if any)."""
    try:
        md = uds_html._read_ref(content_dir, topic["section_md"])
    except OSError:
        return [], ""
    lines: list[str] = []
    quote = ""
    for b in uds_html._blocks(md):
        if b[0] == "h" and b[1] == 1:
            continue
        if b[0] == "h":
            lines.append("§ " + _clean(b[2]).replace("Detail: ", ""))
        elif b[0] == "p":
            lines.append(_clean(b[1]))
        elif b[0] == "list":
            lines += ["• " + _clean(it) for it in b[1]]
        elif b[0] == "quote" and not quote:
            quote = _clean(b[1])
    return [ln for ln in lines if ln], quote


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


def slide_specs_flat(src_path: Path, *, brand: str = "nopilot", lines_per_slide: int = 6, group_lead: int = 0) -> tuple[str, list[dict]]:
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
            elif b[0] == "table":            # data table → its own slide, grouping the supporting lead-in prose
                head, lead = (pending[:-group_lead], pending[-group_lead:]) if group_lead else (pending, [])
                _emit(head, sub_title); pending = []
                if b[1]:
                    deck.append({"kind": "table", "eyebrow": gtitle, "title": sub_title, "rows": b[1], "lead": lead})
                elif lead:
                    _emit(lead, sub_title)
            elif b[0] == "diagram":          # timeline / swimlane → its own slide, grouping the lead-in prose
                head, lead = (pending[:-group_lead], pending[-group_lead:]) if group_lead else (pending, [])
                _emit(head, sub_title); pending = []
                deck.append({"kind": "diagram", "eyebrow": gtitle, "title": sub_title, "spec": b[1], "lead": lead})
            else:
                pending += _flat_lines([b])
        _emit(pending, sub_title)
    return title, deck


def slide_specs(manifest_path: Path, *, brand: str = "nopilot", lines_per_slide: int = 6, group_lead: int = 0) -> tuple[str, list[dict]]:
    """Docket manifest → an ordered deck of plain slide specs (the IR). A ``.md`` path
    is treated as a flat HTML-laced source (``slide_specs_flat``)."""
    manifest_path = Path(manifest_path)
    if manifest_path.suffix.lower() in (".md", ".markdown"):
        return slide_specs_flat(manifest_path, brand=brand, lines_per_slide=lines_per_slide, group_lead=group_lead)
    content_dir = manifest_path.parent.parent
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    meta = manifest.get("meta", {})
    deck: list[dict] = []
    for t in manifest.get("topics", []):
        tid = t.get("id")
        if t.get("type") == "index":
            continue
        if tid == "cover":
            try:
                body = uds_html._read_ref(content_dir, t["section_md"]) if t.get("section_md") else ""
            except OSError:
                body = ""
            wm = uds_html._labelled(body, "Wordmark") or "360°"
            m = re.match(r"^(.*?°)\s*(.*)$", wm, re.DOTALL)
            title, sub = (m.group(1), _clean(m.group(2))) if m else (wm, "")
            deck.append({"kind": "cover", "eyebrow": uds_html._labelled(body, "Eyebrow") or "A partnership proposition",
                         "title": title, "sub": sub, "standfirst": _clean(uds_html._labelled(body, "Standfirst"))})
        elif not t.get("section_md"):
            deck.append({"kind": "section", "eyebrow": _clean(t.get("eyebrow", "")) or "Section", "title": _clean(t.get("title", ""))})
        else:
            lines, quote = _topic_body(content_dir, t)
            eyebrow, title = _clean(t.get("eyebrow", "")), _clean(t.get("title", ""))
            if quote:
                deck.append({"kind": "quote", "eyebrow": eyebrow, "title": title, "quote": quote})
            chunks = [lines[i:i + lines_per_slide] for i in range(0, len(lines), lines_per_slide)] or [[]]
            for n, chunk in enumerate(chunks):
                deck.append({"kind": "content", "eyebrow": eyebrow,
                             "title": title + ("" if n == 0 else f" (cont. {n + 1})"), "body": chunk})
    return str(meta.get("doc_title", "360 proposition")), deck


# ----------------------------------------------------------------- IR → Slides API requests
def _text_box(slide_id: str, box_id: str, x: int, y: int, w: int, h: int) -> dict:
    return {"createShape": {"objectId": box_id, "shapeType": "TEXT_BOX",
            "elementProperties": {"pageObjectId": slide_id,
                "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": h, "unit": "EMU"}},
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"}}}}


def _style(box_id: str, *, font: str, size: int, color: dict, bold: bool = False,
           align: str | None = None, weight: int | None = None) -> list[dict]:
    style: dict = {"fontSize": {"magnitude": size, "unit": "PT"},
                   "foregroundColor": {"opaqueColor": {"rgbColor": color}}}
    if weight:  # a true weighted face (e.g. Poppins SemiBold 600) — "never bold"; beats the bold boolean
        style["weightedFontFamily"] = {"fontFamily": font, "weight": weight}
        fields = "fontSize,foregroundColor,weightedFontFamily"
    else:
        style.update({"fontFamily": font, "bold": bold})
        fields = "fontFamily,fontSize,foregroundColor,bold"
    reqs = [{"updateTextStyle": {"objectId": box_id, "textRange": {"type": "ALL"},
             "style": style, "fields": fields}}]
    if align:
        reqs.append({"updateParagraphStyle": {"objectId": box_id, "textRange": {"type": "ALL"},
                     "style": {"alignment": align}, "fields": "alignment"}})
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


def _swimlane_reqs(slide_id: str, spec: dict, x: int, y: int, w: int, h: int, p: dict) -> list[dict]:
    """A native swimlane / timeline: a month axis, lane rows with span bars (primary tint),
    and milestone diamonds. All native shapes — editable, crisp, on-brand, no image upload."""
    months = spec.get("months", [])
    lanes = spec.get("lanes", [])
    milestones = spec.get("milestones", []) or []
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
        out.append({"insertText": {"objectId": ln, "text": str(lane.get("name", "")), "insertionIndex": 0}})
        out += _style(ln, font=p["body"], size=9, color=_rgb(p["ink"]), weight=600)
        sx, ex = mx(lane.get("start")), mx(lane.get("end"))
        bw = max(int(ex - sx), 240_000)
        bar = f"{slide_id}_bar{li}"
        out += _shape(slide_id, f"{bar}r", "ROUND_RECTANGLE", int(sx), ly, bw, int(lane_h * 0.6), tint)
        out.append(_text_box(slide_id, f"{bar}t", int(sx + 70_000), ly + 24_000, bw - 120_000, int(lane_h * 0.6)))
        out.append({"insertText": {"objectId": f"{bar}t", "text": str(lane.get("label", "")), "insertionIndex": 0}})
        out += _style(f"{bar}t", font=p["body"], size=8, color=_rgb(p["ink"]))
    my = top + len(lanes) * (lane_h + 36_000) + 30_000   # milestone diamonds
    for mi, ms in enumerate(milestones):
        dx = int(mx(ms.get("at")) - 66_000)
        d = f"{slide_id}_ms{mi}"
        out += _shape(slide_id, f"{d}d", "DIAMOND", dx, my, 132_000, 132_000, p["primary"])
        out.append(_text_box(slide_id, f"{d}t", dx - 520_000, my + 150_000, 1_180_000, 280_000))
        out.append({"insertText": {"objectId": f"{d}t", "text": str(ms.get("label", "")), "insertionIndex": 0}})
        out += _style(f"{d}t", font=p["body"], size=8, color=_rgb(p["primary"]), align="CENTER", weight=600)
    return out


def build_requests(manifest_path: Path, *, brand: str = "nopilot", profile: str | None = None) -> tuple[str, list[dict]]:
    """IR → Slides API batchUpdate requests (cover, section, quote, content). A render
    ``profile`` (e.g. 'proposal') sets the reading sizes + column count from the UDS."""
    prof = uds_mod.profile_spec(profile)
    columns = int(prof.get("columns", 1))
    tsize = int(prof.get("table_size") or 9)
    title, deck = slide_specs(manifest_path, brand=brand, lines_per_slide=int(prof.get("lines_per_slide", 6)), group_lead=int(prof.get("group_lead", 0)))
    p = _palette(brand)
    reqs: list[dict] = []
    cx, cw = MARGIN, PAGE_W - 2 * MARGIN

    def add_text(slide_id: str, n: int, text: str, y: int, h: int, *, font, size, color, bold=False, align=None, weight=None, x=None, w=None) -> None:
        box = f"{slide_id}_t{n}"
        reqs.append(_text_box(slide_id, box, cx if x is None else x, y, cw if w is None else w, h))
        reqs.append({"insertText": {"objectId": box, "text": text, "insertionIndex": 0}})
        reqs.extend(_style(box, font=font, size=size, color=color, bold=bold, align=align, weight=weight))

    R = uds_mod.render_contract(brand, "slide", profile=prof)   # role → resolved {family,size,weight,transform,align,colour}
    _AL = {"center": "CENTER", "right": "END", "justify": "JUSTIFIED"}  # left == default → no paragraph request

    def add_role(slide_id: str, n: int, text: str, y: int, h: int, role: str, *, colour=None, align=None, x=None, w=None) -> None:
        st = R.get(role) or {}
        s = text.upper() if st.get("transform") == "upper" else text
        fam = (st.get("family") or "Inter").split(",")[0].strip()
        if "geist" in fam.lower():            # Google Workspace has no Geist Mono → the UDS fallback
            fam = _GSLIDE_MONO
        wt = st.get("weight")
        add_text(slide_id, n, s, y, h, font=fam, size=round(st.get("size", 12)),
                 color=_rgb(colour or st.get("colour", "#1C2022")),
                 align=align or _AL.get(st.get("align")), bold=(wt is None), weight=wt, x=x, w=w)

    def _lead_band(sid: str, lead, base_y: int) -> int:
        """Grouped supporting prose (two columns) above a table/diagram; returns the y to start the data at."""
        if not lead:
            return base_y
        lh, gutter = 1_000_000, 360_000
        colw = (cw - gutter) // 2
        mid = (len(lead) + 1) // 2
        add_role(sid, 8, "\n\n".join(lead[:mid]), base_y, lh, "body", x=MARGIN, w=colw)
        if lead[mid:]:
            add_role(sid, 9, "\n\n".join(lead[mid:]), base_y, lh, "body", x=MARGIN + colw + gutter, w=colw)
        return base_y + lh + 200_000

    for i, s in enumerate(deck):
        sid = f"slide{i:03d}"  # Slides object IDs must be >= 5 chars
        reqs.append({"createSlide": {"objectId": sid, "insertionIndex": i,
                     "slideLayoutReference": {"predefinedLayout": "BLANK"}}})
        kind = s["kind"]
        if kind == "cover":
            reqs.append(_bg(sid, p["surface"]))
            add_role(sid, 0, s["eyebrow"], 1_400_000, 360_000, "eyebrow", align="CENTER")
            add_role(sid, 1, s["title"], 1_800_000, 1_500_000, "cover-title")
            if s.get("standfirst"):
                add_role(sid, 2, s["standfirst"], 3_500_000, 1_200_000, "standfirst")
        elif kind == "section":
            reqs.append(_bg(sid, p["ink"]))            # dark colour block
            add_role(sid, 0, s["eyebrow"], 1_900_000, 360_000, "eyebrow-ondark")
            add_role(sid, 1, s["title"], 2_300_000, 1_600_000, "section-title")
        elif kind == "quote":
            reqs.append(_bg(sid, p["paper"]))
            add_role(sid, 0, s["eyebrow"], 700_000, 320_000, "eyebrow")
            add_role(sid, 1, "“" + s["quote"] + "”", 1_300_000, 3_000_000, "quote")
        elif kind == "callout":            # branded callout box: tint fill + primary accent edge
            reqs.append(_bg(sid, p["surface"]))
            box_x, box_y, box_h = MARGIN, 1_450_000, 2_300_000
            reqs += _shape(sid, f"{sid}_box", "ROUND_RECTANGLE", box_x, box_y, cw, box_h, _mix(p["primary"], "#FFFFFF", 0.90))
            reqs += _shape(sid, f"{sid}_edge", "RECTANGLE", box_x, box_y, 46_000, box_h, p["primary"])  # ~3.6pt accent edge
            pad, tx, tw = 300_000, box_x + 300_000, cw - 600_000
            if s.get("heading"):
                add_role(sid, 0, s["heading"], box_y + pad, 380_000, "eyebrow", x=tx, w=tw)
            add_role(sid, 1, s.get("body", ""), box_y + pad + 480_000, box_h - pad - 700_000, "body", x=tx, w=tw)
        elif kind == "table":              # native data table
            reqs.append(_bg(sid, p["surface"]))
            add_role(sid, 0, s["eyebrow"], 520_000, 300_000, "eyebrow")
            add_role(sid, 1, s.get("title", ""), 850_000, 620_000, "topic-title")
            ty = _lead_band(sid, s.get("lead"), 1_550_000)
            reqs += _table_reqs(sid, f"{sid}_tbl", s["rows"], MARGIN, ty, cw, p, tsize)
        elif kind == "diagram":            # native swimlane / timeline
            reqs.append(_bg(sid, p["surface"]))
            add_role(sid, 0, s["eyebrow"], 520_000, 300_000, "eyebrow")
            add_role(sid, 1, s.get("title", ""), 850_000, 620_000, "topic-title")
            dy = _lead_band(sid, s.get("lead"), 1_950_000)
            reqs += _swimlane_reqs(sid, s.get("spec", {}), MARGIN, dy, cw, PAGE_H - dy - MARGIN, p)
        else:  # content
            reqs.append(_bg(sid, p["surface"]))
            add_role(sid, 0, s["eyebrow"], 520_000, 300_000, "eyebrow")
            add_role(sid, 1, s["title"], 850_000, 760_000, "topic-title")
            if s["body"]:
                by, bh = 1_650_000, PAGE_H - 1_650_000 - MARGIN
                if columns == 2:                       # two-column reading layout (proposal)
                    gutter = 360_000
                    colw = (cw - gutter) // 2
                    mid = (len(s["body"]) + 1) // 2
                    add_role(sid, 2, "\n\n".join(s["body"][:mid]), by, bh, "body", x=MARGIN, w=colw)
                    if s["body"][mid:]:
                        add_role(sid, 3, "\n\n".join(s["body"][mid:]), by, bh, "body", x=MARGIN + colw + gutter, w=colw)
                else:
                    add_role(sid, 2, "\n\n".join(s["body"]), by, bh, "body")
    return title, reqs


def payload(manifest_path: Path, *, brand: str = "nopilot") -> dict[str, Any]:
    """The dry-run: the full native-slide spec (title + batchUpdate requests), no creds."""
    title, reqs = build_requests(manifest_path, brand=brand)
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
    pl = payload(Path(args.manifest), brand=args.brand)
    if args.out:
        Path(args.out).write_text(json.dumps(pl, indent=2), encoding="utf-8")
        print(f"wrote {args.out} — {pl['slides']} slides, {len(pl['requests'])} requests")
    else:
        print(json.dumps(pl, indent=2)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
