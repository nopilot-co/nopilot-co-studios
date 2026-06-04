"""CLI entry point: `planner <command>`.

Subcommands mirror the planner skill's steps 1:1 (judgment in the skill, mechanics
here):

  planner plan new --root PATH --brand SLUG --objective TEXT --format SLUG
  planner section add --root PATH --id ID --title TEXT [--after ID]
  planner section move --root PATH --id ID [--after ID]
  planner section set --root PATH --id ID [--status S] [--title T] [--note N]
  planner data add --root PATH --id ID --path REL --kind md|csv|image
  planner viz set --root PATH --id ID --type T --source REL [--x C] [--y C] [--caption T]
  planner brief write --root PATH --id ID
  planner status --root PATH
  planner assemble --root PATH [--bump patch|minor|major] [--allow-partial]
  planner doctor
"""

from __future__ import annotations

from pathlib import Path

import click

from . import assemble as assemble_mod
from . import brief as brief_mod
from . import composition as comp
from . import deps as deps_mod
from . import docket_bridge

# Reused option: the production-docket root the planner operates over, in place.
_root_opt = click.option(
    "--root",
    "root",
    required=True,
    type=click.Path(path_type=Path),
    help="The production-docket folder to operate over (in place).",
)


def _fail(msg: str) -> None:
    raise click.ClickException(msg)


@click.group()
def main() -> None:
    """Composite-document planner — plan + assemble; the design studio renders."""


# ---------------------------------------------------------------- plan
@main.group()
def plan() -> None:
    """Scaffold a composition over a production docket."""


@plan.command("new")
@_root_opt
@click.option("--brand", "brand", required=True, help="Brand slug (kebab-case).")
@click.option("--objective", required=True, help="High-level document objective.")
@click.option(
    "--format",
    "fmt",
    required=True,
    help="Design format slug to render as, e.g. proposal-pdf (see `studio formats list`).",
)
@click.option(
    "--session",
    "session_name",
    default=None,
    help="Production-session name (default: <brand>-<kebab objective>).",
)
def plan_new(
    root: Path, brand: str, objective: str, fmt: str, session_name: str | None
) -> None:
    """Create the docket (if needed) + the composition manifest."""
    root = root.expanduser()
    session = session_name or _slugify(f"{brand}-{objective}")

    valid = docket_bridge.format_valid(fmt)
    if valid is False:
        _fail(
            f"unknown design format '{fmt}' — run `studio formats list` for valid slugs"
        )
    elif valid is None:
        click.echo(
            f"  ⚠ could not validate format '{fmt}' (design `studio` CLI not "
            "installed) — storing it as given",
            err=True,
        )

    try:
        docket_bridge.init_docket(root, brand=brand, session=session)
        comp.new(root, brand=brand, objective=objective, fmt=fmt, session=session)
    except (RuntimeError, ValueError) as e:
        _fail(str(e))
    (root / "sections").mkdir(parents=True, exist_ok=True)
    click.echo(f"✓ composition ready: {comp.path_for(root)}")
    click.echo(f"  session: {session}   format: {fmt}   brand: {brand}")


# ---------------------------------------------------------------- section
@main.group()
def section() -> None:
    """Add, reorder, and update sections."""


@section.command("add")
@_root_opt
@click.option("--id", "section_id", required=True, help="Section id (kebab-case).")
@click.option("--title", required=True)
@click.option("--after", default=None, help="Insert after this section id.")
def section_add(root: Path, section_id: str, title: str, after: str | None) -> None:
    try:
        comp.add_section(
            root.expanduser(), section_id=section_id, title=title, after=after
        )
    except (FileNotFoundError, ValueError) as e:
        _fail(str(e))
    click.echo(f"✓ added section '{section_id}' — {title}")


