"""CLI entry point: `nit <command>`.

Subcommands mirror the skills:
  nit tests list | show --test SLUG | validate --test SLUG
  nit config show [--brand SLUG]
  nit new --name NAME --target PATH_OR_URL [--brief PATH] [--brand SLUG] [--icp PATH]
  nit capture --session PATH [--bump patch|minor|major]
  nit score --session PATH [--version X.Y.Z]
  nit status --session PATH [--set draft|reviewing|reviewed|signed-off|rejected]
  nit doctor
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import yaml

from . import capture as capture_mod
from . import config as config_mod
from . import deps as deps_mod
from . import session as session_mod
from . import tests as tests_mod


@click.group()
def main() -> None:
    """nitpicker-studio orchestrator."""


# ---------------------------------------------------------------- tests
@main.group()
def tests() -> None:
    """Inspect the scored test battery (configs/tests/)."""


@tests.command("list")
def tests_list() -> None:
    slugs = tests_mod.list_tests()
    if not slugs:
        click.echo("(no tests defined in configs/tests/)")
        return
    for slug in slugs:
        try:
            spec = tests_mod.load(slug)
            q = spec.get("question", "")
            w = spec.get("weight", 1.0)
            click.echo(f"{slug:<22}  w={w:<4}  {q}")
        except (FileNotFoundError, ValueError) as e:
            click.echo(f"{slug:<22}  ✗ {e}", err=True)


@tests.command("show")
@click.option("--test", "slug", required=True)
def tests_show(slug: str) -> None:
    try:
        click.echo(tests_mod.show(slug))
    except FileNotFoundError as e:
        raise click.ClickException(str(e)) from e


@tests.command("validate")
@click.option("--test", "slug", required=True)
def tests_validate(slug: str) -> None:
    errors = tests_mod.validate(slug)
    if errors:
        for e in errors:
            click.echo(f"  ✗ {e}", err=True)
        sys.exit(1)
    click.echo(f"✓ {slug} is valid")


# ---------------------------------------------------------------- config
@main.group()
def config() -> None:
    """Inspect the global configs (baselines + tests + policy)."""


@config.command("show")
@click.option("--brand", "brand", default=None, help="Show a brand's voice overlay too")
def config_show(brand: str | None) -> None:
    click.echo(config_mod.show(brand))


# ---------------------------------------------------------------- new
@main.command("new")
@click.option("--name", required=True, help="Review session name (kebab-case)")
@click.option(
    "--target",
    required=True,
    help="The asset under review: a file path (pdf/pptx/html/image/md) or a URL",
)
@click.option(
    "--brief",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Markdown brief the asset must fulfil (optional; a stub is scaffolded otherwise)",
)
@click.option(
    "--brand", default=None, help="Brand slug, for the voice overlay (optional)"
)
@click.option(
    "--icp",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="Markdown ICP / target-audience profile (optional; a stub is scaffolded otherwise)",
)
def new_cmd(
    name: str, target: str, brief: Path | None, brand: str | None, icp: Path | None
) -> None:
    try:
        path = session_mod.new(
            name,
            target,
            brief=str(brief) if brief else None,
            brand=brand,
            icp=str(icp) if icp else None,
        )
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    state = session_mod.read_state(path)
    click.echo(str(path))
    click.echo(f"  target: {state['target']}  ({state['target_kind']})")
    click.echo(f"  brief : {path}/inputs/brief.md")
    click.echo(f"  icp   : {path}/inputs/icp.md")
    click.echo("  next  : nit capture --session <path>, then run the review skills")


# ---------------------------------------------------------------- capture
@main.command("capture")
@click.option(
    "--session",
    "session_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--bump", default="patch", type=click.Choice(["patch", "minor", "major"]))
def capture_cmd(session_path: Path, bump: str) -> None:
    """Rasterise the target into capture/v<version>/ for visual QA."""
    version = session_mod.next_version(session_path, bump)
    try:
        images = capture_mod.capture(session_path, version)
    except (RuntimeError, FileNotFoundError) as e:
        raise click.ClickException(str(e)) from e
    session_mod.record_capture(session_path, version, images)
    if not images:
        click.echo(
            f"✓ v{version}: text-only target — no visual capture "
            "(critique the source directly)"
        )
        return
    click.echo(f"✓ v{version}: captured {len(images)} image(s) to {images[0].parent}")


# ---------------------------------------------------------------- score
@main.command("score")
@click.option(
    "--session",
    "session_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--version", default=None, help="Version to score (defaults to current)")
def score_cmd(session_path: Path, version: str | None) -> None:
    """Aggregate review/v<version>/scores.yml into a weighted scorecard + verdict."""
    state = session_mod.read_state(session_path)
    version = version or state["current"]
    if version == "0.0.0":
        raise click.ClickException("nothing captured yet — run `nit capture` first")

    scores_path = session_path / "review" / f"v{version}" / "scores.yml"
    if not scores_path.exists():
        raise click.ClickException(
            f"no scores at {scores_path}\n"
            "  (the apply-tests / verdict skills write per-test + per-dimension "
            "scores there)"
        )
    scores = yaml.safe_load(scores_path.read_text()) or {}
    card = tests_mod.aggregate(scores)

    card_path = scores_path.parent / "scorecard.json"
    card_path.write_text(json.dumps(card, indent=2))
    session_mod.record_score(session_path, version, card)

    click.echo(f"verdict: {card['verdict'].upper()}   overall: {card['overall']}/100")
    if card["gates_failed"]:
        click.echo(f"  ⚠ gate(s) failed: {', '.join(card['gates_failed'])}", err=True)
    for i in sorted(card["items"], key=lambda x: x["norm"]):
        flag = " (gate)" if i["gate"] else ""
        click.echo(
            f"  [{i['status']:>4}] {i['key']:<22} {i['score']:>4}/{i['max']:<3}{flag}"
        )
    click.echo(f"\nscorecard: {card_path}")


# ---------------------------------------------------------------- status
@main.command("status")
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
    help="Update the review status",
)
def status_cmd(session_path: Path, new_status: str | None) -> None:
    if new_status:
        session_mod.set_status(session_path, new_status)
    state = session_mod.read_state(session_path)
    click.echo(
        f"{state['session']}  target={state['target_kind']}  "
        f"status={state['status']}  v{state['current']}"
    )


# ---------------------------------------------------------------- doctor
@main.command("doctor")
def doctor_cmd() -> None:
    """Report capture-tool presence. Text-only targets need none."""
    rep = deps_mod.doctor()
    click.echo("Capture tools:")
    for tool, ok in rep["tools"].items():
        if ok:
            click.echo(f"  ✓ {tool}")
        else:
            click.echo(
                f"  ✗ {tool}   →  {deps_mod.INSTALL_HINTS.get(tool, '(install it)')}"
            )
    click.echo("\nConfigs:")
    click.echo(f"  baselines: {', '.join(config_mod.list_baselines()) or '(none)'}")
    click.echo(f"  tests:     {', '.join(tests_mod.list_tests()) or '(none)'}")


if __name__ == "__main__":
    main()
