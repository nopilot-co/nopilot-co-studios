"""CLI entry point: `audience <command>`.

Subcommands mirror the skills (judgment in skills, mechanics here):
  audience persona new --audience SLUG [--persona PATH]
  audience persona validate --audience SLUG
  audience research add --audience SLUG --source PATH_OR_URL [--kind …]
  audience profile build --audience SLUG [--status …]
  audience profile validate --audience SLUG
  audience rubric derive --audience SLUG
  audience rubric validate --audience SLUG
  audience review new --name NAME --audience SLUG --target PATH_OR_URL [--brief PATH]
  audience review score --session PATH [--version X.Y.Z]
  audience review status --session PATH [--set …]
  audience doctor
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml

from . import deps as deps_mod
from . import research as research_mod
from . import rubric as rubric_mod
from . import session as session_mod
from . import store as store_mod

_audience_opt = click.option(
    "--audience", "slug", required=True, help="Reader-model slug (kebab-case)."
)


def _fail(msg: str) -> None:
    raise click.ClickException(msg)


def _print_errors(errors: list[str], ok_msg: str) -> None:
    if errors:
        for e in errors:
            click.echo(f"  ✗ {e}", err=True)
        sys.exit(1)
    click.echo(ok_msg)


@click.group()
def main() -> None:
    """Audience studio — model the reader, critique work against them."""


# ---------------------------------------------------------------- persona
@main.group()
def persona() -> None:
    """Take/infer + validate the reader persona; scaffold the model store."""


@persona.command("new")
@_audience_opt
@click.option(
    "--persona",
    "persona_path",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Optional seed: a YAML file with `name`/`persona` keys, else a stub is scaffolded.",
)
def persona_new(slug: str, persona_path: Path | None) -> None:
    seed = None
    if persona_path:
        try:
            raw = yaml.safe_load(persona_path.read_text())
        except yaml.YAMLError:
            raw = None
        if isinstance(raw, dict):
            seed = {"name": raw.get("name"), "persona": raw.get("persona") or raw}
    try:
        store_mod.scaffold(slug, persona=seed)
    except ValueError as e:
        _fail(str(e))
    click.echo(f"✓ reader model scaffolded: {store_mod.audience_path(slug)}")
    click.echo(
        "  next: review research, then the psychographic-profile skill fills it in"
    )


@persona.command("validate")
@_audience_opt
def persona_validate(slug: str) -> None:
    _print_errors(store_mod.validate_slug(slug), f"✓ {slug} persona is valid")


# ---------------------------------------------------------------- research
@main.group()
def research() -> None:
    """File research sources into the reader-model store."""


@research.command("add")
@_audience_opt
@click.option("--source", required=True, help="A file path or a URL to review.")
@click.option(
    "--kind",
    default=None,
    type=click.Choice(["transcript", "doc", "url", "interview", "web-research"]),
    help="Source kind (inferred from the file otherwise).",
)
@click.option(
    "--id", "source_id", default=None, help="Stable source id (defaults to filename)."
)
def research_add(
    slug: str, source: str, kind: str | None, source_id: str | None
) -> None:
    try:
        research_mod.add_source(slug, source, kind=kind, source_id=source_id)
    except ValueError as e:
        _fail(str(e))
    click.echo(
        f"✓ filed source for '{slug}' — review it into research/ and cite it in needs"
    )


# ---------------------------------------------------------------- profile
@main.group()
def profile() -> None:
    """Lock + validate the synthesized psychographic profile + need-state."""


@profile.command("build")
@_audience_opt
@click.option(
    "--status",
    default=None,
    type=click.Choice(list(store_mod.STATUSES)),
    help="Set model status (use 'validated' only after the user confirms the persona).",
)
def profile_build(slug: str, status: str | None) -> None:
    try:
        data = store_mod.mark_built(slug, status=status)
    except (FileNotFoundError, ValueError) as e:
        _fail(str(e))
    click.echo(f"✓ {slug} built — status: {data['status']}")


@profile.command("validate")
@_audience_opt
def profile_validate(slug: str) -> None:
    _print_errors(store_mod.validate_slug(slug), f"✓ {slug} reader model is valid")


# ---------------------------------------------------------------- rubric
@main.group()
def rubric() -> None:
    """Derive + validate the weighted reader-fit rubric."""


@rubric.command("derive")
@_audience_opt
def rubric_derive(slug: str) -> None:
    try:
        data = rubric_mod.derive(slug)
    except (FileNotFoundError, ValueError) as e:
        _fail(str(e))
    click.echo(f"✓ rubric drafted: {rubric_mod.rubric_path(slug)}")
    click.echo(
        f"  {len(data['tests'])} test(s), gates: {', '.join(data['gates']) or 'none'} "
        "— the scoring-rubric skill fills the criteria"
    )


@rubric.command("validate")
@_audience_opt
def rubric_validate(slug: str) -> None:
    _print_errors(rubric_mod.validate_slug(slug), f"✓ {slug} rubric is valid")


# ---------------------------------------------------------------- review
@main.group()
def review() -> None:
    """Critique an artifact against a reader model."""


@review.command("new")
@click.option("--name", required=True, help="Critique session name (kebab-case).")
@_audience_opt
@click.option(
    "--target", required=True, help="The artifact under critique: a file path or URL."
)
@click.option(
    "--brief",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Optional brief — what the artifact was meant to do.",
)
def review_new(name: str, slug: str, target: str, brief: Path | None) -> None:
    try:
        root = session_mod.new(slug, name, target, brief=str(brief) if brief else None)
    except ValueError as e:
        _fail(str(e))
    state = session_mod.read_state(root)
    click.echo(str(root))
    click.echo(f"  reader: {slug}   target: {state['target']} ({state['target_kind']})")
    click.echo(
        "  next: critique as this reader → review/v1.0.0/scores.yml, then `audience review score`"
    )


@review.command("score")
@click.option(
    "--session",
    "session_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--version", default=None, help="Version to score (defaults to current).")
def review_score(session_path: Path, version: str | None) -> None:
    """Aggregate reader-fit scores via the nitpicker engine → scorecard + strengthening areas."""
    try:
        card = session_mod.score(session_path, version)
    except (FileNotFoundError, RuntimeError) as e:
        _fail(str(e))
    click.echo(
        f"reader-fit: {card['verdict'].upper()}   overall: {card['overall']}/100"
    )
    if card["gates_failed"]:
        click.echo(
            f"  ⚠ unmet must-have(s): {', '.join(card['gates_failed'])}", err=True
        )
    for i in sorted(card["items"], key=lambda x: x["norm"]):
        flag = " (must-have)" if i["gate"] else ""
        click.echo(
            f"  [{i['status']:>4}] {i['key']:<24} {i['score']:>4}/{i['max']:<3}{flag}"
        )
    click.echo(
        f"\nstrengthening areas: {session_path}/review/v{version or session_mod.read_state(session_path)['current']}/strengthening-areas.md"
    )


@review.command("status")
@click.option(
    "--session",
    "session_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--set",
    "new_status",
    default=None,
    type=click.Choice(session_mod.STATUSES),
    help="Update the review status.",
)
def review_status(session_path: Path, new_status: str | None) -> None:
    if new_status:
        session_mod.set_status(session_path, new_status)
    state = session_mod.read_state(session_path)
    click.echo(
        f"{state['session']}  reader={state['audience']}  "
        f"status={state['status']}  v{state['current']}"
    )


# ---------------------------------------------------------------- doctor
@main.command("doctor")
def doctor_cmd() -> None:
    """Report whether the studio is wired up to model + score."""
    rep = deps_mod.doctor()
    click.echo(f"audience {rep['version']}")
    if rep["nit_cli"]:
        click.echo(
            f"  ✓ nitpicker CLI  ({rep['nit_cli']})  — reader-fit scoring engine"
        )
    else:
        click.echo(
            "  ✗ nitpicker CLI  →  run `nitpicker/install.sh` (needed to score reader-fit)"
        )
    click.echo(f"\nstore: {rep['store']}")
    click.echo(f"  models: {', '.join(rep['models']) or '(none yet)'}")
    click.echo(
        "\nNotes:\n"
        "  • The studio models the reader + critiques; scoring reuses the nitpicker\n"
        "    engine (`nit aggregate`) against the same review policy.\n"
        "  • Research/context review uses the LLM host's tools (not this package)."
    )


if __name__ == "__main__":
    main()
