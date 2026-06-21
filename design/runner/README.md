# studio-runner

A thin HTTP front for the design-studio render (Markdown → branded PDF via
Quarto + Typst). It wraps the `studio` Python library (`studio.session.init` +
`studio.render.render`) so non-Python callers — notably the **madrigal** pipeline
in nozero — can request a rendered docket over HTTP.

Tracked as Flightdeck **npt-madrigal #110**. Counterpart client:
`lib/madrigal/studio-client.ts` in nozero.

## Contract

```
POST /render
  Authorization: Bearer <STUDIO_RUNNER_TOKEN>
  { "role_uid": "...", "kind": "cv" | "cover", "markdown": "...", "brand"?: "...", "format"?: "..." }
  -> 200 { "ok": true,  "url": "<hosted pdf>", "brand": "...", "format": "..." }
  -> 4xx/5xx { "ok": false, "error": "..." }

GET /artefacts/{name}   -> the rendered PDF (application/pdf)
GET /health             -> { "ok": true, "studio_importable": true|false }
```

`kind` maps to a format slug (default `report-pdf` for both — design-studio has
no dedicated `cv` / `letter` format yet; add one and set the env overrides below).

## Run

Use the design venv (it has the `studio` package installed editable):

```bash
cd design
.venv/bin/pip install -e '.[runner]'        # fastapi + uvicorn
.venv/bin/uvicorn runner.app:app --host 0.0.0.0 --port 8780
```

Requires `quarto` (>=1.6) and `typst` on PATH, and the brand's `_brand.yml` under
`~/context/studios/brand/<brand>/`.

## Environment

| Var | Default | Purpose |
|---|---|---|
| `STUDIO_RUNNER_TOKEN` | — (required) | Bearer token; `/render` returns 503 until set |
| `STUDIO_RUNNER_PUBLIC_BASE` | "" | Origin used to build returned artefact URLs (e.g. `http://jupiter:8780`) |
| `STUDIO_RUNNER_ARTEFACT_DIR` | `/tmp/studio-runner-artefacts` | Where rendered PDFs are served from |
| `STUDIO_RUNNER_DEFAULT_BRAND` | `nopilot` | Brand slug when the request omits one |
| `STUDIO_RUNNER_CV_FORMAT` | `report-pdf` | Format slug for `kind=cv` |
| `STUDIO_RUNNER_COVER_FORMAT` | `report-pdf` | Format slug for `kind=cover` |

## Deploy

jupiter, alongside hermes-webui / camouflex. Deployment (systemd/launchd unit +
reverse proxy) is **out of scope for the service code in this PR** — see #110.

## Not yet done / seams

- No dedicated CV / cover-letter **format** in design-studio (uses `report-pdf`).
- Artefacts are served from a local dir; for production prefer object storage or
  a grant-scoped path.
- No live render exercised in CI here — needs quarto/typst + a brand on the host.
