"""360 proposition → a single plain Google DOC (white background, NPT UDS fonts).

Roboto Light 10pt reading body; IBM Plex Serif for section + page titles; NO eyebrows;
one flowing readable document. Tables come from the docket CSVs; diagrams are the docket
SVGs (rasterised). Built as clean HTML and uploaded to Drive, which converts HTML → a native
Google Doc. Run:

  NPT_GSLIDE_OAUTH_TOKEN=~/context/studios/npt-oauth-token.json \
  python design/uds/examples/render_360_doc.py
"""
import os
import io
import re
import sys
import html as _html
from pathlib import Path

sys.path.insert(0, "design/scripts")
import yaml  # noqa: E402
from googleapiclient.http import MediaIoBaseUpload  # noqa: E402
from studio import gslide  # noqa: E402

DOCKET = Path(os.environ.get("DOCKET_360", str(Path.home() / "Projects/aqua/nopilot-co-www/assets/dockets/360-gtm-proposition/source")))
MANI = DOCKET / "content" / "manifest.yaml"
TOKEN = os.environ["NPT_GSLIDE_OAUTH_TOKEN"]

# Diagrams per topic — the docket's own designed SVGs (rasterised → embedded image).
VIZ_SVG = {
    "commercials": ["financials.svg"],
    "gtm": ["economics.svg"],
    "tech": ["dartboard.svg"],
    "structure": ["swimlanes.svg", "lean-core.svg"],
    "pillars": ["pillars.svg"],
    "model": ["model.svg"],
}
DIST = DOCKET.parent / "dist" / "360-proposition.html"   # the canonical render — has every chart inline


def extract_dist_charts(drive, skip_topics):
    """Screenshot every chart/diagram in the canonical dist render that isn't already covered by a
    standalone viz SVG, mapped to its topic id (so the landscape hype-cycle + name-scoring chart get in)."""
    out = {}
    if not DIST.exists():
        return out
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
        pg.goto(f"file://{DIST}", wait_until="networkidle")
        for i, el in enumerate(pg.query_selector_all("svg")):
            box = el.bounding_box()
            if not box or box["width"] < 220 or box["height"] < 110:        # skip icons / marks
                continue
            tid = el.evaluate("e => { const n = e.closest('[id]'); return n ? n.id : '' }")
            if not tid or tid in skip_topics:                                # already have a figure for this topic
                continue
            try:
                png = el.screenshot(omit_background=True)
            except Exception:  # noqa: BLE001
                continue
            _fid, url = gslide.upload_drive_image(drive, png, f"360doc-chart-{i}.png")
            out.setdefault(tid, []).append(url)
            print(f"  captured chart for '{tid}' from dist")
        b.close()
    return out


def esc(s):
    return _html.escape(str(s))


def md(s):                                            # **bold** → <b>; drop stray markers
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc(s))
    return s.replace("**", "")


def lines_html(lines):
    out, in_ul = [], False
    for ln in lines:
        if ln.startswith("• "):
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append(f"<li>{md(ln[2:])}</li>"); continue
        if in_ul:
            out.append("</ul>"); in_ul = False
        if ln.startswith("§ "):
            out.append(f"<h3>{md(ln[2:])}</h3>")
        elif ln.startswith("❝ "):
            out.append(f"<blockquote>{md(ln[2:])}</blockquote>")
        elif ln.startswith("‼ "):
            out.append(f'<p class="callout">{md(ln[2:])}</p>')
        elif ln.startswith("❞ "):
            out.append(f'<p class="pullquote">{md(ln[2:].replace(" -- ", " — "))}</p>')
        else:
            out.append(f"<p>{md(ln)}</p>")
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


def table_html(rows):
    if not rows:
        return ""
    head = "<tr>" + "".join(f"<th>{esc(c)}</th>" for c in rows[0]) + "</tr>"
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
    return f"<table>{head}{body}</table>"