@section.command("move")
@_root_opt
@click.option("--id", "section_id", required=True)
@click.option(
    "--after", default=None, help="Move after this id (omit → move to start)."
)
def section_move(root: Path, section_id: str, after: str | None) -> None:
    try:
        comp.move_section(root.expanduser(), section_id=section_id, after=after)
    except (FileNotFoundError, ValueError) as e:
        _fail(str(e))
    click.echo(f"✓ moved '{section_id}'")


@section.command("set")
@_root_opt
@click.option("--id", "section_id", required=True)
@click.option(
    "--status",
    default=None,
    type=click.Choice(list(comp.STATUSES)),
    help="todo | briefed | drafted | approved",
)
@click.option("--title", default=None)
@click.option(
    "--note", default=None, help="Provenance / reference note for the section."
)
def section_set(
    root: Path,
    section_id: str,
    status: str | None,
    title: str | None,
    note: str | None,
) -> None:
    if status is None and title is None and note is None:
        _fail("nothing to set — pass --status, --title, and/or --note")
    try:
        comp.set_section(
            root.expanduser(),
            section_id=section_id,
            status=status,
            title=title,
            note=note,
        )
    except (FileNotFoundError, ValueError) as e:
        _fail(str(e))
    click.echo(f"✓ updated '{section_id}'")


# ---------------------------------------------------------------- data
@main.group()
def data() -> None:
    """Manage a section's data-source contract."""


@data.command("add")
@_root_opt
@click.option("--id", "section_id", required=True)
@click.option(
    "--path",
    "rel_path",
    required=True,
    help="Docket-relative path, e.g. assets/tam.csv.",
)
@click.option("--kind", required=True, type=click.Choice(["md", "csv", "image"]))
def data_add(root: Path, section_id: str, rel_path: str, kind: str) -> None:
    root = root.expanduser()
    if (root / rel_path).resolve().is_file() is False:
        click.echo(
            f"  ⚠ {rel_path} does not exist yet under the docket — recording the "
            "contract anyway; drop the file in before assemble/render",
            err=True,
        )
    try:
        comp.add_data(root, section_id=section_id, rel_path=rel_path, kind=kind)
    except (FileNotFoundError, ValueError) as e:
        _fail(str(e))
    click.echo(f"✓ data source '{rel_path}' ({kind}) → '{section_id}'")


# ---------------------------------------------------------------- viz
@main.group()
def viz() -> None:
    """Suggest a visualisation for a section (rendered by the design studio)."""


@viz.command("set")
@_root_opt
@click.option("--id", "section_id", required=True)
@click.option(
    "--type", "chart_type", required=True, help="bar | line | area | scatter | pie | …"
)
@click.option(
    "--source", required=True, help="Docket-relative data source (usually a csv)."
)
@click.option("--x", default=None, help="X column.")
@click.option("--y", default=None, help="Y column.")
@click.option("--caption", default=None)
def viz_set(
    root: Path,
    section_id: str,
    chart_type: str,
    source: str,
    x: str | None,
    y: str | None,
    caption: str | None,
) -> None:
    try:
        comp.set_viz(
            root.expanduser(),
            section_id=section_id,
            chart_type=chart_type,
            source=source,
            x=x,
            y=y,
            caption=caption,
        )
    except (FileNotFoundError, ValueError) as e:
        _fail(str(e))
    click.echo(f"✓ viz ({chart_type}) → '{section_id}'  [rendered by design]")


# ---------------------------------------------------------------- brief
@main.group()
def brief() -> None:
    """Scaffold discrete briefs for sections."""


@brief.command("write")
@_root_opt
@click.option("--id", "section_id", required=True)
def brief_write(root: Path, section_id: str) -> None:
    root = root.expanduser()
    try:
        data = comp.read(root)
        sec = comp._find(data, section_id)
        brief_path, _ = brief_mod.write_brief(
            root,
            section_id=section_id,
            title=sec["title"],
            objective=data["objective"],
            brand=data["brand"],
            fmt=data["format"],
        )
        # A brief now exists → at least 'briefed' (don't downgrade further-along work).
        if sec["status"] == "todo":
            comp.set_section(root, section_id=section_id, status="briefed")
    except (FileNotFoundError, ValueError) as e:
        _fail(str(e))
    click.echo(f"✓ brief scaffolded: {brief_path}")


