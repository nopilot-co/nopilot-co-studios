"""commercial-studio orchestrator.

Deterministic glue for the commercial studio's two capabilities — the
beancounter's deterministic deal validation (`check-commercials`, review-class)
and the commercial officer's value-based opportunity sizing
(`assess-commercial-value`, caller-supplied-JSON materialiser). The LLM
judgment — interpreting checks, narrating findings, doing financial research,
and synthesising the value assessment — lives in the plugin's skills
(markdown). This package handles only mechanics: scaffolding the shared
commercial store, schema validation, evaluating the deterministic checks,
session versioning, and handing scoring to the nitpicker engine over the CLI
boundary.

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
    """Parse a studios YAML document, keeping dates as strings.

    ``_NoDatesSafeLoader`` is a ``SafeLoader`` subclass — it constructs no
    arbitrary Python objects; it only drops the implicit timestamp resolver.
    Safe to use on untrusted input.
    """
    return yaml.load(text, Loader=_NoDatesSafeLoader) or {}


def docket_root() -> Path | None:
    """The explicit production-docket root, if set."""
    env = os.environ.get("STUDIOS_DOCKET_ROOT")
    return Path(env).expanduser().resolve() if env else None


def commercial_root() -> Path:
    """Shared studios-level commercial store. Mirrors audience_root_base().

    1. ``$STUDIOS_DOCKET_ROOT`` (if set) → ``<docket>/commercial/``
    2. Walk upward from ``cwd`` for ``.wip/config.yml`` → docket-local
    3. Legacy global ``~/context/studios/commercial/``
    """
    docket = docket_root()
    if docket:
        return docket / "commercial"

    env = os.environ.get("STUDIOS_PROJECT_ROOT")
    if env:
        return Path(env).expanduser() / "commercial"

    d = Path.cwd().resolve()
    while d != d.parent:
        if (d / ".wip" / "config.yml").is_file():
            return d / "commercial"
        d = d.parent

    return Path.home() / "context" / "studios" / "commercial"


PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent  # .../commercial/
SCHEMAS = Path(__file__).resolve().parent / "schemas"
TEMPLATES = PLUGIN_ROOT / "templates"
CONFIGS_LOCAL = PLUGIN_ROOT / "configs"

# Global, cross-studio configs (the SAME review policy the nitpicker uses, so a
# commercial verdict reads identically to a nitpicker or reader-fit verdict).
CONFIGS_ROOT = PLUGIN_ROOT.parent / "configs"
REVIEW_POLICY = CONFIGS_ROOT / "default" / "review-policy.yml"
