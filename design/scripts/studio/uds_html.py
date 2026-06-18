"""markdown → UDS-HTML mapper (ADR-006 Slice 2/4/7 — the inversion).

Maps the studio's universal `:::` source (and a manifest-driven **docket** of
sections) to the UDS application-UI archetypes (``uds/ui/base.css`` classes),
wrapped by ``studio.hydrate`` into the HTML *composition primary*. Same source →
HTML now; the deck/gslide serialiser (held) later. One source, parallel renders.

Two entry points:
- ``render_file`` — a single flat `:::` source (e.g. examples/360-proposition.md).
- ``render_docket_file`` — a docket: ``content/manifest.yaml`` ordering prose
  ``sections/`` (+ a cover/intro file with ``#anchor`` chunks) + CSV tables. Used
  to re-render the 360-gtm-proposition docket through the UDS (Slice 7). The
  two-axis showcase nav and viz/charts are not ported — content renders as the
  UDS single-flow document; viz are marked as deferred placeholders.
"""

from __future__ import annotations

import csv
import re
from html import escape as _esc
from pathlib import Path
from typing import Any

import yaml

from . import archetype_ir as _ir
from . import hydrate as hydrate_mod

_FENCE_RE = re.compile(r"^:::+\s*([a-z][a-z0-9-]*)\s*$")
_FENCE_END = re.compile(r"^:::+\s*$")
_HEAD_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_MARKER_RE = re.compile(r"\[\[[^\]]+\]\]")  # [[validate]] / [[PROOF]] editorial markers


# ----------------------------------------------------------------- parse
def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = re.match(r"\A---\n(.*?)\n---\n?(.*)\Z", text, re.DOTALL)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, m.group(2)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def _blocks(body: str) -> list[tuple]:
    """Tokenise into ordered blocks: ('h',level,text) · ('p',text) · ('quote',text)
    · ('list',[items]) · ('hr',) · ('fence',name,inner) · ('table',rows)."""
    lines = body.splitlines()
    out: list[tuple] = []
    i, n = 0, len(lines)
    para: list[str] = []

    def flush() -> None:
        if para:
            out.append(("p", " ".join(s.strip() for s in para).strip()))
            para.clear()

    while i < n:
        line = lines[i]
        s = line.strip()
        if fence := _FENCE_RE.match(s):
            flush()
            name, inner, i = fence.group(1), [], i + 1
            while i < n and not _FENCE_END.match(lines[i].strip()):
                inner.append(lines[i])
                i += 1
            i += 1
            out.append(("fence", name, "\n".join(inner)))
        elif s.startswith("|") and "|" in s:
            flush()
            rows = []
            while i < n and lines[i].lstrip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            out.append(("table", rows))
        elif s.startswith(">"):
            flush()
            q = []
            while i < n and lines[i].lstrip().startswith(">"):
                q.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append(("quote", "\n".join(q).strip()))
        elif re.match(r"^[-*]\s+", s):
            flush()
            items = []
            while i < n and re.match(r"^[-*]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*]\s+", "", lines[i].strip()))
                i += 1
            out.append(("list", items))
        elif s == "---":
            flush()
            out.append(("hr",))
            i += 1
        elif h := _HEAD_RE.match(line):
            flush()
            out.append(("h", len(h.group(1)), h.group(2).strip()))
            i += 1
        elif not s:
            flush()
            i += 1
        else:
            para.append(line)
            i += 1
    flush()
    return out


# ----------------------------------------------------------------- inline + emit
def _inline(text: str) -> str:
    t = _esc(_MARKER_RE.sub("", text)).strip()
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


def _pull_from_text(quote: str) -> str:
    lines = [ln.strip() for ln in quote.strip().splitlines() if ln.strip()]
    attribution = ""
    if lines and re.match(r"^[—-]\s+", lines[-1]):
        attribution = re.sub(r"^[—-]\s+", "", lines.pop())
    body = " ".join(lines)
    attr = f'<figcaption class="uds-pull-quote__attribution">{_inline(attribution)}</figcaption>' if attribution else ""
    return f'<figure class="uds-pull-quote"><p>{_inline(body)}</p>{attr}</figure>'