# ---------------------------------------------------------------- status
@main.command("status")
@_root_opt
def status_cmd(root: Path) -> None:
    """Per-section status + completion rollup + what's blocking assembly."""
    try:
        data = comp.read(root.expanduser())
    except FileNotFoundError as e:
        _fail(str(e))
    click.echo(f"{data['objective']}")
    click.echo(
        f"  brand={data['brand']}  format={data['format']}  v{data['current']}\n"
    )
    marks = {"todo": "·", "briefed": "○", "drafted": "◐", "approved": "●"}
    if not data["sections"]:
        click.echo("  (no sections yet — `planner section add`)")
    for sec in data["sections"]:
        viz = "  +viz" if sec["viz"] else ""
        ds = f"  [{len(sec['data_sources'])} data]" if sec["data_sources"] else ""
        click.echo(
            f"  {marks.get(sec['status'], '?')} {sec['order']:>2}. "
            f"{sec['id']:<28} {sec['status']:<9}{ds}{viz}"
        )
    r = data["rollup"]
    click.echo(
        f"\n  {r['approved']}/{r['total']} approved ({r['percent_approved']}%)  ·  "
        + ("READY to assemble" if r["ready_to_assemble"] else "not ready")
    )
    if not r["ready_to_assemble"]:
        blocking = [s["id"] for s in data["sections"] if s["status"] != "approved"]
        if blocking:
            click.echo(f"  blocking: {', '.join(blocking)}")


# ---------------------------------------------------------------- assemble
@main.command("assemble")
@_root_opt
@click.option(
    "--bump",
    "bump_kind",
    default="minor",
    type=click.Choice(["patch", "minor", "major"]),
)
@click.option(
    "--allow-partial",
    is_flag=True,
    default=False,
    help="Assemble approved sections even if some sections aren't approved yet.",
)
def assemble_cmd(root: Path, bump_kind: str, allow_partial: bool) -> None:
    """Merge approved sections → <session>/inputs/source.md and print the render handoff."""
    try:
        result = assemble_mod.assemble(
            root.expanduser(), bump_kind=bump_kind, allow_partial=allow_partial
        )
    except (FileNotFoundError, assemble_mod.AssembleError) as e:
        _fail(str(e))
    click.echo(f"✓ assembled v{result['version']}: {result['source']}")
    click.echo(
        f"  merged {len(result['sections'])} section(s): {', '.join(result['sections'])}"
    )
    if result["skipped_empty"]:
        click.echo(f"  ⚠ skipped empty: {', '.join(result['skipped_empty'])}", err=True)
    click.echo("\n  next (design renders the branded final):")
    click.echo(f"    {result['render_hint']}")


# ---------------------------------------------------------------- doctor
@main.command("doctor")
def doctor_cmd() -> None:
    """Report whether the planner is wired up to scaffold + hand off to design."""
    rep = deps_mod.doctor()
    click.echo(f"planner {rep['version']}")
    if rep["studio_cli"]:
        click.echo(f"  ✓ design studio CLI  ({rep['studio_cli']})")
    else:
        click.echo(
            "  ✗ design studio CLI  →  run `design/install.sh` (needed to scaffold + render)"
        )
    click.echo(
        "\nNotes:\n"
        "  • The planner plans + assembles; it never renders. `assemble` hands a\n"
        "    merged source.md to the design studio's render-asset.\n"
        "  • Section research uses the LLM host's web tools (not this package)."
    )


# ---------------------------------------------------------------- helpers
def _slugify(text: str) -> str:
    out = []
    prev_dash = False
    for ch in text.lower().strip():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")[:60] or "untitled"


if __name__ == "__main__":
    main()
