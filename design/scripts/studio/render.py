"""Quarto subprocess wrapper.

Materializes a per-render Quarto project in <session>/_render/, points it at the
brand's _brand.yml, runs `quarto render`, moves outputs to <session>/outputs/
with versioned filenames, and cleans up.

Note: the build dir must NOT be dot-prefixed. Quarto (≥1.9) skips hidden
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

import yaml
from jinja2 import Template

from . import TEMPLATES
from . import brand as brand_mod
from . import charts as charts_mod
from . import components as components_mod
from . import diagrams as diagrams_mod
from . import formats as formats_mod
from . import metacontent
from . import pptx_render as pptx_mod
from . import session as session_mod
from . import tokens as tokens_mod

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


_H1_RE = re.compile(r"^#\s+(\S.*)$")
_PRECIS_OPEN_RE = re.compile(r"^:::+\s*\{?\.?(?:precis|lead)\b")
_FENCE_CLOSE_RE = re.compile(r"^:::+\s*$")


def _typst_str(value: str) -> str:
    """A Typst double-quoted string literal (escape backslash + quote)."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _extract_cover(body: str) -> tuple[str | None, str | None, str]:
    """Lift the document's leading title block onto a cover (#38).

    Returns ``(title, standfirst, body_without_cover)``:
    - ``title`` — text of the first level-1 heading (``# ...``); ``None`` (and an
      unchanged body) if the document has no leading H1.
    - ``standfirst`` — the inner text of a ``::: precis`` / ``::: lead`` block
      that immediately follows the H1, if present.
    Both are removed from the returned body so the cover content isn't repeated;
    section headings (H2) then lead the running text.
    """
    lines = body.split("\n")
    h1 = next((i for i, ln in enumerate(lines) if _H1_RE.match(ln)), None)
    if h1 is None:
        return None, None, body
    title = _H1_RE.match(lines[h1]).group(1).strip()
    del lines[h1]
    j = h1
    while j < len(lines) and not lines[j].strip():
        j += 1
    standfirst: str | None = None
    if j < len(lines) and _PRECIS_OPEN_RE.match(lines[j]):
        k = j + 1
        inner: list[str] = []
        while k < len(lines) and not _FENCE_CLOSE_RE.match(lines[k]):
            inner.append(lines[k].strip())
            k += 1
        standfirst = " ".join(s for s in inner if s) or None
        del lines[j : k + 1]  # drop the precis block incl. its closing fence
    return title, standfirst, "\n".join(lines)


def render(session_path: Path, bump_kind: str) -> dict[str, Path]:
    state = session_mod.read_state(session_path)
    slug = state["brand"]

    # The session locks in exactly one format slug; the export it produces is
    # fixed by that slug, never chosen ad hoc at render time.
    fmt_slug = state.get("format")
    if not fmt_slug:
        raise RuntimeError(
            "session has no locked format. Re-create it with "
            "`studio session init --format <slug> ...` (see `studio formats list`)."
        )
    resolved = formats_mod.resolve(fmt_slug)
    sfmt = formats_mod.studio_format(resolved)
    if not formats_mod.is_renderable(resolved):
        raise RuntimeError(
            f"format '{fmt_slug}' (export '{resolved.get('export')}') is not "
            f"renderable by the studio pipeline yet — no Quarto mapping. "
            f"Pick a renderable format (pdf, html, pptx, revealjs)."
        )
    formats = [sfmt]

    brand_yml = brand_mod.brand_yml_path(slug)
    if not brand_yml.exists():
        raise FileNotFoundError(f"brand spec missing: {brand_yml}")

    new_version = session_mod.next_version(session_path, bump_kind)

    # pptx renders through the native python-pptx engine (#19), not Quarto.
    if sfmt == "pptx":
        out_stem = _strip_version_label(
            state.get("source_filename", "source.md").rsplit(".", 1)[0] or "source"
        )
        dest = session_path / "outputs" / f"{out_stem}.v{new_version}.pptx"
        dest.parent.mkdir(parents=True, exist_ok=True)
        tok = tokens_mod.resolve(slug, state.get("design_system"))
        body = metacontent.strip(session_path / "inputs" / "source.md")
        pptx_mod.build_pptx(body, tok, dest)
        outputs = {sfmt: dest}
        session_mod.record_render(session_path, new_version, [sfmt], outputs)
        return outputs

    # Non-pptx (html/pdf/revealjs) render through Quarto.
    if detect_quarto() is None:
        raise RuntimeError(
            "quarto not found on PATH.\n"
            "  Install: brew install --cask quarto  (or download from https://quarto.org/docs/get-started/)\n"
            "  Then re-run: studio render ..."
        )

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
        formats=formats,
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

    # Render each format
    outputs: dict[str, Path] = {}
    src_stem = source_md.stem  # "source"
    out_stem = _strip_version_label(
        state.get("source_filename", "source.md").rsplit(".", 1)[0] or "source"
    )

    for fmt in formats:
        qfmt = _FORMAT_MAP.get(fmt, fmt)
        cmd = ["quarto", "render", "source.md", "--to", qfmt]
        result = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"quarto render --to {qfmt} failed:\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        # Quarto writes to source.<ext> in the tmp dir
        produced = tmp / f"{src_stem}{_EXT[fmt]}"
        if not produced.exists():
            raise RuntimeError(f"quarto reported success but {produced} not found")
        dest = session_path / "outputs" / f"{out_stem}.v{new_version}{_EXT[fmt]}"
        _emit_output(fmt, produced, dest, src_stem, tmp)
        outputs[fmt] = dest

    session_mod.record_render(session_path, new_version, formats, outputs)
    shutil.rmtree(tmp, ignore_errors=True)
    return outputs


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