def _stat_grid(inner: str) -> str:
    items = yaml.safe_load(inner) or []
    cells = [
        f'<div class="uds-stat"><span class="uds-stat__value">{_esc(str(it.get("value","")))}</span>'
        f'<span class="uds-stat__label">{_esc(str(it.get("label","")))}</span>'
        + (f'<span class="uds-stat__delta">{_esc(str(it.get("delta")))}</span>' if it.get("delta") else "")
        + "</div>"
        for it in items
    ]
    return f'<section class="uds-grid" data-cols="{min(len(cells),4) or 1}">{"".join(cells)}</section>'


def _callout(inner: str) -> str:
    parts = []
    for b in _blocks(inner):
        if b[0] == "h":
            parts.append(f"<h3>{_inline(b[2])}</h3>")
        elif b[0] == "p":
            parts.append(f"<p>{_inline(b[1])}</p>")
    return f'<div class="uds-callout">{"".join(parts)}</div>'


def _process(inner: str) -> str:
    data = yaml.safe_load(inner) or {}
    steps = data.get("steps", []) if isinstance(data, dict) else data
    cells = []
    for idx, step in enumerate(steps, 1):
        title, _, rest = str(step).partition(" — ")
        excerpt = f'<p class="uds-card__excerpt">{_inline(rest)}</p>' if rest else ""
        cells.append(
            f'<div class="uds-card"><div class="uds-card__body"><p class="uds-eyebrow">{idx:02d}</p>'
            f'<h3 class="uds-card__title">{_inline(title)}</h3>{excerpt}</div></div>'
        )
    return f'<section class="uds-grid" data-cols="{min(len(cells),4) or 1}">{"".join(cells)}</section>'


def _cta(inner: str) -> str:
    text = " ".join(s.strip() for s in inner.strip().splitlines())
    return ('<aside class="uds-banner uds-banner--promo">'
            f'<p>{_inline(text)}</p>'
            '<a class="uds-button uds-button--primary" href="#book">Book a paid Lunch &amp; Learn</a></aside>')


def _numfmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _chart(inner: str, ctx: dict | None = None) -> str:
    """A native HTML bar chart from a ChartNode — self-contained inline-styled DOM bars
    (no image, no external-CSS dependency), coloured from the brand's dataviz ramp
    (``ctx['ramp']``) so HTML matches the gslide/pptx natives. Colours theme via
    ``var(--uds-*, fallback)`` when a stylesheet is present and fall back otherwise; the
    .uds-chart classes + ``--uds-bar-*`` custom props are hooks for later stylesheet theming."""
    node = _ir.normalise_chart(inner)
    ramp = (ctx or {}).get("ramp") or _ir.DEFAULT_RAMP
    s0 = node.series[0] if node.series else None
    vals = list(s0.values) if s0 else []
    title = (f'<figcaption class="uds-chart__title" style="font-family:var(--uds-font-mono,monospace);'
             'font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;'
             f'color:var(--uds-color-primary,#C3094A);margin-bottom:.6rem">{_inline(node.title)}</figcaption>') if node.title else ""
    if not vals:
        return (f'<figure class="uds-chart uds-chart--empty" data-type="{_esc(node.chart_type)}" style="margin:1.5rem 0">'
                f'{title}<p class="uds-muted">[chart: no data]</p></figure>')
    mx = max(vals) or 1.0
    cats = node.categories
    disp = s0.displays if s0 else []
    bars = []
    for i, v in enumerate(vals):
        hpct = round(max(v / mx * 100.0, 2.0), 1)
        col = ramp[i % len(ramp)]
        label = disp[i] if i < len(disp) else _numfmt(v)
        cat = cats[i] if i < len(cats) else ""
        bars.append(
            f'<div class="uds-chart__bar" style="--uds-bar-h:{hpct}%;--uds-bar-c:{col};'
            'flex:1;min-width:0;height:100%;display:flex;flex-direction:column;justify-content:flex-end;align-items:center">'
            f'<span class="uds-chart__val" style="font-size:.72rem;font-weight:600;color:var(--uds-color-text,#1C2022);margin-bottom:4px">{_esc(str(label))}</span>'
            f'<span class="uds-chart__fill" style="width:100%;height:{hpct}%;min-height:3px;background:{col};border-radius:6px 6px 0 0"></span>'
            f'<span class="uds-chart__cat" style="font-size:.7rem;color:var(--uds-color-text-subtle,#6E747A);margin-top:8px;text-align:center;overflow-wrap:anywhere">{_esc(str(cat))}</span></div>'
        )
    plot = ('<div class="uds-chart__plot" style="display:flex;align-items:flex-end;gap:12px;height:240px;'
            'padding-top:1.25rem;border-bottom:2px solid var(--uds-color-line,#E5E5E5)">' + "".join(bars) + "</div>")
    return f'<figure class="uds-chart" data-type="{_esc(node.chart_type)}" style="margin:1.75rem 0">{title}{plot}</figure>'


