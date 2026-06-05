"""Click entry point for the ``engagement`` CLI.

Subcommands mirror the engagement skill 1:1. Judgment lives in the
skill (``skills/engagement/SKILL.md``); this is glue.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from . import __version__
from . import autonomy as autonomy_mod
from . import checkpoints as cp_mod
from . import decisions as dec_mod
from . import items as items_mod
from . import jobs as jobs_mod
from . import manifest as man


def _die(msg: str, *, code: int = 2) -> None:
    click.echo(msg, err=True)
    sys.exit(code)


@click.group()
@click.version_option(__version__, prog_name="engagement")
def main() -> None:
    """Engagement-level manifest (engagement.json) over a production docket."""


# ----------------------------------------------------------------- new + status


@main.command("new")
@click.option(
    "--root", required=True, type=click.Path(file_okay=False), help="docket root"
)
@click.option("--engagement", required=True, help="engagement slug")
@click.option("--objective")
@click.option("--audience")
@click.option("--client")
def new_cmd(
    root: str,
    engagement: str,
    objective: str | None,
    audience: str | None,
    client: str | None,
) -> None:
    try:
        data = man.new(
            Path(root),
            engagement_slug=engagement,
            objective=objective,
            audience=audience,
            client=client,
        )
    except ValueError as e:
        _die(str(e))
    click.echo(f"wrote {man.path_for(Path(root))}")
    click.echo(json.dumps(data["rollup"], indent=2))


@main.command("status")
@click.option("--root", required=True, type=click.Path(file_okay=False))
@click.option("--set", "new_status", help="new engagement status")
def status_cmd(root: str, new_status: str | None) -> None:
    """Print the deterministic rollup; or set the engagement status."""
    r = Path(root)
    if new_status:
        try:
            data = man.set_status(r, new_status)
        except (FileNotFoundError, ValueError) as e:
            _die(str(e))
        click.echo(
            json.dumps({"status": data["status"], "rollup": data["rollup"]}, indent=2)
        )
        return
    try:
        data = man.read(r)
    except FileNotFoundError as e:
        _die(str(e))
    click.echo(
        json.dumps(
            {
                "engagement": data["engagement"],
                "status": data["status"],
                "rollup": data["rollup"],
            },
            indent=2,
        )
    )


@main.command("brief")
@click.option("--root", required=True, type=click.Path(file_okay=False))
@click.option("--objective")
@click.option("--audience")
@click.option("--client")
@click.option("--constraint", "constraints", multiple=True, help="repeatable")
@click.option("--success", "success_criteria", multiple=True, help="repeatable")
def brief_cmd(
    root: str,
    objective: str | None,
    audience: str | None,
    client: str | None,
    constraints: tuple[str, ...],
    success_criteria: tuple[str, ...],
) -> None:
    try:
        data = man.set_brief(
            Path(root),
            objective=objective,
            audience=audience,
            client=client,
            constraints=list(constraints) if constraints else None,
            success_criteria=list(success_criteria) if success_criteria else None,
        )
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    click.echo(json.dumps(data["brief"], indent=2))


# ----------------------------------------------------------------- cast


@main.group()
def cast() -> None:
    """Cast — chosen roles + their justification."""


@cast.command("add")
@click.option("--root", required=True, type=click.Path(file_okay=False))
@click.option("--role", required=True)
@click.option("--justification")
def cast_add(root: str, role: str, justification: str | None) -> None:
    try:
        man.add_cast(Path(root), role=role, justification=justification)
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    click.echo(f"+ cast: {role}")


# ----------------------------------------------------------------- jobs


@main.group()
def job() -> None:
    """Jobs — invocations of capabilities within the engagement."""


@job.command("add")
@click.option("--root", required=True, type=click.Path(file_okay=False))
@click.option("--capability", required=True)
@click.option("--role")
@click.option("--title")
@click.option(
    "--action-class",
    default="L1",
    type=click.Choice(list(autonomy_mod.ACTION_CLASSES)),
    help="Bible §6 autonomy class — L0 gather / L1 draft / L2 decide / L3 deliver",
)
def job_add(
    root: str,
    capability: str,
    role: str | None,
    title: str | None,
    action_class: str,
) -> None:
    try:
        j = jobs_mod.add(
            Path(root),
            capability=capability,
            role=role,
            title=title,
            action_class=action_class,
        )
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    click.echo(json.dumps(j, indent=2))


@job.command("set")
@click.option("--root", required=True, type=click.Path(file_okay=False))
@click.option("--id", "job_id", required=True)
@click.option("--status", required=True, type=click.Choice(list(man.JOB_STATUSES)))
def job_set(root: str, job_id: str, status: str) -> None:
    try:
        j = jobs_mod.set_status(Path(root), job_id=job_id, status=status)
    except autonomy_mod.AutonomyError as e:
        # Exit code 4 = autonomy contract violation (distinct from generic
        # input errors at 2). The Producer / Principal can branch on it.
        click.echo(f"autonomy violation [{e.rule}]: {e}", err=True)
        sys.exit(4)
    except (FileNotFoundError, KeyError, ValueError) as e:
        _die(str(e))
    click.echo(json.dumps(j, indent=2))


@job.command("list")
@click.option("--root", required=True, type=click.Path(file_okay=False))
@click.option("--status", help="filter by status")
def job_list(root: str, status: str | None) -> None:
    try:
        rows = jobs_mod.list_jobs(Path(root), status=status)
    except FileNotFoundError as e:
        _die(str(e))
    for j in rows:
        click.echo(
            f"{j['id']}  {j.get('action_class','L1')}  "
            f"{j.get('status','?'):<13}  {j['capability']:<26}  "
            f"{j.get('role','-'):<14}  {j.get('title','')}"
        )


# ----------------------------------------------------------------- autonomy


@main.command()
@click.option("--root", required=True, type=click.Path(file_okay=False))
def autonomy(root: str) -> None:
    """Per-job autonomy state (Bible §6) — what can complete, what's blocked."""
    try:
        data = man.read(Path(root))
    except FileNotFoundError as e:
        _die(str(e))
    rows = autonomy_mod.autonomy_state(data)
    for r in rows:
        marker = "✓" if r["can_complete"] else ("·" if r["status"] == "done" else "⛔")
        click.echo(
            f"{marker} {r['id']}  {r['action_class']}  {r['status']:<13}  "
            + ("blocked: " + "; ".join(r["blocked_by"]) if r["blocked_by"] else "free")
        )
    counts = autonomy_mod.rollup_counts(data)
    click.echo("")
    click.echo(
        f"summary: awaiting_l2={counts['awaiting_l2']}  "
        f"awaiting_l3={counts['awaiting_l3']}  "
        f"by_action_class={counts['by_action_class']}"
    )