# 360 brand palette — indigo primary, terracotta secondary (the colour-split applied to headings).
INK, INDIGO, TERRA, MUTED = "#15181E", "#3B4FE0", "#C2410C", "#5B6470"
CSS = f"""body{{font-family:'Roboto',sans-serif;font-weight:300;font-size:10pt;color:{INK};line-height:1.5;}}
h1{{font-family:'IBM Plex Serif',serif;font-weight:600;font-size:22pt;color:{INDIGO};margin:32pt 0 10pt;page-break-after:avoid;}}
h2{{font-family:'IBM Plex Serif',serif;font-weight:600;font-size:16pt;color:{INDIGO};margin:24pt 0 8pt;page-break-after:avoid;}}
h3{{font-family:'IBM Plex Serif',serif;font-weight:600;font-size:12pt;color:{TERRA};margin:16pt 0 6pt;page-break-after:avoid;}}
.cover{{margin-top:150pt;}}
.cover-mark{{font-family:'IBM Plex Serif',serif;font-weight:600;font-size:84pt;color:{INDIGO};line-height:1;}}
.cover-title{{font-family:'IBM Plex Serif',serif;font-weight:600;font-size:30pt;color:{INK};margin:8pt 0 0;}}
.cover-sub{{font-size:13pt;color:{MUTED};margin:16pt 0 0;}}
.cover-meta{{font-size:10pt;color:{MUTED};margin:54pt 0 380pt;}}
p{{margin:0 0 11pt;orphans:2;widows:2;}}
li{{margin:0 0 8pt;}}
ul{{margin:6pt 0 14pt;}}
blockquote{{font-family:'IBM Plex Serif',serif;font-style:italic;font-size:13pt;margin:16pt 0;color:#2C333D;page-break-inside:avoid;}}
.pullquote{{font-family:'IBM Plex Serif',serif;font-size:12pt;color:{INDIGO};margin:0 0 11pt;}}
.callout{{border-left:3px solid {INDIGO};padding-left:12pt;margin:14pt 0;page-break-inside:avoid;}}
.cap{{font-size:8.5pt;color:{MUTED};margin:12pt 0 2pt;}}
table{{border-collapse:collapse;font-size:9pt;margin:10pt 0 18pt;width:100%;page-break-inside:avoid;}}
th,td{{border:1px solid #DCE0E6;padding:5pt 7pt;text-align:left;vertical-align:top;}}
th{{font-weight:600;background:#F1F1F4;color:{INK};}}
figure{{margin:14pt 0;page-break-inside:avoid;}}
img{{max-width:100%;}}"""


def main():
    drive, _ = gslide._services(TOKEN)
    manifest = yaml.safe_load(MANI.read_text(encoding="utf-8"))
    content_dir = MANI.parent.parent

    charts, seen = {}, {}                             # topic id → [image urls]; the 7 standalone figures…
    for tid, svgs in VIZ_SVG.items():
        for svg in svgs:
            p = DOCKET / "content" / "viz" / svg
            if not p.exists():
                continue
            if svg not in seen:
                png, _a = gslide.rasterize_svg(p)
                _fid, seen[svg] = gslide.upload_drive_image(drive, png, f"360doc-{svg}.png")
                print(f"  rasterised {svg}")
            charts.setdefault(tid, []).append(seen[svg])
    for tid, urls in extract_dist_charts(drive, set(VIZ_SVG)).items():   # …plus every other chart from the dist render
        charts.setdefault(tid, []).extend(urls)

    body = ['<div class="cover">'
            '<div class="cover-mark">360°</div>'
            '<div class="cover-title">A Partnership Proposition</div>'
            '<div class="cover-sub">Context operating systems for established businesses</div>'
            '<div class="cover-meta">Prepared for Dan · June 2026 · Private &amp; confidential</div>'
            '</div>']
    embeds = []
    for t in manifest.get("topics", []):
        tid, tp, title = t.get("id"), t.get("type", "content"), (t.get("title") or "").strip()
        if tp == "index" or tid == "cover":
            continue
        if tp == "embed":
            embeds.append((tid, title)); continue
        if tp == "interstitial" or not t.get("section_md"):
            if title:
                body.append(f"<h1>{esc(title)}</h1>")
            continue
        body.append(f"<h2>{esc(title)}</h2>")
        lines, _q = gslide._topic_body(content_dir, t)
        body.append(lines_html(lines))
        for tbl in (t.get("tables") or []):
            rows = gslide._csv_table(content_dir, tbl, max_cols=8)
            if rows:
                cap = tbl.get("caption", "")
                body.append((f'<p class="cap">{esc(cap)}</p>' if cap else "") + table_html(rows))
        for url in charts.get(tid, []):
            body.append(f'<figure><img src="{url}" width="640"></figure>')
    if embeds:
        body.append("<h2>Related documents</h2><ul>" + "".join(f"<li>{esc(l)} — docket: {esc(i)}</li>" for i, l in embeds) + "</ul>")

    doc_html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(body)}</body></html>"
    Path("design/uds/examples/_360-doc.html").write_text(doc_html, encoding="utf-8")
    media = MediaIoBaseUpload(io.BytesIO(doc_html.encode("utf-8")), mimetype="text/html", resumable=False)
    f = drive.files().create(
        body={"name": os.environ.get("DOC_NAME", "360 — A Partnership Proposition"), "mimeType": "application/vnd.google-apps.document"},
        media_body=media, fields="id,webViewLink").execute()
    print("DOC:", f.get("webViewLink"))


if __name__ == "__main__":
    main()
