"""CLI entry point: `studio <command>`.

Subcommands match the skills:
  studio brand list | validate | show
  studio formats list | show --format SLUG | validate --format SLUG
  studio ingest --brand SLUG --sources PATH [PATH ...]
  studio ingest synthesize-pptx --brand SLUG
  studio session init --brand SLUG --name NAME --format SLUG --source PATH
  studio render --session PATH --bump patch|minor|major
  studio qa capture --session PATH [--version X.Y.Z]
  studio doctor
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from . import brand as brand_mod
from . import deps as deps_mod
from . import formats as formats_mod
from . import ingest as ingest_mod
from . import qa as qa_mod
from . import render as render_mod
from . import session as session_mod


@click.group()
def main() -> None:
    """design-studio orchestrator."""


# ---------------------------------------------------------------- brand
@main.group()
def brand() -> None:
    """Manage brand specs."""


@brand.command("list")
def brand_list() -> None:
    rows = brand_mod.list_brands()
    if not rows:
        click.echo("(no brands yet — run: studio ingest --brand <slug> --sources ...)")
        return
    width = max(len(r["slug"]) for r in rows)
    for r in rows:
        last = r.get("last_rendered") or "never"
        click.echo(
            f"{r['slug']:<{width}}  {r['primary']:<9}  {r['font']:<28}  last: {last}"
        )


@brand.command("validate")
@click.option("--brand", "slug", required=True)
def brand_validate(slug: str) -> None:
    errors = brand_mod.validate(slug)
    if errors:
        for e in errors:
            click.echo(f"  ✗ {e}", err=True)
        sys.exit(1)
    click.echo(f"✓ {slug} is valid")


@brand.command("show")
@click.option("--brand", "slug", required=True)
def brand_show(slug: str) -> None:
    click.echo(brand_mod.show(slug))


# ---------------------------------------------------------------- formats
@main.group()
def formats() -> None:
    """Inspect format contracts (purpose × export)."""


@formats.command("list")
def formats_list() -> None:
    slugs = formats_mod.list_formats()
    if not slugs:
        click.echo("(no formats defined)")
        return
    for slug in slugs:
        try:
            r = formats_mod.resolve(slug)
            sfmt = formats_mod.studio_format(r) or "—"
            if not formats_mod.is_renderable(r):
                note = "  (not renderable yet)"
            else:
                missing = deps_mod.missing_for(r, "render")
                note = f"  (needs: {', '.join(missing)})" if missing else ""
            click.echo(f"{slug:<18}  {r.get('asset_type', '—'):<10}  -> {sfmt}{note}")
        except (FileNotFoundError, ValueError) as e:
            click.echo(f"{slug:<18}  ✗ {e}", err=True)


@formats.command("show")
@click.option("--format", "slug", required=True)
def formats_show(slug: str) -> None:
    try:
        click.echo(formats_mod.show(slug))
    except (FileNotFoundError, ValueError) as e:
        raise click.ClickException(str(e)) from e


@formats.command("validate")
@click.option("--format", "slug", required=True)
def formats_validate(slug: str) -> None:
    errors = formats_mod.validate(slug)
    if errors:
        for e in errors:
            click.echo(f"  ✗ {e}", err=True)
        sys.exit(1)
    click.echo(f"✓ {slug} is valid")


# ---------------------------------------------------------------- ingest
@main.group(invoke_without_command=True)
@click.option("--brand", "slug", help="Brand slug (kebab-case)")
@click.option(
    "--sources",
    multiple=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path),
    help="One or more files OR folders. Folders are walked recursively; "
    "hidden files and __pycache__/node_modules/.git are skipped.",
)
@click.pass_context
def ingest(ctx: click.Context, slug: str | None, sources: tuple[Path, ...]) -> None:
    """Ingest source materials into a canonical brand folder.

    With no subcommand: runs the full ingest pipeline.
    Sources may be individual files (.pdf .pptx .png .jpg .jpeg .svg) or folders
    containing any mix of supported files at any depth.
    """
    if ctx.invoked_subcommand is not None:
        return
    if not slug:
        raise click.UsageError("--brand <slug> required")
    if not sources:
        raise click.UsageError("--sources <path> [<path> ...] required")
    report = ingest_mod.run(slug, list(sources))
    click.echo(report)


@ingest.command("synthesize-pptx")
@click.option("--brand", "slug", required=True)
def ingest_synth_pptx(slug: str) -> None:
    path = ingest_mod.synthesize_reference_pptx(slug)
    click.echo(f"✓ synthesized reference deck: {path}")


# ---------------------------------------------------------------- session
@main.group()
def session() -> None:
    """Manage render sessions."""


@session.command("init")
@click.option("--brand", "slug", required=True)
@click.option("--name", required=True, help="Session name (kebab-case)")
@click.option(
    "--format",
    "fmt",
    required=True,
    help="Format slug to lock in, e.g. pitch-pdf (see `studio formats list`)",
)
@click.option("--source", required=True, type=click.Path(exists=True, path_type=Path))
def session_init(slug: str, name: str, fmt: str, source: Path) -> None:
    try:
        path = session_mod.init(slug, name, source, fmt)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    click.echo(str(path))


# ---------------------------------------------------------------- render
@main.command("render")
@click.option(
    "--session",
    "session_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--bump", default="patch", type=click.Choice(["patch", "minor", "major"]))
def render_cmd(session_path: Path, bump: str) -> None:
    """Render the session's locked format. The export is fixed by the format slug."""
    try:
        outputs = render_mod.render(session_path, bump)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        raise click.ClickException(str(e)) from e
    for fmt, out_path in outputs.items():
        click.echo(f"  ✓ {fmt:<8} {out_path}")

    # Deterministic ruleset enforcement against the rendered artifacts.
    state = session_mod.read_state(session_path)
    resolved = formats_mod.resolve(state["format"])
    violations = formats_mod.check_output(resolved, outputs)
    if violations:
        click.echo(f"\n✗ format '{state['format']}' ruleset violations:", err=True)
        for v in violations:
            click.echo(f"  - {v}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------- doctor
@main.command("doctor")
def doctor_cmd() -> None:
    """Report runtime dependency status and per-format render readiness."""
    rep = deps_mod.doctor()
    click.echo("Tools:")
    for tool, ok in rep["tools"].items():
        if ok:
            click.echo(f"  ✓ {tool}")
        else:
            click.echo(
                f"  ✗ {tool}   →  {deps_mod.INSTALL_HINTS.get(tool, '(install it)')}"
            )
    click.echo("\nFormats:")
    for f in rep["formats"]:
        if not f["renderable"]:
            status = "— not renderable (no Quarto mapping)"
        elif f["render_ready"]:
            status = "✓ ready"
            if f["qa_missing"]:
                status += f"  (QA needs: {', '.join(f['qa_missing'])})"
        else:
            status = f"✗ needs: {', '.join(f['render_missing'])}"
        click.echo(f"  {f['slug']:<16} {status}")


# ---------------------------------------------------------------- qa
@main.group()
def qa() -> None:
    """Visual QA against a rendered version."""


@qa.command("capture")
@click.option(
    "--session",
    "session_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--version", default=None, help="Version to capture (defaults to current)"
)
def qa_capture(session_path: Path, version: str | None) -> None:
    images = qa_mod.capture(session_path, version)
    click.echo(
        f"✓ captured {len(images)} images to {images[0].parent if images else '(none)'}"
    )


if __name__ == "__main__":
    main()
