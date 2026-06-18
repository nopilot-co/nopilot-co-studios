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

CLI:  studio-gslide <manifest> [--out payload.json]            # dry-run
      studio-gslide <manifest> --execute --creds token.json    # live
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
    return {
        "ink": light.get("text", "#1C2022"),
        "muted": light.get("text-muted", "#6E747A"),
        "primary": light.get("primary", "#C3094A"),
        "active": light.get("active", "#FFC10E"),
        "on_active": light.get("on-active", "#1C2022"),
        "surface": light.get("surface", "#FFFFFF"),
        "paper": light.get("bg", "#F1F1F4"),
        "on_primary": light.get("on-primary", "#FFFFFF"),
        "display": display, "body": body, "mono": _GSLIDE_MONO,
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


def slide_specs(manifest_path: Path, *, brand: str = "nopilot", lines_per_slide: int = 6) -> tuple[str, list[dict]]:
    """Docket manifest → an ordered deck of plain slide specs (the IR)."""
    manifest_path = Path(manifest_path)
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


def _style(box_id: str, *, font: str, size: int, color: dict, bold: bool = False, align: str | None = None) -> list[dict]:
    reqs = [{"updateTextStyle": {"objectId": box_id, "textRange": {"type": "ALL"},
             "style": {"fontFamily": font, "fontSize": {"magnitude": size, "unit": "PT"},
                       "foregroundColor": {"opaqueColor": {"rgbColor": color}}, "bold": bold},
             "fields": "fontFamily,fontSize,foregroundColor,bold"}}]
    if align:
        reqs.append({"updateParagraphStyle": {"objectId": box_id, "textRange": {"type": "ALL"},
                     "style": {"alignment": align}, "fields": "alignment"}})
    return reqs


def _bg(slide_id: str, hex_color: str) -> dict:
    return {"updatePageProperties": {"objectId": slide_id,
            "pageProperties": {"pageBackgroundFill": {"solidFill": {"color": {"rgbColor": _rgb(hex_color)}}}},
            "fields": "pageBackgroundFill.solidFill.color"}}


def build_requests(manifest_path: Path, *, brand: str = "nopilot") -> tuple[str, list[dict]]:
    """IR → Slides API batchUpdate requests (cover, section, quote, content)."""
    title, deck = slide_specs(manifest_path, brand=brand)
    p = _palette(brand)
    reqs: list[dict] = []
    cx, cw = MARGIN, PAGE_W - 2 * MARGIN

    def add_text(slide_id: str, n: int, text: str, y: int, h: int, *, font, size, color, bold=False, align=None) -> None:
        box = f"{slide_id}_t{n}"
        reqs.append(_text_box(slide_id, box, cx, y, cw, h))
        reqs.append({"insertText": {"objectId": box, "text": text, "insertionIndex": 0}})
        reqs.extend(_style(box, font=font, size=size, color=color, bold=bold, align=align))

    for i, s in enumerate(deck):
        sid = f"slide{i:03d}"  # Slides object IDs must be >= 5 chars
        reqs.append({"createSlide": {"objectId": sid, "insertionIndex": i,
                     "slideLayoutReference": {"predefinedLayout": "BLANK"}}})
        kind = s["kind"]
        if kind == "cover":
            reqs.append(_bg(sid, p["surface"]))
            add_text(sid, 0, s["eyebrow"].upper(), 1_400_000, 360_000, font=p["mono"], size=12, color=_rgb(p["primary"]), align="CENTER")
            add_text(sid, 1, s["title"], 1_800_000, 1_500_000, font=p["display"], size=96, color=_rgb(p["ink"]), bold=True, align="CENTER")
            if s.get("standfirst"):
                add_text(sid, 2, s["standfirst"], 3_500_000, 1_200_000, font=p["display"], size=22, color=_rgb(p["ink"]), align="CENTER")
        elif kind == "section":
            reqs.append(_bg(sid, p["ink"]))            # dark colour block
            add_text(sid, 0, s["eyebrow"].upper(), 1_900_000, 360_000, font=p["mono"], size=12, color=_rgb(p["active"]))
            add_text(sid, 1, s["title"], 2_300_000, 1_600_000, font=p["display"], size=54, color=_rgb(p["surface"]), bold=True)
        elif kind == "quote":
            reqs.append(_bg(sid, p["paper"]))
            add_text(sid, 0, s["eyebrow"].upper(), 700_000, 320_000, font=p["mono"], size=11, color=_rgb(p["primary"]))
            add_text(sid, 1, "“" + s["quote"] + "”", 1_300_000, 3_000_000, font=p["display"], size=28, color=_rgb(p["ink"]), align="START")
        else:  # content
            reqs.append(_bg(sid, p["surface"]))
            add_text(sid, 0, s["eyebrow"].upper(), 520_000, 300_000, font=p["mono"], size=11, color=_rgb(p["primary"]))
            add_text(sid, 1, s["title"], 850_000, 760_000, font=p["display"], size=30, color=_rgb(p["ink"]), bold=True)
            if s["body"]:
                add_text(sid, 2, "\n\n".join(s["body"]), 1_750_000, PAGE_H - 1_750_000 - MARGIN,
                         font=p["body"], size=13, color=_rgb(p["ink"]))
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


def resolve_account(account: str, destination: str | None = None) -> tuple[str, str, str | None]:
    """account (+ optional destination) → (sa_key_path, drive_folder_id, impersonate)."""
    cfg = (load_delivery().get("accounts", {}) or {}).get(account)
    if not cfg:
        raise SystemExit(f"no delivery config for '{account}' — set STUDIOS_DELIVERY_CONFIG or ~/context/studios/delivery.yml")
    key = os.environ.get(cfg.get("credential_env", ""))
    if not key:
        raise SystemExit(f"credential env {cfg.get('credential_env')!r} is unset (point it at the SA key JSON)")
    dest = (cfg.get("destinations", {}) or {}).get(destination or cfg.get("default_destination"))
    if not dest:
        raise SystemExit(f"no destination {destination!r} for account '{account}'")
    return key, dest["drive_folder_id"], dest.get("impersonate") or cfg.get("impersonate")


# ----------------------------------------------------------------- live execution
def _services(creds_file: str, impersonate: str | None = None):
    from google.oauth2 import service_account  # lazy: only needed live
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(creds_file, scopes=_SCOPES)
    if impersonate:
        # Domain-wide delegation: act AS a Workspace user, so files are owned by
        # them (their quota) — lets a SA write to a My-Drive folder. Requires the
        # Workspace admin to authorize this SA's client ID for the scopes.
        creds = creds.with_subject(impersonate)
    return build("drive", "v3", credentials=creds), build("slides", "v1", credentials=creds)


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


def execute(manifest_path: Path, *, brand: str = "nopilot", creds_file: str,
            drive_folder_id: str | None = None, asset_name: str | None = None,
            presentation_id: str | None = None, impersonate: str | None = None) -> str:
    """Create (or update in place) the native deck via the Slides + Drive APIs using
    a **service account**. Places it in a Shared-Drive folder (optionally an
    ``asset_name`` subfolder), or updates ``presentation_id`` if given. Returns the URL.

    Requires: Slides + Drive APIs enabled on the SA's project, and the SA a member
    of the target Shared Drive. This is an account write — confirm first.
    """
    drive, slides = _services(creds_file, impersonate=impersonate)
    title, reqs = build_requests(manifest_path, brand=brand)

    if presentation_id:                                          # update in place (re-render)
        pid = presentation_id
        cur = slides.presentations().get(presentationId=pid, fields="slides(objectId)").execute().get("slides", [])
        batch = [{"deleteObject": {"objectId": s["objectId"]}} for s in cur] + reqs
    else:
        parent = drive_folder_id
        if parent and asset_name:
            parent = _ensure_subfolder(drive, parent, asset_name)
        if parent:                                               # create inside the Shared-Drive folder
            pid = drive.files().create(
                body={"name": title, "mimeType": "application/vnd.google-apps.presentation", "parents": [parent]},
                fields="id", supportsAllDrives=True).execute()["id"]
        else:                                                    # fallback: the SA's own Drive
            pid = slides.presentations().create(body={"title": title}).execute()["presentationId"]
        default = slides.presentations().get(presentationId=pid, fields="slides(objectId)").execute().get("slides", [])
        batch = reqs + [{"deleteObject": {"objectId": s["objectId"]}} for s in default]

    slides.presentations().batchUpdate(presentationId=pid, body={"requests": batch}).execute()
    return f"https://docs.google.com/presentation/d/{pid}/edit"


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="studio-gslide", description="Native Google Slides from a UDS docket (ADR-006).")
    ap.add_argument("manifest")
    ap.add_argument("--brand", default="nopilot")
    ap.add_argument("--out", help="write the dry-run payload JSON here")
    ap.add_argument("--execute", action="store_true", help="create/update the live deck")
    ap.add_argument("--account", help="delivery account (e.g. coh/npt) — resolves SA key + folder from the delivery config")
    ap.add_argument("--destination", help="named destination within the account (else its default)")
    ap.add_argument("--asset-name", help="subfolder under the destination for this asset")
    ap.add_argument("--creds", help="explicit service-account key JSON (overrides --account)")
    ap.add_argument("--folder", help="explicit Drive folder id (overrides --account)")
    ap.add_argument("--impersonate", help="Workspace user to act as (domain-wide delegation) — needed to write to a My-Drive folder")
    ap.add_argument("--presentation-id", help="update this deck in place instead of creating a new one")
    args = ap.parse_args(argv)
    if args.execute:
        creds, folder, impersonate = args.creds, args.folder, args.impersonate
        if args.account and not creds:
            creds, folder, cfg_imp = resolve_account(args.account, args.destination)
            impersonate = impersonate or cfg_imp
        if not creds:
            ap.error("--execute needs --account (configured) or --creds")
        print(execute(Path(args.manifest), brand=args.brand, creds_file=creds,
                       drive_folder_id=folder, asset_name=args.asset_name,
                       presentation_id=args.presentation_id, impersonate=impersonate))
        return 0
    pl = payload(Path(args.manifest), brand=args.brand)
    if args.out:
        Path(args.out).write_text(json.dumps(pl, indent=2), encoding="utf-8")
        print(f"wrote {args.out} — {pl['slides']} slides, {len(pl['requests'])} requests")
    else:
        print(json.dumps(pl, indent=2)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
