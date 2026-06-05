"""Click entry point for the ``delivery`` CLI.

Subcommands mirror the skill 1:1. Judgment stays in the skill; this is glue.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import click
import yaml

from . import __version__
from . import deps as deps_mod
from . import plan as plan_mod
from . import raid as raid_mod
from . import store


def _die(msg: str, *, code: int = 2) -> None:
    click.echo(msg, err=True)
    sys.exit(code)


@click.group()
@click.version_option(__version__, prog_name="delivery")
def main() -> None:
    """Delivery studio — plan-delivery (swimlanes / phases / resourcing / RAID)."""


@main.command()
def doctor() -> None:
    """Report studio wiring: store, optional commercial-CLI reuse."""
    click.echo(yaml.safe_dump(deps_mod.doctor(), sort_keys=False))


# ----------------------------------------------------------------- plan


@main.group()
def plan() -> None:
    """Engagement-level delivery plan."""


@plan.command("new")
@click.option(
    "--engagement", "slug", required=True, help="engagement slug (kebab-case)"
)
@click.option("--brief", type=click.Path(exists=True, dir_okay=False))
def plan_new(slug: str, brief: str | None) -> None:
    try:
        data = store.scaffold(slug, brief=Path(brief) if brief else None)
    except ValueError as e:
        _die(str(e))
    click.echo(f"scaffolded engagement '{slug}' at {store.engagement_dir(slug)}")
    click.echo(yaml.safe_dump(data, sort_keys=False))


@plan.command("materialise")
@click.option("--engagement", "slug", required=True)
@click.option(
    "--plan-json",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="caller-produced plan JSON / YAML (schema in the SKILL)",
)
@click.option(
    "--bump", "level", default="patch", type=click.Choice(["patch", "minor", "major"])
)
def plan_materialise(slug: str, plan_json: str, level: str) -> None:
    try:
        data = plan_mod.materialise(slug, Path(plan_json))
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    version = store.bump(slug, level=level)
    click.echo(f"v{version}: wrote {store.plan_path(slug)}")
    rollup = data.get("rollups") or {}
    click.echo(
        f"  total_days={rollup.get('total_days', '?')}  "
        f"buffer={rollup.get('buffer_days', '?')}  "
        f"contingency_pct={rollup.get('contingency_pct', '?')}%  "
        f"phases={rollup.get('phase_count', '?')}  "
        f"swimlanes={rollup.get('swimlane_count', '?')}"
    )


@plan.command("show")
@click.option("--engagement", "slug", required=True)
def plan_show(slug: str) -> None:
    try:
        data = store.read_plan(slug)
    except FileNotFoundError as e:
        _die(str(e))
    click.echo(yaml.safe_dump(data, sort_keys=False))


@plan.command("list")
def plan_list() -> None:
    rows = store.list_engagements()
    click.echo("\n".join(rows) if rows else "(no engagements yet)")


@plan.command("cost")
@click.option("--engagement", "slug", required=True)
def plan_cost(slug: str) -> None:
    """Cost the resourcing via the commercial studio's rate-card.

    Degrades cleanly when the commercial CLI isn't installed.
    """
    if not deps_mod.commercial_reachable():
        _die(
            "commercial CLI not reachable — install with `../commercial/install.sh` "
            "(plan cost reuses the commercial rate-card)",
            code=2,
        )
    try:
        plan_data = store.read_plan(slug)
    except FileNotFoundError as e:
        _die(str(e))

    cmd = [deps_mod._commercial_binary(), "rate-card", "show"]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        _die(
            f"`commercial rate-card show` failed: {proc.stderr or proc.stdout}", code=3
        )
    rate_card = yaml.safe_load(proc.stdout) or {}
    role_idx = {r["role"]: r for r in rate_card.get("roles", [])}

    out_phases = []
    grand_rev = grand_cost = 0.0
    for ph in plan_data.get("phases") or []:
        rev = 0.0
        cost = 0.0
        for r in ph.get("resourcing") or []:
            role = r.get("role")
            days = float(r.get("days", 0))
            spec = role_idx.get(role) or {}
            rev += float(spec.get("rate", 0)) * days
            cost += float(spec.get("cost", 0)) * days
        margin = (rev - cost) / rev if rev else 0.0
        out_phases.append(
            {
                "id": ph.get("id"),
                "revenue": rev,
                "cost": cost,
                "margin": round(margin, 3),
            }
        )
        grand_rev += rev
        grand_cost += cost
    grand_margin = (grand_rev - grand_cost) / grand_rev if grand_rev else 0.0
    click.echo(
        yaml.safe_dump(
            {
                "engagement": slug,
                "currency": rate_card.get("currency", "USD"),
                "unit": rate_card.get("unit", "day"),
                "phases": out_phases,
                "total": {
                    "revenue": grand_rev,
                    "cost": grand_cost,
                    "margin": round(grand_margin, 3),
                },
            },
            sort_keys=False,
        )
    )


# ----------------------------------------------------------------- raid


@main.group()
def raid() -> None:
    """First-class RAID register: risks / assumptions / issues / dependencies."""


@raid.command("add")
@click.option("--engagement", "slug", required=True)
@click.option("--kind", required=True, type=click.Choice(list(raid_mod.KINDS)))
@click.option("--title", required=True)
@click.option(
    "--severity", default="medium", type=click.Choice(list(raid_mod.SEVERITIES))
)
@click.option("--owner")
@click.option("--notes")
def raid_add(
    slug: str,
    kind: str,
    title: str,
    severity: str,
    owner: str | None,
    notes: str | None,
) -> None:
    try:
        item = raid_mod.add(
            slug, kind=kind, title=title, severity=severity, owner=owner, notes=notes
        )
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    click.echo(yaml.safe_dump(item, sort_keys=False))


@raid.command("resolve")
@click.option("--engagement", "slug", required=True)
@click.option("--id", "raid_id", required=True)
@click.option("--resolution", required=True)
def raid_resolve(slug: str, raid_id: str, resolution: str) -> None:
    try:
        item = raid_mod.resolve(slug, raid_id=raid_id, resolution=resolution)
    except (FileNotFoundError, KeyError) as e:
        _die(str(e))
    click.echo(yaml.safe_dump(item, sort_keys=False))


@raid.command("show")
@click.option("--engagement", "slug", required=True)
@click.option("--kind", type=click.Choice(list(raid_mod.KINDS)))
def raid_show(slug: str, kind: str | None) -> None:
    try:
        items = raid_mod.show(slug, kind=kind)
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    if not items:
        click.echo("(no entries)")
        return
    for it in items:
        click.echo(
            f"{it['id']}  {it['kind']:<11}  {it.get('severity', '?'):<8}  "
            f"{it['status']:<8}  {it['title']}"
        )


@raid.command("summary")
@click.option("--engagement", "slug", required=True)
def raid_summary_cmd(slug: str) -> None:
    try:
        s = raid_mod.summary(slug)
    except FileNotFoundError as e:
        _die(str(e))
    click.echo(yaml.safe_dump(s, sort_keys=False))


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
