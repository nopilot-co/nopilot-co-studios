"""Quarto subprocess wrapper.

Materializes a per-render Quarto project in <session>/.tmp/, points it at the
brand's _brand.yml, runs `quarto render`, moves outputs to <session>/outputs/
with versioned filenames, and cleans up.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml
from jinja2 import Template

from . import TEMPLATES
from . import brand as brand_mod
from . import formats as formats_mod
from . import session as session_mod

# Quarto format names by our short names
_FORMAT_MAP = {
    "pdf": "typst",   # use Typst engine, not LaTeX
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
    tmp = session_path / ".tmp"
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

    # Generate quarto.yml from template
    quarto_tpl = (TEMPLATES / "quarto" / "quarto.yml.j2").read_text()
    quarto_yml = Template(quarto_tpl).render(
        formats=formats,
        format_map=_FORMAT_MAP,
        has_pptx_reference=pptx_ref.exists(),
        css_override=(brand_root / "css" / "overrides.css").exists(),
    )
    (tmp / "_quarto.yml").write_text(quarto_yml)

    if (brand_root / "css" / "overrides.css").exists():
        (tmp / "css").mkdir(exist_ok=True)
        shutil.copy2(brand_root / "css" / "overrides.css", tmp / "css" / "overrides.css")

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
        shutil.move(str(produced), dest)
        outputs[fmt] = dest

    session_mod.record_render(session_path, new_version, formats, outputs)
    shutil.rmtree(tmp, ignore_errors=True)
    return outputs


def detect_quarto() -> str | None:
    return shutil.which("quarto")
