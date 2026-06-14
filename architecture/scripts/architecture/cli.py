"""Click entry point for the ``arch`` CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import yaml

from . import __version__
from . import adr as adr_mod
from . import deps as deps_mod
from . import design_bridge
from . import spec as spec_mod
from . import store


def _die(msg: str, *, code: int = 2) -> None:
    click.echo(msg, err=True)
    sys.exit(code)


@click.group()
@click.version_option(__version__, prog_name="arch")
def main() -> None:
    """Architecture studio — design-architecture (systems / flows / integrations / ADRs)."""


@main.command()
def doctor() -> None:
    click.echo(yaml.safe_dump(deps_mod.doctor(), sort_keys=False))


# ----------------------------------------------------------------- spec


@main.group()
def spec() -> None:
    """Architecture spec (systems / data flows / integrations)."""


@spec.command("new")
@click.option("--engagement", "slug", required=True)
@click.option("--brief", type=click.Path(exists=True, dir_okay=False))
def spec_new(slug: str, brief: str | None) -> None:
    try:
        data = store.scaffold(slug, brief=Path(brief) if brief else None)
    except ValueError as e:
        _die(str(e))
    click.echo(f"scaffolded engagement '{slug}' at {store.engagement_dir(slug)}")
    click.echo(yaml.safe_dump(data, sort_keys=False))


@spec.command("materialise")
@click.option("--engagement", "slug", required=True)
@click.option(
    "--spec-json",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="caller-produced spec JSON / YAML (schema in the SKILL)",
)
@click.option(
    "--bump", "level", default="patch", type=click.Choice(["patch", "minor", "major"])
)
def spec_materialise(slug: str, spec_json: str, level: str) -> None:
    try:
        data = spec_mod.materialise(slug, Path(spec_json))
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    version = store.bump(slug, level=level)
    click.echo(f"v{version}: wrote {store.spec_path(slug)}")
    click.echo(
        f"  systems={len(data.get('systems') or [])}  "
        f"flows={len(data.get('data_flows') or [])}  "
        f"integrations={len(data.get('integrations') or [])}"
    )


@spec.command("show")
@click.option("--engagement", "slug", required=True)
def spec_show(slug: str) -> None:
    try:
        click.echo(yaml.safe_dump(store.read_spec(slug), sort_keys=False))
    except FileNotFoundError as e:
        _die(str(e))


@spec.command("validate")
@click.option("--engagement", "slug", required=True)
def spec_validate(slug: str) -> None:
    try:
        data = store.read_spec(slug)
    except FileNotFoundError as e:
        _die(str(e))
    errs = store.validate_spec_payload(data)
    if errs:
        for e in errs:
            click.echo(f"✗ {e}", err=True)
        sys.exit(2)
    click.echo("✓ spec valid (schema + invariants)")


# ----------------------------------------------------------------- ADR


@main.group()
def adr() -> None:
    """ADR-style decision records."""


@adr.command("add")
@click.option("--engagement", "slug", required=True)
@click.option("--title", required=True)
@click.option("--status", default="proposed", type=click.Choice(list(adr_mod.STATUSES)))
@click.option("--context")
@click.option("--decision")
@click.option("--consequences")
@click.option("--alternatives")
def adr_add(
    slug: str,
    title: str,
    status: str,
    context: str | None,
    decision: str | None,
    consequences: str | None,
    alternatives: str | None,
) -> None:
    if not store.engagement_exists(slug):
        _die(f"no engagement '{slug}' — run `arch spec new --engagement {slug}`")
    try:
        out = adr_mod.add(
            slug,
            title=title,
            status=status,
            context=context,
            decision=decision,
            consequences=consequences,
            alternatives=alternatives,
        )
    except ValueError as e:
        _die(str(e))
    click.echo(yaml.safe_dump(out, sort_keys=False))


@adr.command("show")
@click.option("--engagement", "slug", required=True)
@click.option("--id", "adr_id")
def adr_show(slug: str, adr_id: str | None) -> None:
    items = adr_mod.show(slug, adr_id=adr_id)
    if not items:
        click.echo("(no ADRs)")
        return
    for it in items:
        click.echo(f"{it['id']}  {it['status']:<11}  {it['date']}  {it['title']}")


@adr.command("list")
@click.option("--engagement", "slug", required=True)
def adr_list(slug: str) -> None:
    items = adr_mod.show(slug)
    if not items:
        click.echo("(no ADRs)")
        return
    for it in items:
        click.echo(f"{it['id']}  {it['status']:<11}  {it['title']}")


@adr.command("set-status")
@click.option("--engagement", "slug", required=True)
@click.option("--id", "adr_id", required=True)
@click.option("--status", required=True, type=click.Choice(list(adr_mod.STATUSES)))
def adr_set_status(slug: str, adr_id: str, status: str) -> None:
    try:
        out = adr_mod.set_status(slug, adr_id, status)
    except (KeyError, ValueError) as e:
        _die(str(e))
    click.echo(yaml.safe_dump(out, sort_keys=False))


# ----------------------------------------------------------------- render


@main.command()
@click.option("--engagement", "slug", required=True)
@click.option(
    "--format", "fmt", default="pdf", type=click.Choice(["pdf", "html", "svg"])
)
def render(slug: str, fmt: str) -> None:
    """Render diagrams from the spec via the design studio (degrades cleanly)."""
    try:
        spec_data = store.read_spec(slug)
    except FileNotFoundError as e:
        _die(str(e))
    version = store.read_version(slug)["current"]
    out_dir = store.engagement_dir(slug) / "render" / f"v{version}"
    rendered = design_bridge.render(spec_data, out_dir=out_dir, fmt=fmt)
    if rendered is None:
        click.echo(
            f"design CLI not reachable — wrote diagram source to {out_dir}/architecture.md "
            "but didn't render. Install with `../design/install.sh` to render to "
            f"{fmt}.",
            err=True,
        )
        sys.exit(2)
    click.echo(f"wrote diagram source: {rendered}")


# ----------------------------------------------------------------- status


@main.command()
@click.option("--engagement", "slug", required=True)
@click.option("--set", "new_status", help="new status")
def status(slug: str, new_status: str | None) -> None:
    if new_status:
        try:
            data = store.set_status(slug, new_status)
        except (FileNotFoundError, ValueError) as e:
            _die(str(e))
        click.echo(yaml.safe_dump(data, sort_keys=False))
        return
    if not store.engagement_exists(slug):
        _die(f"no engagement '{slug}'")
    click.echo(json.dumps(store.read_version(slug), indent=2))


if __name__ == "__main__":
    main()
