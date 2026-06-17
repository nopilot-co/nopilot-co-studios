"""markdown → UDS-HTML mapper (ADR-006 Slice 2/4 — the inversion).

The single `:::` source (the studio's universal content form) is mapped to the
**UDS application-UI archetypes** (``uds/ui/base.css`` classes) and wrapped by
``studio.hydrate.render_document`` into the HTML *composition primary*. The same
source also feeds the deck/gslide serialiser (``studio.pptx_render``) — one source,
parallel renders.

This is deliberately a *small, explicit* mapper for the proposition vocabulary
(``cover/hero``, sections, ``stat-panel``, ``pullquote``, ``callout-panel``,
``process``, table, ``cta``) — each markdown construct has one home in the register
(``uds/archetypes.yml`` markdown_mapping). It maps to base.css markup verbatim
(BEM ``.uds-*`` / ``__`` elements), so the page is hydrated by a brand theme with
no per-asset styling.
"""

from __future__ import annotations

import re
from html import escape as _esc
from pathlib import Path
from typing import Any

import yaml

from . import hydrate as hydrate_mod

_FENCE_RE = re.compile(r"^:::+\s*([a-z][a-z0-9-]*)\s*$")
_FENCE_END = re.compile(r"^:::+\s*$")
_HEAD_RE = re.compile(r"^(#{1,4})\s+(.*)$")


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


def _blocks(body: str) -> list[tuple[str, Any]]:
    """Tokenise the body into ordered blocks: ('h', level, text) · ('p', text) ·
    ('fence', name, inner) · ('table', rows)."""
    lines = body.splitlines()
    out: list[tuple[str, Any]] = []
    i, n = 0, len(lines)
    para: list[str] = []

    def flush_para() -> None:
        if para:
            out.append(("p", " ".join(s.strip() for s in para).strip()))
            para.clear()

    while i < n:
        line = lines[i]
        if fence := _FENCE_RE.match(line.strip()):
            flush_para()
            name, inner, i = fence.group(1), [], i + 1
            while i < n and not _FENCE_END.match(lines[i].strip()):
                inner.append(lines[i])
                i += 1
            i += 1  # consume closing :::
            out.append(("fence", name, "\n".join(inner)))
        elif line.lstrip().startswith("|") and "|" in line:
            flush_para()
            rows, i = [], i
            while i < n and lines[i].lstrip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            out.append(("table", rows))
        elif h := _HEAD_RE.match(line):
            flush_para()
            out.append(("h", len(h.group(1)), h.group(2).strip()))
            i += 1
        elif not line.strip():
            flush_para()
            i += 1
        else:
            para.append(line)
            i += 1
    flush_para()
    return out


# ----------------------------------------------------------------- emit
def _inline(text: str) -> str:
    """Minimal inline markdown → HTML: **bold** / *italic* (escaped first)."""
    t = _esc(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", t)
    return t


def _stat_grid(inner: str) -> str:
    items = yaml.safe_load(inner) or []
    cells = []
    for it in items:
        value = _esc(str(it.get("value", "")))
        label = _esc(str(it.get("label", "")))
        delta = it.get("delta")
        d = f'<span class="uds-stat__delta">{_esc(str(delta))}</span>' if delta else ""
        cells.append(
            f'<div class="uds-stat"><span class="uds-stat__value">{value}</span>'
            f'<span class="uds-stat__label">{label}</span>{d}</div>'
        )
    cols = min(len(cells), 4) or 1
    return f'<section class="uds-grid" data-cols="{cols}">{"".join(cells)}</section>'


def _pullquote(inner: str) -> str:
    lines = [ln.strip() for ln in inner.strip().splitlines() if ln.strip()]
    attribution = ""
    if lines and re.match(r"^[—-]\s+", lines[-1]):
        attribution = re.sub(r"^[—-]\s+", "", lines.pop())
    quote = " ".join(lines)
    attr = (
        f'<figcaption class="uds-pull-quote__attribution">{_inline(attribution)}</figcaption>'
        if attribution else ""
    )
    return f'<figure class="uds-pull-quote"><p>{_inline(quote)}</p>{attr}</figure>'


def _callout(inner: str) -> str:
    blk = _blocks(inner)
    parts = []
    for b in blk:
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
            f'<div class="uds-card"><div class="uds-card__body">'
            f'<p class="uds-eyebrow">{idx:02d}</p>'
            f'<h3 class="uds-card__title">{_inline(title)}</h3>{excerpt}</div></div>'
        )
    cols = min(len(cells), 4) or 1
    return f'<section class="uds-grid" data-cols="{cols}">{"".join(cells)}</section>'


