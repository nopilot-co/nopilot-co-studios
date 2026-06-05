"""delivery-studio orchestrator.

Deterministic glue for the delivery studio's planning + RAID. The LLM
judgment — shaping swimlanes, phasing, resourcing, contingency posture,
identifying RAID items — lives in the plugin's skills (markdown). This
package handles only mechanics: scaffolding the per-engagement store,
validating the caller-supplied plan against the schema, stamping
provenance, deriving rollups (total days, contingency %, by-role / by-
swimlane totals), and maintaining the RAID register.

No judgment lives here. CLI subcommands mirror the skills.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

__version__ = "0.1.0"


class _NoDatesSafeLoader(yaml.SafeLoader):
    """SafeLoader that keeps ISO dates/timestamps as strings (mirrors audience)."""


_NoDatesSafeLoader.yaml_implicit_resolvers = {
    key: [
        (tag, regexp)
        for tag, regexp in resolvers
        if tag != "tag:yaml.org,2002:timestamp"
    ]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml(text: str) -> dict:
    """Parse a studios YAML doc, keeping dates as strings.

    ``_NoDatesSafeLoader`` is a ``SafeLoader`` subclass — it constructs no
    arbitrary Python objects; it only drops the implicit timestamp
    resolver. Safe to use on untrusted input.
    """
    return yaml.load(text, Loader=_NoDatesSafeLoader) or {}


def docket_root() -> Path | None:
    env = os.environ.get("STUDIOS_DOCKET_ROOT")
    return Path(env).expanduser().resolve() if env else None


def delivery_root() -> Path:
    """Shared studios-level delivery store. Mirrors the other studios."""
    docket = docket_root()
    if docket:
        return docket / "delivery"

    env = os.environ.get("STUDIOS_PROJECT_ROOT")
    if env:
        return Path(env).expanduser() / "delivery"

    d = Path.cwd().resolve()
    while d != d.parent:
        if (d / ".wip" / "config.yml").is_file():
            return d / "delivery"
        d = d.parent

    return Path.home() / "context" / "studios" / "delivery"


PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent  # .../delivery/
SCHEMAS = Path(__file__).resolve().parent / "schemas"
