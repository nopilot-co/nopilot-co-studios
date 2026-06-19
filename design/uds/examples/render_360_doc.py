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


CSS = """body{font-family:'Roboto',sans-serif;font-weight:300;font-size:10pt;color:#15181E;line-height:1.45;}
h1{font-family:'IBM Plex Serif',serif;font-weight:600;font-size:22pt;margin:26pt 0 6pt;}
h1.doctitle{font-size:34pt;margin-top:0;}
h2{font-family:'IBM Plex Serif',serif;font-weight:600;font-size:16pt;margin:18pt 0 4pt;}
h3{font-family:'IBM Plex Serif',serif;font-weight:600;font-size:12pt;margin:10pt 0 2pt;}
p{margin:6pt 0;}
li{margin:3pt 0;}
blockquote{font-family:'IBM Plex Serif',serif;font-style:italic;font-size:13pt;margin:12pt 0;color:#2C333D;}
.pullquote{font-family:'IBM Plex Serif',serif;font-size:12pt;}
.callout{border-left:3px solid #3B4FE0;padding-left:10pt;}
.cap{font-size:8.5pt;color:#5B6470;margin-top:8pt;}
table{border-collapse:collapse;font-size:9pt;margin:8pt 0;width:100%;}
th,td{border:1px solid #DCE0E6;padding:4pt 6pt;text-align:left;vertical-align:top;}
th{font-weight:600;background:#F1F1F4;}
img{max-width:100%;}"""


def main():
    drive, _ = gslide._services(TOKEN)
    manifest = yaml.safe_load(MANI.read_text(encoding="utf-8"))
    content_dir = MANI.parent.parent

    img_url, fids = {}, []                            # rasterise + upload each diagram once
    for svgs in VIZ_SVG.values():
        for svg in svgs:
            if svg in img_url:
                continue
            p = DOCKET / "content" / "viz" / svg
            if not p.exists():
                continue
            png, _aspect = gslide.rasterize_svg(p)
            fid, url = gslide.upload_drive_image(drive, png, f"360doc-{svg}.png")
            img_url[svg], _ = url, fids.append(fid)
            print(f"  rasterised {svg}")

    body = ['<h1 class="doctitle">360° — A Partnership Proposition</h1>',
            '<p>A partnership proposition — Context Operating Systems for established businesses.</p>']
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
        for svg in VIZ_SVG.get(tid, []):
            if svg in img_url:
                body.append(f'<p><img src="{img_url[svg]}" width="640"></p>')
    if embeds:
        body.append("<h2>Related documents</h2><ul>" + "".join(f"<li>{esc(l)} — docket: {esc(i)}</li>" for i, l in embeds) + "</ul>")

    doc_html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(body)}</body></html>"
    Path("design/uds/examples/_360-doc.html").write_text(doc_html, encoding="utf-8")
    media = MediaIoBaseUpload(io.BytesIO(doc_html.encode("utf-8")), mimetype="text/html", resumable=False)
    f = drive.files().create(
        body={"name": "360 — A Partnership Proposition", "mimeType": "application/vnd.google-apps.document"},
        media_body=media, fields="id,webViewLink").execute()
    print("DOC:", f.get("webViewLink"))
    print("(temp figure images left in Drive so the Doc keeps them; ids:", " ".join(fids), ")")


if __name__ == "__main__":
    main()
