"""CLI entry point: `motion <command>`. Subcommands mirror the skills 1:1.

S0 scaffold: `doctor` and `info` are live; the pipeline subcommands are declared
now (so the contract surface exists) and filled in by later slices — see the
build sequence in motion/CLAUDE.md.
"""

from __future__ import annotations

import click

from . import __version__, resolve_context_root
from . import deps as deps_mod


@click.group()
@click.version_option(__version__)
def main() -> None:
    """motion-studio orchestrator — animated/narrated assets."""


@main.command("doctor")
def doctor_cmd() -> None:
    """Report local render tools + external provider configuration."""
    rep = deps_mod.doctor()

    click.echo("Render tools:")
    for tool, ok in rep["tools"].items():
        hint = "" if ok else f"   → {deps_mod.TOOLS[tool]}"
        click.echo(f"  {'✓' if ok else '✗'} {tool}{hint}")

    click.echo("\nOptional:")
    for tool, ok in rep["optional"].items():
        hint = "" if ok else f"   → {deps_mod.OPTIONAL_TOOLS[tool]}"
        click.echo(f"  {'✓' if ok else '○'} {tool}{hint}")

    click.echo("\nProviders (external render — set the env key to enable):")
    for name, info in rep["providers"].items():
        mark = "✓" if info["configured"] else "○"
        click.echo(f"  {mark} {name:<11} {info['use']}  (${info['env']})")

    click.echo(
        "\nNotes:\n"
        "  • Remotion runs via `npx remotion` (needs node); ffmpeg encodes and\n"
        "    extracts QA keyframes. The declarative SVG/HTML path needs neither.\n"
        "  • Providers are render-time external services; keys come from the\n"
        "    environment, never the docket. Avatar renders require a twin with a\n"
        "    recorded consent (see `motion twin`)."
    )


@main.command("info")
def info_cmd() -> None:
    """Show studio identity + where outputs land."""
    click.echo("Motion Studio (motion) — animated / narrated assets")
    click.echo(f"  outputs root:    {resolve_context_root('motion')}")
    click.echo("  source of truth: storyboard.json  (schema lands in S1)")
    click.echo("  exports:         mp4 · webm · gif · svg · html · lottie · png")
    click.echo("  status:          S0 scaffold — build sequence in motion/CLAUDE.md")


def _todo(slice_label: str) -> None:
    raise click.ClickException(
        f"not implemented yet — scheduled for {slice_label} "
        "(see the build sequence in motion/CLAUDE.md)"
    )


# ---------------------------------------------------------------- storyboard
@main.group()
def storyboard() -> None:
    """The storyboard spec — single source of truth for a render."""


@storyboard.command("validate")
@click.option("--file", "path", required=True, type=click.Path())
def storyboard_validate(path: str) -> None:
    """Validate a storyboard.json against the schema."""
    _todo("S1 (storyboard schema + validator)")


# ---------------------------------------------------------------- produce
@main.command("produce")
@click.option("--session", required=True, type=click.Path())
@click.option("--bump", default="patch", type=click.Choice(["patch", "minor", "major"]))
def produce_cmd(session: str, bump: str) -> None:
    """Render the session's locked format from its storyboard."""
    _todo("S2 (Remotion → explainer-mp4)")


# ---------------------------------------------------------------- twin
@main.group()
def twin() -> None:
    """Digital-twin registry — likeness + voice + consent."""


@twin.command("ingest")
@click.option("--twin", "slug", required=True)
def twin_ingest(slug: str) -> None:
    """Register a twin (portrait/clip + voice ref); records consent."""
    _todo("S3.5 (digital-twin presenter)")


# ---------------------------------------------------------------- qa
@main.group()
def qa() -> None:
    """Visual QA for motion (keyframe sampling)."""


@qa.command("capture")
@click.option("--session", required=True, type=click.Path())
def qa_capture(session: str) -> None:
    """Extract keyframes + a contact sheet for eyes-on-pixels review."""
    _todo("S2 (keyframe capture)")


if __name__ == "__main__":
    main()
