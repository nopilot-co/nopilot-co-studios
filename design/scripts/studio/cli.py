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
from . import content as content_mod
from . import deps as deps_mod
from . import docket as docket_mod
from . import formats as formats_mod
from . import ingest as ingest_mod
from . import qa as qa_mod
from . import render as render_mod
from . import session as session_mod
from . import tokens as tokens_mod


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
            layout = r.get("layout", "—")
            if not formats_mod.is_renderable(r):
                note = "  (not renderable yet)"
            else:
                missing = deps_mod.missing_for(r, "render")
                note = f"  (needs: {', '.join(missing)})" if missing else ""
            click.echo(
                f"{slug:<18}  {r.get('asset_type', '—'):<10}  "
                f"[{layout:<7}] -> {sfmt}{note}"
            )
        except (FileNotFoundError, ValueError, formats_mod.SealedKeyConflict) as e:
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
    try:
        errors = errors + formats_mod.validate_asset_refs(formats_mod.resolve(slug))
    except (FileNotFoundError, ValueError):
        pass
    if errors:
        for e in errors:
            click.echo(f"  ✗ {e}", err=True)
        sys.exit(1)
    click.echo(f"✓ {slug} is valid")


@formats.command("assets")
def formats_assets() -> None:
    """List the asset library (design/formats/assets/)."""
    from . import assets as assets_mod

    for slug in assets_mod.list_assets():
        a = assets_mod.load_asset(None, slug)
        buckets = ",".join(a.get("buckets", []))
        exports = ",".join(a.get("exports", []))
        click.echo(f"{slug:<22} {buckets:<28} {exports}")


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
@click.option(
    "--import-from",
    "import_from",
    default=None,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="One-shot import of an existing Brand Docket (a folder with _brand.yml) "
    "into the docket-local brand store. Origin is recorded as provenance only.",
)
@click.pass_context
def ingest(
    ctx: click.Context,
    slug: str | None,
    sources: tuple[Path, ...],
    import_from: Path | None,
) -> None:
    """Ingest source materials into a canonical brand folder.

    With no subcommand: runs the full ingest pipeline, or — with --import-from —
    copies an existing Brand Docket in (no extraction).
    Sources may be individual files (.pdf .pptx .png .jpg .jpeg .svg) or folders
    containing any mix of supported files at any depth.
    """
    if ctx.invoked_subcommand is not None:
        return
    if not slug:
        raise click.UsageError("--brand <slug> required")
    if import_from is not None:
        try:
            click.echo(ingest_mod.import_from(slug, import_from))
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        return
    if not sources:
        raise click.UsageError(
            "--sources <path> [<path> ...] (or --import-from) required"
        )
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
@click.option(
    "--design-system",
    "design_system",
    default=None,
    help="Optional design-system slug to lock (see `studio design-systems`); "
    "its tokens layer under the brand.",
)
def session_init(
    slug: str, name: str, fmt: str, source: Path, design_system: str | None
) -> None:
    if design_system and design_system not in tokens_mod.list_design_systems():
        raise click.ClickException(
            f"unknown design-system '{design_system}' "
            f"(see `studio design-systems`)"
        )
    try:
        path = session_mod.init(slug, name, source, fmt, design_system)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    click.echo(str(path))


# ---------------------------------------------------------------- design-systems
@main.command("design-systems")
def design_systems_cmd() -> None:
    """List available design-system slugs (lockable per session)."""
    systems = tokens_mod.list_design_systems()
    if not systems:
        click.echo("(no design systems in resources/design-systems/)")
        return
    for s in systems:
        click.echo(s)


# ---------------------------------------------------------------- docket
@main.group()
def docket() -> None:
    """Scaffold and manage production dockets (self-contained production_root)."""


@docket.command("init")
@click.argument("production_root", type=click.Path(path_type=Path))
@click.option("--brand", "slug", default=None, help="Brand slug to record (kebab-case)")
@click.option(
    "--session", "session_name", default=None, help="First production-session name"
)
def docket_init(
    production_root: Path, slug: str | None, session_name: str | None
) -> None:
    """Create (or top up) a production docket under PRODUCTION_ROOT."""
    try:
        root = docket_mod.init_docket(production_root, brand=slug, session=session_name)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    click.echo(str(root))


@docket.command("validate")
@click.argument(
    "manifest", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--kind",
    type=click.Choice(["production", "session"]),
    required=True,
    help="Which manifest schema to validate against.",
)
def docket_validate(manifest: Path, kind: str) -> None:
    """Validate a production- or session-manifest against its JSON Schema."""
    errors = docket_mod.validate_manifest(kind, docket_mod.read_manifest(manifest))
    if errors:
        for e in errors:
            click.echo(f"  ✗ {e}", err=True)
        sys.exit(1)
    click.echo(f"✓ {manifest.name} is a valid {kind}-manifest")


# ---------------------------------------------------------------- content
@main.group()
def content() -> None:
    """Manage docket content files (primaries + format variants)."""


@content.command("bump")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--kind", default="patch", type=click.Choice(["patch", "minor", "major"]))
@click.option("--author", default=None)
@click.option("--status", default=None, help="draft | in-review | approved")
@click.option("--note", default=None)
def content_bump(
    file: Path,
    kind: str,
    author: str | None,
    status: str | None,
    note: str | None,
) -> None:
    """Bump a content file's version: stamps the filename, front-matter, history."""
    new_path, new_version = content_mod.bump(
        file, kind, author=author, status=status, note=note
    )
    click.echo(f"✓ v{new_version}  {new_path}")


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

    click.echo(
        "\nNotes:\n"
        "  • PDF diagrams (flow/timeline/process/hierarchy/org) use the Typst "
        "`fletcher` package,\n    fetched from the network on first use and cached "
        "after. The first PDF-with-diagram\n    render needs internet; subsequent "
        "renders are offline. (Pre-vendor the package into\n    the Typst cache for "
        "fully offline/sandbox runs.)"
    )


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
