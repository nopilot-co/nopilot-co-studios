"""nitpicker-studio orchestrator.

Deterministic glue for asset review. The LLM judgment — visual/format QA, brief
fulfilment, audience/ICP fit, tone-of-voice adherence, and the scored test
battery (so-what / yawn / sniff) — lives in the plugin's skills (markdown). This
package handles only mechanics: capturing the target asset, loading + validating
the global configs (baselines + tests), session/versioning, and deterministic
aggregation of scores into a weighted verdict.

No judgment lives here. CLI subcommands mirror the skills.
"""

__version__ = "0.1.0"

import os
from pathlib import Path


def resolve_context_root(studio_name: str = "nitpicker") -> Path:
    """Resolve where this studio's review sessions live, with the same override
    chain the design + messaging studios use so a wip-bootstrapped project
    co-locates outputs:

    1. ``$STUDIOS_PROJECT_ROOT`` env var (if set) →
       ``<env>/agents/claude/outbox/<studio>/``
    2. Walk upward from ``cwd`` for ``.wip/config.yml`` — if found, use
       ``<found>/agents/claude/outbox/<studio>/``
    3. Fall back to ``~/context/studios/<studio>/`` (legacy default).
    """
    env = os.environ.get("STUDIOS_PROJECT_ROOT")
    if env:
        return Path(env).expanduser() / "agents" / "claude" / "outbox" / studio_name

    d = Path.cwd().resolve()
    while d != d.parent:
        if (d / ".wip" / "config.yml").is_file():
            return d / "agents" / "claude" / "outbox" / studio_name
        d = d.parent

    return Path.home() / "context" / "studios" / studio_name


CONTEXT_ROOT = resolve_context_root("nitpicker")
PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent  # .../nitpicker/
SCHEMAS = Path(__file__).resolve().parent / "schemas"

# Global, cross-studio configs live at the studios repo root (configs/), shared
# by every studio and independent of any brand slug.
CONFIGS_ROOT = PLUGIN_ROOT.parent / "configs"
DEFAULTS = CONFIGS_ROOT / "default"
TESTS = CONFIGS_ROOT / "tests"

# Brand is a studios-level entity (shared with design + messaging). A brand's own
# tone-of-voice overlays the default baseline in configs/default/.
BRAND_ROOT = Path.home() / "context" / "studios" / "brand"
DESIGN_CONTEXT = Path.home() / "context" / "studios" / "design"  # legacy location