# ----------------------------------------------------------------- items (Q/B/R)


@main.group()
def item() -> None:
    """First-class items: questions / blockers / risks (Bible §8)."""


@item.command("add")
@click.option("--root", required=True, type=click.Path(file_okay=False))
@click.option("--kind", required=True, type=click.Choice(list(man.ITEM_KINDS)))
@click.option("--title", required=True)
@click.option("--raised-by")
@click.option("--needs", type=click.Choice(list(items_mod.NEEDS)))
@click.option("--blocking", "blocking_jobs", multiple=True, help="repeatable job id")
def item_add(
    root: str,
    kind: str,
    title: str,
    raised_by: str | None,
    needs: str | None,
    blocking_jobs: tuple[str, ...],
) -> None:
    try:
        it = items_mod.add(
            Path(root),
            kind=kind,
            title=title,
            raised_by_role=raised_by,
            needs=needs,
            blocking_jobs=list(blocking_jobs) if blocking_jobs else None,
        )
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    click.echo(json.dumps(it, indent=2))


@item.command("resolve")
@click.option("--root", required=True, type=click.Path(file_okay=False))
@click.option("--kind", required=True, type=click.Choice(list(man.ITEM_KINDS)))
@click.option("--id", "item_id", required=True)
@click.option("--resolution", required=True)
@click.option(
    "--status", default="resolved", type=click.Choice(list(man.ITEM_STATUSES))
)
def item_resolve(
    root: str, kind: str, item_id: str, resolution: str, status: str
) -> None:
    try:
        it = items_mod.resolve(
            Path(root), kind=kind, item_id=item_id, resolution=resolution, status=status
        )
    except (FileNotFoundError, KeyError, ValueError) as e:
        _die(str(e))
    click.echo(json.dumps(it, indent=2))