_FENCE = {"stat-panel": _stat_grid, "pullquote": _pull_from_text, "callout-panel": _callout,
          "process": _process, "cta": _cta}


def _table_rows(rows: list[str], caption: str = "") -> str:
    cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
    if len(rows) < 2:
        return ""
    head = "".join(f"<th>{_inline(c)}</th>" for c in cells(rows[0]))
    body = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells(r)) + "</tr>" for r in rows[2:])
    cap = f"<caption>{_inline(caption)}</caption>" if caption else ""
    return f'<table class="uds-table">{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def _render_blocks(blocks: list[tuple], *, demote: int = 0, ctx: dict | None = None) -> list[str]:
    out: list[str] = []
    for b in blocks:
        if b[0] == "h":
            level = min(b[1] + demote, 4)
            text = re.sub(r"^Detail:\s*", "", b[2])  # ### Detail: X → a subsection heading
            out.append(f"<h{level}>{_inline(text)}</h{level}>")
        elif b[0] == "p":
            out.append(f"<p>{_inline(b[1])}</p>")
        elif b[0] == "quote":
            out.append(_pull_from_text(b[1]))
        elif b[0] == "list":
            out.append("<ul>" + "".join(f"<li>{_inline(it)}</li>" for it in b[1]) + "</ul>")
        elif b[0] == "hr":
            out.append('<hr class="uds-divider">')
        elif b[0] == "table":
            out.append(_table_rows(b[1]))
        elif b[0] == "fence":
            if _ir.canonical(b[1]) == "chart":
                out.append(_chart(b[2], ctx))
            else:
                fn = _FENCE.get(b[1])
                out.append(fn(b[2]) if fn else "")
    return out


# ----------------------------------------------------------------- flat source
def render_body(source_md: str, *, brand: str | None = None) -> tuple[dict[str, Any], str]:
    """Map a single flat `:::` source to a UDS-HTML body (hero + detail body). ``brand``
    resolves the dataviz ramp for native viz (charts); None → the default ramp."""
    meta, body = split_frontmatter(source_md)
    ctx = {"ramp": _ir.palette_for(brand)}
    blocks = _blocks(body)
    hero_title = meta.get("title", "")
    standfirst: list[str] = []
    rest_start = len(blocks)
    seen_h2 = False
    for idx, b in enumerate(blocks):
        if b[0] == "h" and b[1] == 1:
            if not hero_title:
                hero_title = b[2]
        elif b[0] == "h" and b[1] == 2:
            rest_start = idx
            break
        elif b[0] == "p" and not seen_h2:
            standfirst.append(b[1])
        else:
            rest_start = idx
            break
    eyebrow = (_esc(str(meta.get("brand", "")).upper()) + " · PROPOSITION") if meta.get("brand") else ""
    hero = ['<header class="uds-hero">']
    if eyebrow:
        hero.append(f'<p class="uds-eyebrow">{eyebrow}</p>')
    hero.append(f'<h1 class="uds-hero__title">{_inline(hero_title)}</h1>')
    if standfirst:
        hero.append(f'<p class="uds-hero__standfirst">{_inline(" ".join(standfirst))}</p>')
    hero.append("</header>")
    body_html = _render_blocks(blocks[rest_start:], ctx=ctx)
    html = ('<article class="uds-detail">\n' + "".join(hero) + "\n"
            + '<div class="uds-detail__body">\n' + "\n".join(body_html) + "\n</div>\n</article>")
    return meta, html


# ----------------------------------------------------------------- docket
def _read_ref(content_dir: Path, ref: str) -> str:
    """Read a section_md ref (``path`` or ``path#anchor``); strip front-matter."""
    path_part, _, anchor = ref.partition("#")
    text = (content_dir / path_part).read_text(encoding="utf-8")
    _, body = split_frontmatter(text)
    if anchor:
        # Manifest anchors match headings loosely: "#introduction" → "# Section 1: Introduction".
        parts = re.split(r"^#\s+(.+)$", body, flags=re.M)
        for j in range(1, len(parts) - 1, 2):
            if _slug(anchor) in _slug(parts[j]):
                return parts[j + 1]
    return body


