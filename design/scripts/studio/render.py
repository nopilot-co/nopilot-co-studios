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

import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from jinja2 import Template

from . import TEMPLATES
from . import brand as brand_mod
from . import formats as formats_mod
from . import session as session_mod

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


def render(session_path: Path, bump_kind: str) -> dict[str, Path]:
    if detect_quarto() is None:
        raise RuntimeError(
            "quarto not found on PATH.\n"
            "  Install: brew install --cask quarto  (or download from https://quarto.org/docs/get-started/)\n"
            "  Then re-run: studio render ..."
        )

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
    tmp = session_path / "_render"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    # Copy source and brand assets into the tmp project
    source_md = session_path / "inputs" / "source.md"
    shutil.copy2(source_md, tmp / "source.md")
    shutil.copy2(brand_yml, tmp / "_brand.yml")

    brand_root = brand_mod.brand_root(slug)
    assets_src = brand_root / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, tmp / "assets")
    pptx_ref = brand_root / "reference.pptx"
    if pptx_ref.exists():
        shutil.copy2(pptx_ref, tmp / "reference.pptx")

    # Generate quarto.yml from template. The header logo (if any) is passed in so
    # the PDF/Typst block can cap it and reserve top margin — Quarto's default
    # 1.5in background logo overlaps body text on continuation pages (issue #2).
    header_logo = _brand_logo_path(brand_yml)
    quarto_tpl = (TEMPLATES / "quarto" / "quarto.yml.j2").read_text()
    quarto_yml = Template(quarto_tpl).render(
        formats=formats,
        format_map=_FORMAT_MAP,
        has_pptx_reference=pptx_ref.exists(),
        css_override=(brand_root / "css" / "overrides.css").exists(),
        logo=(f"/{header_logo}" if header_logo else None),
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
    out_stem = state.get("source_filename", "source.md").rsplit(".", 1)[0] or "source"

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
