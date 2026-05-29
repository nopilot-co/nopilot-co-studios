"""CLI entry point: `message <command>`.

Subcommands match the skills:
  message formats list | show --format SLUG | validate --format SLUG
  message new --brand SLUG --name NAME --format SLUG
  message lint --session PATH
  message render --session PATH --bump patch|minor|major
  message status --session PATH [--set draft|approved|sent]
  message doctor
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from . import deps as deps_mod
from . import formats as formats_mod
from . import lint as lint_mod
from . import render as render_mod
from . import sequence as sequence_mod
from . import session as session_mod
from . import voice as voice_mod


@click.group()
def main() -> None:
    """messaging-studio orchestrator."""


# ---------------------------------------------------------------- formats
@main.group()
def formats() -> None:
    """Inspect communication format contracts (purpose × channel)."""


@formats.command("list")
def formats_list() -> None:
    slugs = formats_mod.list_formats()
    if not slugs:
        click.echo("(no formats defined)")
        return
    for slug in slugs:
        try:
            r = formats_mod.resolve(slug)
            targets = ",".join(formats_mod.channel_targets(r)) or "—"
            missing = deps_mod.missing_render_tools(r)
            note = f"  (needs: {', '.join(missing)})" if missing else ""
            click.echo(f"{slug:<22}  {r.get('channel', '—'):<14}  -> {targets}{note}")
        except (FileNotFoundError, ValueError) as e:
            click.echo(f"{slug:<22}  ✗ {e}", err=True)


@formats.command("show")
@click.option("--format", "slug", required=True)
def formats_show(slug: str) -> None:
    try:
        click.echo(formats_mod.show(slug))
    except (FileNotFoundError, ValueError) as e:
        raise click.ClickException(str(e)) from e


@formats.command("validate")
@click.option("--format", "slug", required=True)
def formats_validate(slug: str) -> None:
    errors = formats_mod.validate(slug)
    if errors:
        for e in errors:
            click.echo(f"  ✗ {e}", err=True)
        sys.exit(1)
    click.echo(f"✓ {slug} is valid")


# ---------------------------------------------------------------- new
@main.command("new")
@click.option(
    "--brand", required=True, help="Brand slug (shares the design studio's voice)"
)
@click.option("--name", required=True, help="Session name (kebab-case)")
@click.option(
    "--format",
    "fmt",
    required=True,
    help="Format slug to lock in, e.g. outreach-email (see `message formats list`)",
)
def new_cmd(brand: str, name: str, fmt: str) -> None:
    try:
        path = session_mod.new(brand, name, fmt)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    voice = voice_mod.voice_path(brand)
    click.echo(str(path))
    click.echo(f"  voice: {voice if voice else '(none — default missing)'}")
    click.echo(f"  compose into: {path}/inputs/message.md")


# ---------------------------------------------------------------- lint
@main.command("lint")
@click.option(
    "--session",
    "session_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
def lint_cmd(session_path: Path) -> None:
    """Enforce the locked format's deterministic ruleset against the composed message."""
    try:
        violations = lint_mod.lint(session_path)
    except (FileNotFoundError, ValueError) as e:
        raise click.ClickException(str(e)) from e
    if violations:
        click.echo("✗ ruleset violations:", err=True)
        for v in violations:
            click.echo(f"  - {v}", err=True)
        sys.exit(1)
    click.echo("✓ within ruleset")


# ---------------------------------------------------------------- render
@main.command("render")
@click.option(
    "--session",
    "session_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--bump", default="patch", type=click.Choice(["patch", "minor", "major"]))