def _labelled(body: str, label: str) -> str:
    """Pull a ``**Label:** value`` (or following line) out of a cover/intro chunk."""
    m = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.*(?:\n(?!\s*\*\*|\s*#).*)*)", body)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def _wordmark(text: str) -> str:
    """Wordmark with the degree mark in crimson (the nopilot accent)."""
    return _inline(text).replace("°", '<span class="deg">°</span>')


_NAV_PREF = ["landscape", "vision", "model", "gtm", "commercials", "ask"]


def _doc_header(topics_by_id: dict[str, Any], version: str) -> str:
    nav = "".join(
        f'<a href="#{nid}">{_inline(topics_by_id[nid].get("title", nid))}</a>'
        for nid in _NAV_PREF if nid in topics_by_id
    )
    nav_html = f'<nav class="doc-nav">{nav}</nav>' if nav else ""
    ask = "#ask" if "ask" in topics_by_id else "#contents"
    return ('<header class="doc-header">'
            '<span class="doc-brand">360<span class="deg">°</span></span>'
            f'<span class="doc-badge">Draft · {_esc(version)}</span>'
            f'{nav_html}<a class="doc-cta" href="{ask}">The ask</a></header>')


def _doc_cover(content_dir: Path, topic: dict[str, Any], meta: dict[str, Any], version: str) -> str:
    try:
        body = _read_ref(content_dir, topic["section_md"]) if topic.get("section_md") else ""
    except OSError:
        body = ""
    eyebrow = _labelled(body, "Eyebrow") or topic.get("eyebrow", "A partnership proposition")
    wordmark = _labelled(body, "Wordmark") or topic.get("title", "360°")
    m = re.match(r"^(.*?°)\s*(.*)$", wordmark, re.DOTALL)
    title, sub = (m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()) if m else (wordmark, "")
    standfirst = _labelled(body, "Standfirst")
    footer = re.sub(r"\s+", " ", _labelled(body, "Footer")).strip() or (
        f"Prepared for {str(meta.get('audience','')).split('(')[0].strip()} · {version}")
    p = ['<section class="doc-cover" id="cover">',
         f'<p class="doc-cover-eyebrow">{_inline(eyebrow)}</p>',
         f'<h1 class="doc-cover-title">{_wordmark(title)}</h1>']
    if sub:
        p.append(f'<p class="doc-cover-sub">{_inline(sub)}</p>')
    if standfirst:
        p.append(f'<p class="doc-cover-standfirst">{_inline(standfirst)}</p>')
    if footer:
        p.append(f'<p class="doc-cover-footer">{_inline(footer)}</p>')
    p.append("</section>")
    return "".join(p)


def _doc_contents(topics: list[dict[str, Any]]) -> str:
    items = []
    for t in topics:
        if t.get("id") == "cover" or t.get("type") == "index":
            continue
        cls = ' class="is-part"' if not t.get("section_md") else ""
        items.append(f'<li{cls}><a href="#{_esc(t.get("id",""))}">{_inline(t.get("title",""))}</a></li>')
    return ('<section class="doc-contents" id="contents">'
            '<p class="uds-eyebrow">Contents</p><h2>What’s inside</h2>'
            f'<ol>{"".join(items)}</ol></section>')


def _doc_section_cover(topic: dict[str, Any], dark: bool) -> str:
    cls = "doc-section-cover is-dark" if dark else "doc-section-cover"
    eyebrow = _inline(topic.get("eyebrow", "")) or "Section"
    return (f'<section class="{cls}" id="{_esc(topic.get("id",""))}">'
            f'<p class="doc-section-eyebrow">{eyebrow}</p>'
            f'<h2>{_inline(topic.get("title",""))}</h2></section>')


def _csv_table(content_dir: Path, spec: dict[str, Any]) -> str:
    try:
        with (content_dir / spec["csv"]).open(encoding="utf-8") as f:
            rows = [r for r in csv.reader(f) if r]
    except OSError:
        return ""
    if not rows:
        return ""
    head = "".join(f"<th>{_inline(c)}</th>" for c in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
    cap = f'<caption>{_inline(spec.get("caption",""))}</caption>' if spec.get("caption") else ""
    return f'<table class="uds-table">{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def _doc_topic(content_dir: Path, topic: dict[str, Any]) -> str:
    parts = [f'<article class="doc-topic" id="{_esc(topic.get("id",""))}">']
    if topic.get("eyebrow"):
        parts.append(f'<p class="uds-eyebrow">{_inline(topic["eyebrow"])}</p>')
    parts.append(f'<h2>{_inline(topic.get("title",""))}</h2><div class="doc-prose">')
    if topic.get("section_md"):
        try:
            md = _read_ref(content_dir, topic["section_md"])
        except OSError:
            parts.append(f'<p class="uds-muted">[section source missing: {_esc(topic["section_md"])}]</p>')
            md = ""
        if md:
            # drop the section's own leading H1 (manifest title is authoritative); demote the rest.
            blocks = [b for b in _blocks(md) if not (b[0] == "h" and b[1] == 1)]
            parts += _render_blocks(blocks, demote=1)
    for spec in topic.get("tables", []) or []:
        parts.append(_csv_table(content_dir, spec))
    if topic.get("viz"):
        names = ", ".join(str(v).split("/")[-1] for v in topic["viz"])
        parts.append(f'<p class="uds-muted">[figure: {_esc(names)} — viz port pending]</p>')
    parts.append("</div></article>")
    return "".join(parts)


def render_docket(manifest_path: Path, *, version: str = "v13") -> tuple[dict[str, Any], str]:
    """Render a docket to a UDS-HTML document with full chrome: branded header,
    cover, contents, alternating section covers, and prose topics."""
    manifest_path = Path(manifest_path)
    content_dir = manifest_path.parent.parent  # docket source/ root; section_md paths are "content/..."
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    meta = manifest.get("meta", {})
    topics = manifest.get("topics", [])
    topics_by_id = {t.get("id"): t for t in topics}

    main: list[str] = []
    dark = False
    for topic in topics:
        if topic.get("id") == "cover":
            main.append(_doc_cover(content_dir, topic, meta, version))
            main.append(_doc_contents(topics))
        elif topic.get("type") == "index":
            continue
        elif not topic.get("section_md"):
            main.append(_doc_section_cover(topic, dark))
            dark = not dark
        else:
            main.append(_doc_topic(content_dir, topic))
    body = (_doc_header(topics_by_id, version)
            + '\n<main class="doc-main">\n' + "\n".join(main) + "\n</main>")
    return {"title": meta.get("doc_title", "360 proposition"), **meta}, body


# ----------------------------------------------------------------- documents
def _self_contained(body: str, title: str, brand: str) -> str:
    """A standalone UDS document — base.css + theme inlined (docket-servable)."""
    base = hydrate_mod.BASE_CSS.read_text(encoding="utf-8")
    theme = (hydrate_mod.THEMES_DIR / f"theme-{brand}.css").read_text(encoding="utf-8")
    doc = (hydrate_mod.UI_ROOT / "uds-doc.css").read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
{hydrate_mod._FONT_LINK}
<style>{theme}</style>
<style>{base}</style>
<style>{doc}</style>
</head>
<body class="uds-root doc">
{body}
</body>
</html>
"""


def render_file(src_path: Path, out_path: Path, *, brand: str = "nopilot") -> Path:
    meta, body = render_body(Path(src_path).read_text(encoding="utf-8"), brand=brand)
    doc = hydrate_mod.render_document(
        body, title=str(meta.get("title", "Untitled")), theme=brand,
        base_href="../ui/base.css", theme_href=f"../ui/themes/theme-{brand}.css",
    )
    Path(out_path).write_text(doc, encoding="utf-8")
    return Path(out_path)


def render_docket_file(manifest_path: Path, out_path: Path, *, brand: str = "nopilot") -> Path:
    """Render a docket to a self-contained UDS-HTML document (servable as a docket entry)."""
    meta, body = render_docket(Path(manifest_path))
    Path(out_path).write_text(_self_contained(body, str(meta.get("title", "Proposition")), brand), encoding="utf-8")
    return Path(out_path)


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="studio-uds-html", description="markdown → UDS-HTML (ADR-006).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("render", help="render a flat ::: source")
    p1.add_argument("source")
    p1.add_argument("--out", required=True)
    p1.add_argument("--brand", default="nopilot")
    p2 = sub.add_parser("docket", help="render a docket manifest (self-contained)")
    p2.add_argument("manifest")
    p2.add_argument("--out", required=True)
    p2.add_argument("--brand", default="nopilot")
    args = ap.parse_args(argv)
    if args.cmd == "render":
        print("wrote", render_file(Path(args.source), Path(args.out), brand=args.brand))
    else:
        print("wrote", render_docket_file(Path(args.manifest), Path(args.out), brand=args.brand))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
