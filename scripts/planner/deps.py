"""``planner doctor`` checks: is the planner wired up to do real work?

The planner has no native render tooling of its own — its only hard dependency
is the design ``studio`` CLI, used to scaffold the docket and (downstream, via the
creative-director) to render the assembled source. This reports that link plus a
note on the research tooling the skill uses (web search), which lives in the LLM
host, not this package.
"""

from __future__ import annotations

from . import __version__, docket_bridge


def doctor() -> dict:
    cli = docket_bridge.studio_cli()
    return {
        "version": __version__,
        "studio_cli": cli,  # path or None
    }