def render_cmd(session_path: Path, bump: str) -> None:
    """Render the composed message to its channel target(s); enforces the ruleset."""
    try:
        outputs = render_mod.render(session_path, bump)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        raise click.ClickException(str(e)) from e
    for target, path in outputs.items():
        click.echo(f"  ✓ {target:<4} {path}")

    # Surface any MJML-gated targets that were skipped because the tool is missing.
    resolved = formats_mod.resolve(session_mod.read_state(session_path)["format"])
    gated = {"html", "eml"} & set(formats_mod.channel_targets(resolved))
    missing = deps_mod.missing_render_tools(resolved)
    if gated and missing:
        hint = deps_mod.INSTALL_HINTS.get(missing[0], "install it")
        click.echo(
            f"\n⚠ skipped {', '.join(sorted(gated))} — needs {', '.join(missing)}: {hint}",
            err=True,
        )

    violations = lint_mod.lint(session_path)
    if violations:
        click.echo("\n✗ ruleset violations (fix the message and re-render):", err=True)
        for v in violations:
            click.echo(f"  - {v}", err=True)
        sys.exit(1)


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
    type=click.Choice(["draft", "approved", "sent"]),
    help="Update the message status",
)
def status_cmd(session_path: Path, new_status: str | None) -> None:
    if new_status:
        session_mod.set_status(session_path, new_status)
    state = session_mod.read_state(session_path)
    click.echo(
        f"{state['session']}  format={state['format']}  status={state['status']}  v{state['current']}"
    )


# ---------------------------------------------------------------- sequence
@main.group()
def sequence() -> None:
    """Compose a multi-step campaign as ordered, linked message sessions."""


@sequence.command("new")
@click.option(
    "--brand", required=True, help="Brand slug (shares the design studio's voice)"
)
@click.option("--name", required=True, help="Sequence name (kebab-case)")
@click.option(
    "--step",
    "steps",
    multiple=True,
    required=True,
    help="Repeatable NAME:FORMAT, in order "
    "(e.g. --step cold:outreach-email --step bump:followup-email)",
)
def sequence_new(brand: str, name: str, steps: tuple[str, ...]) -> None:
    parsed: list[tuple[str, str]] = []
    for s in steps:
        if ":" not in s:
            raise click.UsageError(f"--step must be NAME:FORMAT, got '{s}'")
        step_name, fmt = s.split(":", 1)
        parsed.append((step_name.strip(), fmt.strip()))
    try:
        root = sequence_mod.new(brand, name, parsed)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    click.echo(str(root))
    for i, (step_name, fmt) in enumerate(parsed, start=1):
        sid = sequence_mod.step_id(i, step_name)
        click.echo(
            f"  step {i}: {step_name} [{fmt}]  -> compose into {root}/{sid}/inputs/message.md"
        )


@sequence.command("status")
@click.option(
    "--sequence",
    "seq_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
def sequence_status(seq_path: Path) -> None:
    try:
        rows = sequence_mod.status(seq_path)
    except FileNotFoundError as e:
        raise click.ClickException(f"not a sequence ({e})") from e
    for r in rows:
        click.echo(
            f"  step {r['step']:>2}  {r['name']:<16} {r['format']:<20} "
            f"status={r['status']:<9} v{r['current']}"
        )


# ---------------------------------------------------------------- doctor
@main.command("doctor")
def doctor_cmd() -> None:
    """Report native-tool presence and per-format render readiness."""
    rep = deps_mod.doctor()
    click.echo("Tools:")
    if not rep["tools"]:
        click.echo("  (none required — all channels are text-first)")
    for tool, ok in rep["tools"].items():
        if ok:
            click.echo(f"  ✓ {tool}")
        else:
            click.echo(
                f"  ✗ {tool}   →  {deps_mod.INSTALL_HINTS.get(tool, '(install it)')}"
            )
    click.echo("\nFormats:")
    for f in rep["formats"]:
        targets = ",".join(f["targets"]) or "—"
        status = (
            "✓ ready"
            if f["render_ready"]
            else f"✗ needs: {', '.join(f['render_missing'])}"
        )
        click.echo(f"  {f['slug']:<22} {targets:<22} {status}")


if __name__ == "__main__":
    main()
