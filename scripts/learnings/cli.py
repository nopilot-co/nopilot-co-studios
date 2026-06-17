"""Click entry point for the ``learnings`` CLI.

Subcommands mirror the ``reflect`` skill 1:1. Judgment lives in the skill
(``skills/reflect/SKILL.md``); this is glue (file ops, schema, id allocation).
"""

from __future__ import annotations

import json
import shlex
import sys

import click

from . import __version__
from . import deps as deps_mod
from . import store


def _die(msg: str, *, code: int = 2) -> None:
    click.echo(msg, err=True)
    sys.exit(code)


@click.group()
@click.version_option(__version__, prog_name="learnings")
def main() -> None:
    """Append-only plugin-improvement learnings for the studios plugin."""


# ----------------------------------------------------------------- add / none


@main.command("add")
@click.option("--studio", required=True, help="studio slug, or 'cross' for orchestration")
@click.option(
    "--category",
    required=True,
    type=click.Choice([c for c in store.CATEGORIES if c != "none"]),
)
@click.option("--severity", default="medium", type=click.Choice(list(store.SEVERITIES)))
@click.option("--title", required=True)
@click.option("--proposed-change", "proposed_change")
@click.option("--engagement", default="")
@click.option("--body", "body")
def add_cmd(
    studio: str,
    category: str,
    severity: str,
    title: str,
    proposed_change: str | None,
    engagement: str,
    body: str | None,
) -> None:
    """Record one plugin-improvement learning."""
    try:
        rec = store.add(
            studio=studio,
            category=category,
            severity=severity,
            title=title,
            proposed_change=proposed_change,
            engagement=engagement,
            body=body,
        )
    except ValueError as e:
        _die(str(e))
    click.echo(f"wrote {rec['path']}")


@main.command("none")
@click.option("--engagement", default="")
@click.option("--reason", required=True)
def none_cmd(engagement: str, reason: str) -> None:
    """Record an auditable 'no learnings this run' — satisfies the gate."""
    rec = store.add_none(engagement=engagement, reason=reason)
    click.echo(f"wrote {rec['path']}  (no-learning record)")


# ----------------------------------------------------------------- list / show


@main.command("list")
@click.option("--status", type=click.Choice(list(store.STATUSES)))
@click.option("--studio")
@click.option("--category", type=click.Choice(list(store.CATEGORIES)))
def list_cmd(status: str | None, studio: str | None, category: str | None) -> None:
    rows = store.list_(status=status, studio=studio, category=category)
    if not rows:
        click.echo("(none)")
        return
    for r in rows:
        click.echo(
            f"{r.get('date',''):<10}  {r.get('status','?'):<9}  "
            f"{r.get('severity','?'):<6}  {r.get('category','?'):<13}  "
            f"{r.get('studio','?'):<12}  {r.get('title','')}"
        )


@main.command("show")
@click.argument("learning_id")
def show_cmd(learning_id: str) -> None:
    try:
        r = store.read_one(learning_id)
    except FileNotFoundError as e:
        _die(str(e))
    meta = {k: v for k, v in r.items() if not k.startswith("_")}
    click.echo(json.dumps(meta, indent=2))
    click.echo("")
    click.echo(r.get("_body", ""))


# ----------------------------------------------------------------- status / promote


@main.command("status")
@click.argument("learning_id")
@click.option("--set", "new_status", required=True, type=click.Choice(list(store.STATUSES)))
@click.option("--ref", help="issue # or ADR id recorded on promotion")
def status_cmd(learning_id: str, new_status: str, ref: str | None) -> None:
    try:
        r = store.set_status(learning_id, status=new_status, ref=ref)
    except (FileNotFoundError, ValueError) as e:
        _die(str(e))
    click.echo(f"{r['id']} → {r['status']}" + (f"  ({ref})" if ref else ""))


@main.command("promote")
@click.argument("learning_id")
@click.option("--issue", "as_issue", is_flag=True, help="build a GitHub issue command (default)")
def promote_cmd(learning_id: str, as_issue: bool) -> None:
    """Build (dry-run) the command to promote a learning to a GitHub issue."""
    try:
        plan = store.promote_command(learning_id)
    except FileNotFoundError as e:
        _die(str(e))
    click.echo("# dry-run — creating the issue is an outward action; run it yourself:")
    click.echo(" ".join(shlex.quote(a) for a in plan["command"]))
    click.echo("")
    click.echo(f"# then record it: learnings status {plan['id']} --set promoted --ref '#<n>'")


# ----------------------------------------------------------------- doctor


@main.command("doctor")
def doctor_cmd() -> None:
    rep = deps_mod.doctor()
    click.echo(f"learnings {rep['version']}")
    click.echo(
        ("  ✓" if rep["learnings_cli"] else "  ✗")
        + f" learnings CLI  ({rep['learnings_cli'] or 'pip install -e .'})"
    )
    click.echo(
        ("  ✓" if rep["dir_writable"] else "  ✗")
        + f" store writable  ({rep['learnings_dir']})"
    )


if __name__ == "__main__":
    main()
