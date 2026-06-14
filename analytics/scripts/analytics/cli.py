"""Click entry point for the ``analytics`` CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import yaml

from . import __version__
from . import analysis as analysis_mod
from . import deps as deps_mod
from . import store


def _die(msg: str, *, code: int = 2) -> None:
    click.echo(msg, err=True)
    sys.exit(code)


@click.group()
@click.version_option(__version__, prog_name="analytics")
def main() -> None:
    """Analytics studio — analyse-data (caller-supplied-JSON materialiser)."""


@main.command()
def doctor() -> None:
    click.echo(yaml.safe_dump(deps_mod.doctor(), sort_keys=False))


@main.group()
def analysis() -> None:
    """Per-engagement structured analysis."""


@analysis.command("new")
@click.option("--engagement", "slug", required=True)
@click.option("--brief", type=click.Path(exists=True, dir_okay=False))
def analysis_new(slug: str, brief: str | None) -> None:
    try:
        data = store.scaffold(slug, brief=Path(brief) if brief else None)
    except ValueError as e:
        _die(str(e))
    click.echo(f"scaffolded engagement '{slug}' at {store.engagement_dir(slug)}")
    click.echo(yaml.safe_dump(data, sort_keys=False))


@analysis.command("materialise")
@click.option("--engagement", "slug", required=True)
@click.option(
    "--analysis-json",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="caller-produced analysis JSON / YAML (schema in the SKILL)",
)
@click.option(
    "--bump", "level", default="patch", type=click.Choice(["patch", "minor", "major"])
)
def analysis_materialise(slug: str, analysis_json: str, level: str) -> None:
    try:
        data = analysis_mod.materialise(slug, Path(analysis_json))
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    version = store.bump(slug, level=level)
    click.echo(f"v{version}: wrote {store.analysis_path(slug)}")
    r = data.get("rollups") or {}
    click.echo(
        f"  patterns={r.get('pattern_count', 0)}  "
        f"insights={r.get('insight_count', 0)}  "
        f"recommendations={r.get('recommendation_count', 0)}  "
        f"sample_size={r.get('sample_size', '?')}"
    )
    by_sev = r.get("insights_by_severity") or {}
    if by_sev:
        click.echo(
            "  insights by severity: "
            + ", ".join(f"{k}={v}" for k, v in by_sev.items())
        )


@analysis.command("show")
@click.option("--engagement", "slug", required=True)
def analysis_show(slug: str) -> None:
    try:
        click.echo(yaml.safe_dump(store.read_analysis(slug), sort_keys=False))
    except FileNotFoundError as e:
        _die(str(e))


@analysis.command("list")
def analysis_list() -> None:
    rows = store.list_engagements()
    click.echo("\n".join(rows) if rows else "(no engagements yet)")


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
