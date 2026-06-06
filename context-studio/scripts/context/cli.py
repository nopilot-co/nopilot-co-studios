"""Click entry point for the ``context`` CLI."""

from __future__ import annotations

import json
import sys

import click
import yaml

from . import __version__
from . import deps as deps_mod
from . import pipeline
from . import store


def _die(msg: str, *, code: int = 2) -> None:
    click.echo(msg, err=True)
    sys.exit(code)


@click.group()
@click.version_option(__version__, prog_name="context")
def main() -> None:
    """Context studio — ingest / map / extend an engagement's context store
    by orchestrating the tools/ tier."""


@main.command()
def doctor() -> None:
    click.echo(yaml.safe_dump(deps_mod.doctor(), sort_keys=False))


# ----------------------------------------------------------------- engagement


@main.group()
def engagement() -> None:
    """Per-engagement context store."""


@engagement.command("new")
@click.option("--engagement", "slug", required=True)
def engagement_new(slug: str) -> None:
    try:
        data = store.scaffold(slug)
    except ValueError as e:
        _die(str(e))
    click.echo(f"scaffolded engagement '{slug}' at {store.engagement_dir(slug)}")
    click.echo(yaml.safe_dump(data, sort_keys=False))


@engagement.command("list")
def engagement_list() -> None:
    rows = store.list_engagements()
    click.echo("\n".join(rows) if rows else "(no engagements yet)")


@engagement.command("show")
@click.option("--engagement", "slug", required=True)
def engagement_show(slug: str) -> None:
    try:
        click.echo(json.dumps(store.read_manifest(slug), indent=2))
    except FileNotFoundError as e:
        _die(str(e))


# ----------------------------------------------------------------- ingest


@main.command()
@click.option("--engagement", "slug", required=True)
@click.option("--notion-db", help="Notion database id")
@click.option("--source", help="path or URL of a single source")
@click.option(
    "--kind",
    default="file",
    type=click.Choice(["file", "url"]),
    help="how to handle --source (file copy or URL stub)",
)
@click.option("--youtube", help="YouTube URL")
@click.option("--enrich", is_flag=True, help="run source-enrich on the batch")
@click.option("--summarise", is_flag=True, help="run source-summarise")
@click.option(
    "--summary-json",
    type=click.Path(exists=True, dir_okay=False),
    help="caller-supplied summaries JSON (required with --summarise)",
)
def ingest(
    slug: str,
    notion_db: str | None,
    source: str | None,
    kind: str,
    youtube: str | None,
    enrich: bool,
    summarise: bool,
    summary_json: str | None,
) -> None:
    """Orchestrate the ingest pipeline. Exactly one of the source-supplying
    flags should be set per call (notion-db / source / youtube / enrich /
    summarise)."""
    if not store.engagement_exists(slug):
        _die(
            f"no engagement '{slug}' — run `context engagement new --engagement {slug}`"
        )

    if notion_db:
        out = pipeline.ingest_notion(slug, database=notion_db)
        _emit_result("notion-sources", out)
        return
    if youtube:
        out = pipeline.ingest_youtube(slug, url=youtube)
        _emit_result("yt-transcript", out)
        return
    if source:
        out = pipeline.ingest_source(slug, source=source, kind=kind)
        _emit_result(f"add-{kind}", out)
        return
    if enrich:
        out = pipeline.ingest_enrich(slug)
        _emit_result("source-enrich", out)
        return
    if summarise:
        if not summary_json:
            _die("--summarise requires --summary-json")
        out = pipeline.ingest_summarise(slug, summary_json=summary_json)
        _emit_result("source-summarise", out)
        return

    _die(
        "one of --notion-db / --source / --youtube / --enrich / --summarise must be set"
    )


# ----------------------------------------------------------------- map


@main.command()
@click.option("--engagement", "slug", required=True)
@click.option("--propose", is_flag=True, help="theme-propose (scan or materialise)")
@click.option(
    "--proposal-json",
    type=click.Path(exists=True, dir_okay=False),
    help="caller-supplied proposal JSON (with --propose)",
)
@click.option(
    "--adopt",
    type=click.Path(exists=True, dir_okay=False),
    help="agreed proposal/manifest JSON to freeze",
)
@click.option("--cluster", is_flag=True, help="theme-cluster")
@click.option(
    "--assignments",
    type=click.Path(exists=True, dir_okay=False),
    help="caller-supplied assignments JSON (with --cluster)",
)
@click.option("--entity", is_flag=True, help="theme-entity")
@click.option(
    "--spec",
    type=click.Path(exists=True, dir_okay=False),
    help="caller-supplied synthesis JSON (with --entity)",
)
def map_cmd(
    slug: str,
    propose: bool,
    proposal_json: str | None,
    adopt: str | None,
    cluster: bool,
    assignments: str | None,
    entity: bool,
    spec: str | None,
) -> None:
    """Orchestrate the map pipeline."""
    if not store.engagement_exists(slug):
        _die(
            f"no engagement '{slug}' — run `context engagement new --engagement {slug}`"
        )
    if propose or adopt:
        out = pipeline.map_propose(slug, proposal_json=proposal_json, adopt=adopt)
        _emit_result("theme-propose", out)
        return
    if cluster:
        if not assignments:
            _die("--cluster requires --assignments")
        out = pipeline.map_cluster(slug, assignments=assignments)
        _emit_result("theme-cluster", out)
        return
    if entity:
        if not spec:
            _die("--entity requires --spec")
        out = pipeline.map_entity(slug, spec=spec)
        _emit_result("theme-entity", out)
        return
    _die("one of --propose / --adopt / --cluster / --entity must be set")


# Click reserves `map` at the group level via add_command; we expose it under
# the same name explicitly to keep the help text clean.
map_cmd.name = "map"


# ----------------------------------------------------------------- extend


@main.command()
@click.option("--engagement", "slug", required=True)
@click.option("--source", help="path or URL of the new source")
@click.option(
    "--kind",
    default="file",
    type=click.Choice(["file", "url", "youtube"]),
)
@click.option("--enrich", is_flag=True, help="run source-enrich incrementally")
@click.option("--remap", is_flag=True, help="re-trigger map-context (user follows up)")
def extend(slug: str, source: str | None, kind: str, enrich: bool, remap: bool) -> None:
    if not store.engagement_exists(slug):
        _die(f"no engagement '{slug}'")
    if source:
        if kind == "youtube":
            out = pipeline.ingest_youtube(slug, url=source)
        else:
            out = pipeline.ingest_source(slug, source=source, kind=kind)
        _emit_result(f"add-{kind}", out)
    if enrich:
        out = pipeline.ingest_enrich(slug)
        _emit_result("source-enrich", out)
    if remap:
        click.echo(
            "remap requested — run `context map --engagement {} --propose` to "
            "start a fresh map cycle".format(slug)
        )


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


def _emit_result(name: str, result: dict) -> None:
    if result.get("ok"):
        click.echo(f"✓ {name}")
        if result.get("dest"):
            click.echo(f"  → {result['dest']}")
        if result.get("out"):
            click.echo(f"  → {result['out']}")
    else:
        click.echo(f"✗ {name} (returncode={result.get('returncode', '?')})", err=True)
        if result.get("stderr"):
            click.echo(result["stderr"], err=True)
        sys.exit(3)


if __name__ == "__main__":
    main()
