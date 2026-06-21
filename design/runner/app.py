"""Studio runner — a thin HTTP front for the design-studio render.

design-studio is a Claude Code plugin; its render is a Python library
(`studio.session` + `studio.render`), not a service. The madrigal pipeline (and
any other caller) needs an HTTP endpoint that turns markdown + a brand into a
branded PDF — the way `hermes` fronts the research agent. This service is that
front (Flightdeck npt-madrigal #110).

Flow per request:
  1. write the posted markdown to a temp session source,
  2. `studio.session.init(brand, name, source, format)` to lock the format,
  3. `studio.render.render(session, "patch", no_sync_guard=True)` to produce the PDF,
  4. copy the PDF into the artefact dir and return a hosted URL.

Run (with the design venv, which has the `studio` package installed):
  uvicorn runner.app:app --host 0.0.0.0 --port 8780
Deploy: jupiter, alongside hermes-webui / camouflex (deployment is out of scope
for this PR — this is the service code + contract).

Contract (matches nozero `lib/madrigal/studio-client.ts`):
  POST /render  {role_uid, kind: "cv"|"cover", markdown, brand?, format?}
                -> {ok: true, url}  |  {ok: false, error}
  GET  /artefacts/{name}            -> the rendered PDF
  GET  /health                      -> {ok, studio_importable}
Auth: Authorization: Bearer <STUDIO_RUNNER_TOKEN> on /render.
"""

from __future__ import annotations

import os
import shutil
import sys
import uuid
from pathlib import Path
from tempfile import mkdtemp

from fastapi import FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse

# The `studio` package lives in ../scripts (installed editable in the design
# venv). Add it to the path defensively so the runner works even if not installed.
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if _SCRIPTS.is_dir() and str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

ARTEFACT_DIR = Path(
    os.environ.get("STUDIO_RUNNER_ARTEFACT_DIR", "/tmp/studio-runner-artefacts")
)
PUBLIC_BASE = os.environ.get("STUDIO_RUNNER_PUBLIC_BASE", "").rstrip("/")
DEFAULT_BRAND = os.environ.get("STUDIO_RUNNER_DEFAULT_BRAND", "nopilot")
FORMAT_BY_KIND = {
    "cv": os.environ.get("STUDIO_RUNNER_CV_FORMAT", "report-pdf"),
    "cover": os.environ.get("STUDIO_RUNNER_COVER_FORMAT", "report-pdf"),
}

app = FastAPI(title="studio-runner", version="0.1.0")


def _studio_importable() -> bool:
    try:
        import studio.render  # noqa: F401
        import studio.session  # noqa: F401
    except Exception:
        return False
    return True


def _authorised(authorization: str | None) -> bool:
    token = os.environ.get("STUDIO_RUNNER_TOKEN", "").strip()
    if not token:
        return False  # refuse until a token is configured
    expected = f"Bearer {token}"
    return (authorization or "").strip() == expected


@app.get("/health")
def health() -> dict[str, object]:
    return {"ok": True, "service": "studio-runner", "studio_importable": _studio_importable()}


@app.get("/artefacts/{name}")
def artefact(name: str) -> FileResponse | JSONResponse:
    # Guard against path traversal; only serve flat .pdf files from the dir.
    safe = Path(name).name
    path = ARTEFACT_DIR / safe
    if safe != name or not path.is_file():
        return JSONResponse({"ok": False, "error": "not found"}, status_code=404)
    return FileResponse(path, media_type="application/pdf")


@app.post("/render")
async def render(
    request: Request, authorization: str | None = Header(default=None)
) -> JSONResponse:
    if not _authorised(authorization):
        status = 503 if not os.environ.get("STUDIO_RUNNER_TOKEN") else 401
        msg = "STUDIO_RUNNER_TOKEN not configured" if status == 503 else "unauthorized"
        return JSONResponse({"ok": False, "error": msg}, status_code=status)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid JSON"}, status_code=400)

    role_uid = str(body.get("role_uid") or "").strip()
    kind = str(body.get("kind") or "").strip()
    markdown = body.get("markdown")
    if not (role_uid and kind in FORMAT_BY_KIND and isinstance(markdown, str) and markdown):
        return JSONResponse(
            {"ok": False, "error": "role_uid, kind (cv|cover), markdown required"},
            status_code=422,
        )

    brand = str(body.get("brand") or DEFAULT_BRAND)
    fmt = str(body.get("format") or FORMAT_BY_KIND[kind])

    import studio.render as studio_render
    import studio.session as studio_session

    work = Path(mkdtemp(prefix="studio-runner-"))
    try:
        source = work / "source.md"
        source.write_text(markdown, encoding="utf-8")
        session_path = studio_session.init(
            brand, f"madrigal-{role_uid}-{kind}", source, fmt
        )
        outputs = studio_render.render(session_path, "patch", no_sync_guard=True)
        pdf = next(
            (p for p in outputs.values() if str(p).lower().endswith(".pdf")), None
        )
        if pdf is None or not Path(pdf).is_file():
            return JSONResponse(
                {"ok": False, "error": "render produced no PDF"}, status_code=500
            )

        ARTEFACT_DIR.mkdir(parents=True, exist_ok=True)
        name = f"{role_uid}-{kind}-{uuid.uuid4().hex[:8]}.pdf"
        shutil.copyfile(pdf, ARTEFACT_DIR / name)
        url = f"{PUBLIC_BASE}/artefacts/{name}" if PUBLIC_BASE else f"/artefacts/{name}"
        return JSONResponse({"ok": True, "url": url, "brand": brand, "format": fmt})
    except Exception as exc:  # render is best-effort; never 500-crash the worker
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
    finally:
        shutil.rmtree(work, ignore_errors=True)