@item.command("show")
@click.option("--root", required=True, type=click.Path(file_okay=False))
@click.option("--kind", type=click.Choice(list(man.ITEM_KINDS)))
@click.option("--status", type=click.Choice(list(man.ITEM_STATUSES)))
def item_show(root: str, kind: str | None, status: str | None) -> None:
    try:
        rows = items_mod.show(Path(root), kind=kind, status=status)
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    if not rows:
        click.echo("(none)")
        return
    for r in rows:
        click.echo(
            f"{r['id']}  {r['kind']:<9}  {r['status']:<10}  {r.get('needs','-'):<7}  "
            f"{r['title']}"
        )


# ----------------------------------------------------------------- decisions


@main.group()
def decision() -> None:
    """Decisions — pointers to ADR-style records (Bible §7)."""


@decision.command("add")
@click.option("--root", required=True, type=click.Path(file_okay=False))
@click.option("--title", required=True)
@click.option("--ref", help="path or URL of the decision record")
@click.option("--role")
@click.option("--summary")
def decision_add(
    root: str, title: str, ref: str | None, role: str | None, summary: str | None
) -> None:
    try:
        d = dec_mod.add(Path(root), title=title, ref=ref, role=role, summary=summary)
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    click.echo(json.dumps(d, indent=2))


@decision.command("show")
@click.option("--root", required=True, type=click.Path(file_okay=False))
def decision_show(root: str) -> None:
    try:
        rows = dec_mod.show(Path(root))
    except FileNotFoundError as e:
        _die(str(e))
    for d in rows:
        click.echo(f"{d['id']}  {d.get('role','-'):<14}  {d['title']}")
        if d.get("ref"):
            click.echo(f"  → {d['ref']}")


# ----------------------------------------------------------------- checkpoints


@main.group()
def checkpoint() -> None:
    """L2 / L3 checkpoints (Bible §6)."""


@checkpoint.command("open")
@click.option("--root", required=True, type=click.Path(file_okay=False))
@click.option("--level", required=True, type=click.Choice(list(man.CHECKPOINT_LEVELS)))
@click.option("--title", required=True)
@click.option("--raised-by")
@click.option("--blocking", "blocking_jobs", multiple=True)
@click.option("--evidence")
def checkpoint_open(
    root: str,
    level: str,
    title: str,
    raised_by: str | None,
    blocking_jobs: tuple[str, ...],
    evidence: str | None,
) -> None:
    try:
        cp = cp_mod.open_checkpoint(
            Path(root),
            level=level,
            title=title,
            raised_by_role=raised_by,
            blocking_jobs=list(blocking_jobs) if blocking_jobs else None,
            evidence=evidence,
        )
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    click.echo(json.dumps(cp, indent=2))


@checkpoint.command("clear")
@click.option("--root", required=True, type=click.Path(file_okay=False))
@click.option("--id", "checkpoint_id", required=True)
@click.option("--outcome", required=True)
@click.option(
    "--status", default="cleared", type=click.Choice(list(man.CHECKPOINT_STATUSES))
)
@click.option("--decided-by")
def checkpoint_clear(
    root: str,
    checkpoint_id: str,
    outcome: str,
    status: str,
    decided_by: str | None,
) -> None:
    try:
        cp = cp_mod.clear(
            Path(root),
            checkpoint_id=checkpoint_id,
            outcome=outcome,
            status=status,
            decided_by=decided_by,
        )
    except (FileNotFoundError, KeyError, ValueError) as e:
        _die(str(e))
    click.echo(json.dumps(cp, indent=2))


@checkpoint.command("show")
@click.option("--root", required=True, type=click.Path(file_okay=False))
@click.option("--status", type=click.Choice(list(man.CHECKPOINT_STATUSES)))
def checkpoint_show(root: str, status: str | None) -> None:
    try:
        rows = cp_mod.show(Path(root), status=status)
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    for cp in rows:
        click.echo(
            f"{cp['id']}  {cp['level']}  {cp['status']:<9}  "
            f"{cp.get('raised_by_role','-'):<14}  {cp['title']}"
        )


if __name__ == "__main__":
    main()
