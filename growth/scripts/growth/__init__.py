"""growth-studio orchestrator.

Deterministic glue for the growth studio's two capabilities (generate-leads
and map-market). The LLM judgment — qualifying leads against an ICP,
shaping the market segmentation, positioning — lives in the plugin's
skills. This package handles only mechanics: scaffolding the per-engagement
store, validating the caller-supplied JSON payloads, deriving rollups.

No judgment lives here. CLI subcommands mirror the skills 1:1.
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


def growth_root() -> Path:
    docket = docket_root()
    if docket:
        return docket / "growth"
    env = os.environ.get("STUDIOS_PROJECT_ROOT")
    if env:
        return Path(env).expanduser() / "growth"
    d = Path.cwd().resolve()
    while d != d.parent:
        if (d / ".wip" / "config.yml").is_file():
            return d / "growth"
        d = d.parent
    return Path.home() / "context" / "studios" / "growth"


PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMAS = Path(__file__).resolve().parent / "schemas"