def _cta(inner: str) -> str:
    text = " ".join(s.strip() for s in inner.strip().splitlines())
    return (
        '<aside class="uds-banner uds-banner--promo">'
        f'<p>{_inline(text)}</p>'
        '<a class="uds-button uds-button--primary" href="#book">Book a paid Lunch &amp; Learn</a>'
        "</aside>"
    )


def _table(rows: list[str]) -> str:
    def cells(r: str) -> list[str]:
        return [c.strip() for c in r.strip().strip("|").split("|")]

    if len(rows) < 2:
        return ""
    head = cells(rows[0])
    body = [cells(r) for r in rows[2:]]  # rows[1] is the --- separator
    thead = "".join(f"<th>{_inline(c)}</th>" for c in head)
    tbody = "".join(
        "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in body
    )
    return f'<table class="uds-table"><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>'


_FENCE = {
    "stat-panel": _stat_grid,
    "pullquote": _pullquote,
    "callout-panel": _callout,
    "process": _process,
    "cta": _cta,
}


def render_body(source_md: str) -> tuple[dict[str, Any], str]:
    """Map a `:::` source to a UDS-HTML body (hero + detail body)."""
    meta, body = split_frontmatter(source_md)
    blocks = _blocks(body)

    # The leading H1 + the paragraph(s) before the first section become the hero.
    hero_title = meta.get("title", "")
    standfirst: list[str] = []
    rest_start = 0
    for idx, b in enumerate(blocks):
        if b[0] == "h" and b[1] == 1 and not hero_title:
            hero_title = b[2]
        elif b[0] == "h" and b[1] == 1:
            continue
        elif b[0] == "p" and not any(x[0] == "h" and x[1] == 2 for x in blocks[:idx]):
            standfirst.append(b[1])
        else:
            rest_start = idx
            break
    else:
        rest_start = len(blocks)

    eyebrow = _esc(str(meta.get("brand", "")).upper()) + " · PROPOSITION" if meta.get("brand") else ""
    hero = ['<header class="uds-hero">']
    if eyebrow:
        hero.append(f'<p class="uds-eyebrow">{eyebrow}</p>')
    hero.append(f'<h1 class="uds-hero__title">{_inline(hero_title)}</h1>')
    if standfirst:
        hero.append(f'<p class="uds-hero__standfirst">{_inline(" ".join(standfirst))}</p>')
    hero.append("</header>")

    body_parts: list[str] = []
    for b in blocks[rest_start:]:
        if b[0] == "h":
            body_parts.append(f"<h{b[1]}>{_inline(b[2])}</h{b[1]}>")
        elif b[0] == "p":
            body_parts.append(f"<p>{_inline(b[1])}</p>")
        elif b[0] == "table":
            body_parts.append(_table(b[1]))
        elif b[0] == "fence":
            fn = _FENCE.get(b[1])
            body_parts.append(fn(b[2]) if fn else "")

    html = (
        '<article class="uds-detail">\n'
        + "".join(hero) + "\n"
        + '<div class="uds-detail__body">\n' + "\n".join(body_parts) + "\n</div>\n"
        + "</article>"
    )
    return meta, html


def render_file(src_path: Path, out_path: Path, *, brand: str = "nopilot", mode: str = "light") -> Path:
    """Render a `:::` source to a full hydrated UDS-HTML document."""
    meta, body = render_body(Path(src_path).read_text(encoding="utf-8"))
    # out lives in design/uds/examples/; base.css + themes live under design/uds/ui/.
    doc = hydrate_mod.render_document(
        body,
        title=str(meta.get("title", "Untitled")),
        theme=brand,
        mode=mode,
        base_href="../ui/base.css",
        theme_href=f"../ui/themes/theme-{brand}.css",
    )
    Path(out_path).write_text(doc, encoding="utf-8")
    return Path(out_path)


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="studio-uds-html", description="markdown → UDS-HTML (ADR-006).")
    ap.add_argument("source")
    ap.add_argument("--out", required=True)
    ap.add_argument("--brand", default="nopilot")
    args = ap.parse_args(argv)
    p = render_file(Path(args.source), Path(args.out), brand=args.brand)
    print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
