"""Click entry point for the ``growth`` CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import yaml

from . import __version__
from . import deps as deps_mod
from . import leads as leads_mod
from . import market as market_mod
from . import store


def _die(msg: str, *, code: int = 2) -> None:
    click.echo(msg, err=True)
    sys.exit(code)


@click.group()
@click.version_option(__version__, prog_name="growth")
def main() -> None:
    """Growth/BD studio — generate-leads + map-market."""


@main.command()
def doctor() -> None:
    click.echo(yaml.safe_dump(deps_mod.doctor(), sort_keys=False))


# ---------------- leads


@main.group()
def leads() -> None:
    """Lead list materialiser."""


@leads.command("new")
@click.option("--engagement", "slug", required=True)
def leads_new(slug: str) -> None:
    try:
        data = store.scaffold(slug)
    except ValueError as e:
        _die(str(e))
    click.echo(yaml.safe_dump(data, sort_keys=False))


@leads.command("materialise")
@click.option("--engagement", "slug", required=True)
@click.option(
    "--leads-json",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--bump", "level", default="patch", type=click.Choice(["patch", "minor", "major"])
)
def leads_materialise(slug: str, leads_json: str, level: str) -> None:
    try:
        data = leads_mod.materialise(slug, Path(leads_json))
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    version = store.bump(slug, level=level)
    r = data["rollups"]
    click.echo(f"v{version}: wrote {store.leads_path(slug)}")
    click.echo(
        f"  count={r['count']}  by_fit={r['by_fit']}  by_source={r['by_source']}"
    )


@leads.command("show")
@click.option("--engagement", "slug", required=True)
def leads_show(slug: str) -> None:
    try:
        click.echo(yaml.safe_dump(store.read_leads(slug), sort_keys=False))
    except FileNotFoundError as e:
        _die(str(e))


# ---------------- market


@main.group()
def market() -> None:
    """Market-map materialiser."""


@market.command("new")
@click.option("--engagement", "slug", required=True)
def market_new(slug: str) -> None:
    try:
        data = store.scaffold(slug)
    except ValueError as e:
        # If the engagement already exists from a prior leads-new, that's
        # fine — leads + market share the engagement store.
        if "already exists" in str(e):
            data = store.read_version(slug)
        else:
            _die(str(e))
    click.echo(yaml.safe_dump(data, sort_keys=False))


@market.command("materialise")
@click.option("--engagement", "slug", required=True)
@click.option(
    "--market-json",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--bump", "level", default="patch", type=click.Choice(["patch", "minor", "major"])
)
def market_materialise(slug: str, market_json: str, level: str) -> None:
    try:
        data = market_mod.materialise(slug, Path(market_json))
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    version = store.bump(slug, level=level)
    r = data["rollups"]
    click.echo(f"v{version}: wrote {store.market_path(slug)}")
    click.echo(
        f"  segments={r['segment_count']}  competitors={r['competitor_count']}  "
        f"by_quadrant={r['competitors_by_quadrant']}"
    )


@market.command("show")
@click.option("--engagement", "slug", required=True)
def market_show(slug: str) -> None:
    try:
        click.echo(yaml.safe_dump(store.read_market(slug), sort_keys=False))
    except FileNotFoundError as e:
        _die(str(e))


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
