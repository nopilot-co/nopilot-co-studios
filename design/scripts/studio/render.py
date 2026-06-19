"""Render dispatch: layout-keyed engine selection (#99).

`render(session_path, bump_kind)` reads the resolved format contract, looks up
its declared engine in ``_ENGINES``, and dispatches. Engines are pure functions
``(session_path, resolved, state, version) -> {sfmt: dest_path}``. Adding a new
layout means adding an engine + template; nothing else here changes.

Engines:
- ``linear-engine`` — the existing Quarto doc pipeline (HTML/PDF/RevealJS).
- ``pptx-engine``  — the native python-pptx builder (slice 4b / #19).
- ``frame-engine`` — fills the canonical two-axis showcase template
  (``templates/showcase/showcase.html``). Brand-token + content fill is the
  next slice (#100); this PR lands the dispatch so the contract is honoured.

Note: the Quarto build dir must NOT be dot-prefixed. Quarto (≥1.9) skips hidden
directories when inlining assets, so rendering HTML in a `.tmp/` dir silently
defeats `embed-resources: true` and leaves an orphaned `_files/` sidecar
(issue #1). Hence `_render/`.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from html import escape as _html_escape
from pathlib import Path
from typing import Any, Callable

import yaml
from jinja2 import Template

from . import PLUGIN_ROOT, TEMPLATES
from . import brand as brand_mod
from . import charts as charts_mod
from . import components as components_mod
from . import diagrams as diagrams_mod
from . import formats as formats_mod
from . import frameworks as frameworks_mod
from . import frame_template as frame_template_mod
from . import metacontent
from . import pptx_render as pptx_mod
from . import session as session_mod
from . import sync as sync_mod
from . import tokens as tokens_mod
from . import viz_data as viz_data_mod

# Quarto format names by our short names
_FORMAT_MAP = {
    "pdf": "typst",  # use Typst engine, not LaTeX
    "pptx": "pptx",
    "html": "html",
    "revealjs": "revealjs",
}

_EXT = {
    "pdf": ".pdf",
    "pptx": ".pptx",
    "html": ".html",
    "revealjs": ".html",  # RevealJS outputs HTML
}

_VER_LABEL_RE = re.compile(r"-v\d+\.\d+\.\d+$")


def _strip_version_label(stem: str) -> str:
    """Remove a trailing -v<semver> label so the render version isn't compounded
    onto a content filename that already carries one (e.g. foo-v1.0.0 -> foo)."""
    return _VER_LABEL_RE.sub("", stem)


def _out_stem(state: dict[str, Any]) -> str:
    return _strip_version_label(
        state.get("source_filename", "source.md").rsplit(".", 1)[0] or "source"
    )


# Engine type — every engine takes the same inputs and returns the same shape.
Engine = Callable[[Path, dict[str, Any], dict[str, Any], str], dict[str, Path]]


def render(
    session_path: Path,
    bump_kind: str,
    *,
    no_sync_guard: bool = False,
    sync_server: str | None = None,
) -> dict[str, Path]:
    """Render the session's locked format. Dispatches by resolved engine name.

    Raises ``RuntimeError`` if the session has no locked format, the format is
    not renderable, or the resolved engine is unknown.
    """
    sync_mod.check_render_guard(
        session_path, sync_server, no_sync_guard=no_sync_guard
    )
    production_uuid = sync_mod.ensure_production_uuid(session_path)
    state = session_mod.read_state(session_path)

    # The session locks exactly one format slug; the export it produces is fixed
    # by that slug, never chosen ad hoc at render time.
    fmt_slug = state.get("format")
    if not fmt_slug:
        raise RuntimeError(
            "session has no locked format. Re-create it with "
            "`studio session init --format <slug> ...` (see `studio formats list`)."
        )
    # Fail-closed (#101): the contract the session will build against must be
    # schema-valid before we touch any rendering pipeline. A local lock
    # (session/contract.lock.yml) overrides the global resolve.
    resolved, built_against = formats_mod.resolve_for_session(fmt_slug, session_path)
    schema_errors = formats_mod.validate_resolved(resolved)
    if schema_errors:
        raise RuntimeError(
            f"format '{fmt_slug}' resolved contract failed schema validation:\n  "
            + "\n  ".join(schema_errors)
            + "\n  (fix the slug / layer / local lock; render refuses fail-closed)"
        )
    if not formats_mod.is_renderable(resolved):
        raise RuntimeError(
            f"format '{fmt_slug}' (export '{resolved.get('export')}') is not "
            f"renderable by the studio pipeline yet — no engine mapping. "
            f"Pick a renderable format (pdf, html, pptx, revealjs)."
        )

    engine_name = (resolved.get("render") or {}).get("engine")
    engine = _ENGINES.get(engine_name)
    if engine is None:
        raise RuntimeError(
            f"unknown render engine '{engine_name}' on format '{fmt_slug}'. "
            f"Known engines: {sorted(_ENGINES)}. Add a registry entry in "
            f"render.py and a layout/<layout>.yml declaration."
        )

    new_version = session_mod.next_version(session_path, bump_kind)
    outputs = engine(session_path, resolved, state, new_version)

    # Emit normalised CSV sidecars for every viz block in the source — for ALL
    # exports (independent of the engine), and even for viz types without a
    # renderer yet. Never crashes the render; the manifest is persisted into
    # version.json so a data editor (nopilot.co) can find the data behind a viz.
    try:
        data_manifest = viz_data_mod.scan_session(session_path, state)
    except Exception as e:  # noqa: BLE001 — sidecars must never fail a render
        print(f"⚠ viz_data: CSV sidecar pass failed ({e})", file=sys.stderr)
        data_manifest = []

    sfmt = formats_mod.studio_format(resolved)
    for fmt, out_path in outputs.items():
        if fmt in ("html", "revealjs"):
            sync_mod.stamp_html_production_uuid(out_path, production_uuid)
    session_mod.record_render(
        session_path,
        new_version,
        [sfmt],
        outputs,
        built_against=built_against,
        data=data_manifest,
    )
    sync_mod.prune_rendered_html(session_path)
    return outputs


# ---------------------------------------------------------------- pptx-engine


def _engine_pptx(
    session_path: Path, resolved: dict[str, Any], state: dict[str, Any], version: str
) -> dict[str, Path]:
    """Native python-pptx renderer (slice 4b). No Quarto involved."""
    slug = state["brand"]
    dest = session_path / "outputs" / f"{_out_stem(state)}.v{version}.pptx"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tok = tokens_mod.resolve(slug, state.get("design_system"))
    body = metacontent.strip(session_path / "inputs" / "source.md")
    pptx_mod.build_pptx(body, tok, dest)
    return {"pptx": dest}


# ---------------------------------------------------------------- uds-pdf-engine


def _engine_uds_pdf(
    session_path: Path, resolved: dict[str, Any], state: dict[str, Any], version: str
) -> dict[str, Path]:
    """UDS-HTML → PDF print engine (#123). Prints the UDS reading document via
    Chromium with a native running header/footer — no Quarto. Playwright is an
    optional dep, imported lazily so this module still loads without it."""
    from . import uds_pdf as uds_pdf_mod

    slug = state["brand"]
    dest = session_path / "outputs" / f"{_out_stem(state)}.v{version}.pdf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Meta-content strip first (issue #11): no `nopilot:` region or front-matter
    # may leak into the client-facing PDF, so compose from a cleaned source.
    body = metacontent.strip(session_path / "inputs" / "source.md")
    tmp_src = session_path / "_uds_src.md"
    tmp_src.write_text(body, encoding="utf-8")
    try:
        orientation = (resolved.get("render") or {}).get("orientation") or "landscape"
        uds_pdf_mod.render(tmp_src, dest, brand=slug, orientation=orientation)
    finally:
        tmp_src.unlink(missing_ok=True)
    return {"pdf": dest}


# ---------------------------------------------------------------- linear-engine


def _engine_linear(
    session_path: Path, resolved: dict[str, Any], state: dict[str, Any], version: str
) -> dict[str, Path]:
    """The Quarto doc pipeline for HTML/PDF/RevealJS."""
    if detect_quarto() is None:
        raise RuntimeError(
            "quarto not found on PATH.\n"
            "  Install: brew install --cask quarto  (or download from https://quarto.org/docs/get-started/)\n"
            "  Then re-run: studio render ..."
        )

    slug = state["brand"]
    sfmt = formats_mod.studio_format(resolved)
    brand_yml = brand_mod.brand_yml_path(slug)
    if not brand_yml.exists():
        raise FileNotFoundError(f"brand spec missing: {brand_yml}")

    tmp = session_path / "_render"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    # Copy source and brand assets into the tmp project. The source is run through
    # the meta-content strip first (issue #11): front-matter + every `nopilot:`
    # region is removed BEFORE Quarto sees it, on every export path — HTML comments
    # are not self-hiding on the HTML/RevealJS path, so this is mandatory.
    source_md = session_path / "inputs" / "source.md"
    # Preprocess order: strip meta-content (issue #11), then expand structured
    # `::: <diagram>` blocks for THIS export — Mermaid for HTML, fletcher for PDF
    # (slice 4a). `sfmt` is the locked studio format; `tok` the resolved tokens.
    tok = tokens_mod.resolve(slug, state.get("design_system"))
    body = metacontent.strip(source_md)
    body = diagrams_mod.expand(body, sfmt, tok)
    # Charts write a brand-styled SVG into the render dir and reference it (#20).
    body = charts_mod.expand(body, sfmt, tok, tmp)
    # Frameworks (bullseye/matrix/funnel/heatmap/swimlane/decision-tree) — same
    # SVG-into-render-dir pattern, expanded after charts (Phase 2 / #121).
    body = frameworks_mod.expand(body, sfmt, tok, tmp)
    # Lift the leading title block onto a cover (#38): the first H1 becomes the
    # cover title and an immediately-following precis/lead becomes the standfirst,
    # both removed from the body so they aren't repeated.
    cover_title, cover_standfirst, body = _extract_cover(body)
    (tmp / "source.md").write_text(body, encoding="utf-8")
    shutil.copy2(brand_yml, tmp / "_brand.yml")

    brand_root = brand_mod.brand_root(slug)
    assets_src = brand_root / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, tmp / "assets")
    pptx_ref = brand_root / "reference.pptx"
    if pptx_ref.exists():
        shutil.copy2(pptx_ref, tmp / "reference.pptx")

    # Materialize the component library (slice 2): static CSS/Typst component
    # definitions + a per-brand design-token block they consume, plus the Lua
    # bridge that maps `::: <class>` divs to Typst component calls. This is what
    # turns a flat brand render into a designed one — same components, re-skinned
    # per brand via the generated token block.
    comp_dir = TEMPLATES / "components"
    # HTML: the :root token block + static component rules (one inlined file).
    (tmp / "_components.css").write_text(
        components_mod.css_root(tok) + (comp_dir / "components.css").read_text(),
        encoding="utf-8",
    )
    shutil.copy2(comp_dir / "components.lua", tmp / "components.lua")

    # Typst preamble: the token dict (#let ds) + component functions (#let c_*),
    # then the document-chrome wrapper (issue #38). It MUST be injected via the
    # template's include-before-body TEXT so the bindings land in the body's
    # top-level scope — a file include / include-in-header gets wrapped in a
    # #block that scopes the #let definitions away, so the Lua-injected
    # `#c_<class>[ ... ]` calls can't see them (found via spike). `#show:
    # doc_chrome` then wraps the whole body for running header/footer, measure,
    # and brand-spent headings. HTML/PPTX ignore the typst-only template branch.
    header_logo = _brand_logo_path(brand_yml)
    typst_preamble = (
        components_mod.typ_tokens(tok) + (comp_dir / "components.typ").read_text()
    )
    logo_arg = f'"/{header_logo}"' if header_logo else "none"
    chrome_args = [f"logo: {logo_arg}"]
    if cover_title:
        chrome_args.append(f"title: {_typst_str(cover_title)}")
    if cover_standfirst:
        chrome_args.append(f"standfirst: {_typst_str(cover_standfirst)}")
    typst_preamble += f"#show: doc_chrome.with({', '.join(chrome_args)})\n"

    # HTML gets the same identity before the body (issue #38 — the logo
    # previously appeared on PDF only). A leading H1 becomes a full cover banner;
    # otherwise just the logo header. embed-resources inlines the referenced
    # asset at render, so the deliverable stays self-contained.
    html_header = None
    if cover_title:
        parts = ['<section class="ds-cover">']
        if header_logo:
            parts.append(f'<img class="ds-cover-logo" src="{header_logo}" alt="">')
        parts.append(f'<h1 class="ds-cover-title">{_html_escape(cover_title)}</h1>')
        parts.append('<div class="ds-cover-rule"></div>')
        if cover_standfirst:
            parts.append(
                f'<p class="ds-cover-standfirst">{_html_escape(cover_standfirst)}</p>'
            )
        parts.append("</section>\n")
        (tmp / "_cover.html").write_text("".join(parts), encoding="utf-8")
        html_header = "_cover.html"
    elif header_logo:
        (tmp / "_doc_header.html").write_text(
            '<header class="ds-doc-header">'
            f'<img src="{header_logo}" alt="">'
            "</header>\n",
            encoding="utf-8",
        )
        html_header = "_doc_header.html"

    quarto_tpl = (TEMPLATES / "quarto" / "quarto.yml.j2").read_text()
    quarto_yml = Template(quarto_tpl).render(
        formats=[sfmt],
        format_map=_FORMAT_MAP,
        has_pptx_reference=pptx_ref.exists(),
        css_override=(brand_root / "css" / "overrides.css").exists(),
        typst_preamble=typst_preamble,
        html_header=html_header,
    )
    (tmp / "_quarto.yml").write_text(quarto_yml)

    if (brand_root / "css" / "overrides.css").exists():
        (tmp / "css").mkdir(exist_ok=True)
        shutil.copy2(
            brand_root / "css" / "overrides.css", tmp / "css" / "overrides.css"
        )

    # Render
    src_stem = source_md.stem  # "source"
    out_stem = _out_stem(state)
    qfmt = _FORMAT_MAP.get(sfmt, sfmt)
    cmd = ["quarto", "render", "source.md", "--to", qfmt]
    result = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"quarto render --to {qfmt} failed:\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    produced = tmp / f"{src_stem}{_EXT[sfmt]}"
    if not produced.exists():
        raise RuntimeError(f"quarto reported success but {produced} not found")
    dest = session_path / "outputs" / f"{out_stem}.v{version}{_EXT[sfmt]}"
    _emit_output(sfmt, produced, dest, src_stem, tmp)

    shutil.rmtree(tmp, ignore_errors=True)
    return {sfmt: dest}


# ---------------------------------------------------------------- frame-engine


def _engine_frame(
    session_path: Path, resolved: dict[str, Any], state: dict[str, Any], version: str
) -> dict[str, Path]:
    """Fill the canonical two-axis showcase template against the brand.

    Reads the template path from the resolved contract (sealed by
    ``layouts/frame.yml``), substitutes the BRAND TOKENS block + inline
    hardcoded hexes from the brand's ``_brand.yml`` (#100), then jinja-renders
    ``{{ title }}`` / ``{{ description }}``. CONTENT SLOT replacement
    (source.md → topics) is a follow-up slice; the template's authored copy is
    kept verbatim for now.
    """
    template_rel = resolved.get("template")
    if not template_rel:
        raise RuntimeError(
            "frame-engine: resolved contract has no `template:` field. "
            "Check layouts/frame.yml."
        )
    template_path = PLUGIN_ROOT / template_rel
    if not template_path.exists():
        raise FileNotFoundError(f"frame-engine: template not found: {template_path}")

    slug = state["brand"]
    brand_yml_path = brand_mod.brand_yml_path(slug)
    if not brand_yml_path.exists():
        raise FileNotFoundError(
            f"frame-engine: brand spec missing: {brand_yml_path}. "
            f"Run `studio ingest --brand {slug} --sources ...` first."
        )
    brand_yml = yaml.safe_load(brand_yml_path.read_text()) or {}

    # Source frontmatter wins for document-level title/description; session
    # state and the resolved contract are the fallbacks. The body (post-
    # frontmatter) feeds the CONTENT SLOT topic parser when it has H2 headings.
    source_text = (session_path / "inputs" / "source.md").read_text(encoding="utf-8")
    front, body = frame_template_mod.parse_frontmatter(source_text)
    title = (
        front.get("title")
        or state.get("title")
        or resolved.get("name")
        or "Showcase"
    )
    description = (
        front.get("description")
        or state.get("description")
        or resolved.get("description")
        or ""
    )

    rendered = frame_template_mod.fill_template(
        template_path.read_text(encoding="utf-8"),
        brand_yml,
        title=title,
        description=description,
        source_body=body,
    )

    sfmt = formats_mod.studio_format(resolved)
    out_stem = _out_stem(state)
    dest = session_path / "outputs" / f"{out_stem}.v{version}{_EXT[sfmt]}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(rendered, encoding="utf-8")

    # The viewer contract guarantee (data-page-key, np:pagechange, NP_ASSET)
    # is the template's responsibility; render here only verifies the meta-strip
    # invariant — no `nopilot:` leak from session inputs.
    if metacontent.has_meta_leak(rendered):
        raise RuntimeError(
            f"meta-content leak in {dest.name} — template or input contains a "
            "surviving `nopilot:` region (issue #11)."
        )
    return {sfmt: dest}


def _engine_gslide(
    session_path: Path, resolved: dict[str, Any], state: dict[str, Any], version: str
) -> dict[str, Path]:
    """Native Google Slides renderer (manifest-native via studio.gslide). Builds the
    Slides batchUpdate payload (the renderable artifact) from the session source + brand
    tokens, honouring the format's render profile (e.g. proposal → longform typography +
    figures). Pushing to a live deck is a separate `python -m studio.gslide --execute`
    step (an account write); bespoke SVG figures rasterise at push time."""
    import json as _json

    from . import gslide as gslide_mod

    slug = state["brand"]
    profile = resolved.get("profile") or (resolved.get("render") or {}).get("profile")
    src = session_path / "inputs" / "source.md"
    dest = session_path / "outputs" / f"{_out_stem(state)}.v{version}.gslide.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    title, reqs = gslide_mod.build_requests(src, brand=slug, profile=profile)
    payload = {"title": title, "slides": sum(1 for r in reqs if "createSlide" in r),
               "requests": [r for r in reqs if "_studio_image" not in r]}
    dest.write_text(_json.dumps(payload, indent=2), encoding="utf-8")
    return {"gslide": dest}


# Registry of engine name -> function. Layouts declare which engine they use.
_ENGINES: dict[str, Engine] = {
    "linear-engine": _engine_linear,
    "pptx-engine": _engine_pptx,
    "uds-pdf-engine": _engine_uds_pdf,
    "frame-engine": _engine_frame,
    "gslide-engine": _engine_gslide,
}


def known_engines() -> list[str]:
    """Engine names registered in this build (exposed for `studio doctor`)."""
    return sorted(_ENGINES)


# ---------------------------------------------------------------- helpers


def _brand_logo_path(brand_yml: Path) -> str | None:
    """The brand's logo path relative to its folder (e.g. ``assets/logo.svg``).

    Used to cap the Typst header logo (issue #2). Accepts ``logo`` as a string,
    a ``{path: ...}`` mapping, or ``small``/``medium``/``large`` variants of
    either. Returns None when the brand has no logo.
    """
    try:
        data = yaml.safe_load(brand_yml.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return None

    def _as_path(value: object) -> str | None:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return value.get("path")
        return None

    logo = data.get("logo")
    if isinstance(logo, str):
        candidate: str | None = logo
    elif isinstance(logo, dict):
        candidate = next(
            (
                _as_path(logo.get(k))
                for k in ("small", "medium", "large")
                if logo.get(k)
            ),
            None,
        ) or _as_path(logo)
    else:
        candidate = None
    return candidate.lstrip("./") if candidate else None


def _emit_output(
    fmt: str, produced: Path, dest: Path, src_stem: str, tmp: Path
) -> None:
    """Move a rendered artifact to ``dest``, guaranteeing HTML actually works.

    HTML/RevealJS are meant to be self-contained (``embed-resources: true``).
    Rendering in a non-hidden build dir gives that. But if a future Quarto change
    again leaves a ``<stem>_files`` support directory the HTML still references,
    moving only the ``.html`` and deleting the build dir would orphan those assets
    and ship an unstyled page under a success banner (issue #1). So guard: if the
    sidecar survives, ship it alongside the output and rewrite the references —
    a working multi-file deliverable with a loud warning, never a silent break.
    """
    # The session's outputs/ dir exists for `session init`-created sessions, but
    # not for docket-scaffolded render sessions (just version.json + inputs/).
    # Guarantee the destination dir before moving/writing (issue #34).
    dest.parent.mkdir(parents=True, exist_ok=True)

    if fmt not in ("html", "revealjs"):
        shutil.move(str(produced), dest)
        return

    # HTML-path verification of the meta-content strip (issue #11): HTML comments
    # are not self-hiding here, so a surviving `nopilot:` region would ship inside
    # client-facing source. Fail loudly rather than leak.
    if metacontent.has_meta_leak(produced.read_text(encoding="utf-8")):
        raise RuntimeError(
            f"meta-content leak: a `nopilot:` region survived into {produced.name} "
            "— the strip step must run before render (issue #11)."
        )

    sidecar = tmp / f"{src_stem}_files"
    if not sidecar.exists():
        shutil.move(str(produced), dest)  # genuinely self-contained
        return

    dest_sidecar = dest.parent / f"{dest.stem}_files"
    if dest_sidecar.exists():
        shutil.rmtree(dest_sidecar)
    html = produced.read_text(encoding="utf-8").replace(
        f"{src_stem}_files/", f"{dest_sidecar.name}/"
    )
    dest.write_text(html, encoding="utf-8")
    produced.unlink(missing_ok=True)
    shutil.move(str(sidecar), dest_sidecar)
    print(
        f"⚠ {dest.name}: Quarto did not inline assets — shipped support files in "
        f"{dest_sidecar.name}/ so the page renders. Keep the .html and that "
        "folder together.",
        file=sys.stderr,
    )


def detect_quarto() -> str | None:
    return shutil.which("quarto")
