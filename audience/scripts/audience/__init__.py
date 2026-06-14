"""audience-studio orchestrator.

Deterministic glue for modelling **the reader** and critiquing work against them.
The LLM judgment — inferring/validating a persona, reviewing research, synthesising
a psychographic profile + need-state, deciding which needs matter and the rubric
criteria, and the reader-perspective critique — lives in the plugin's skills
(markdown). This package handles only mechanics: scaffolding the shared reader-model
store, filing research sources + provenance, validating the model/rubric, session
versioning, and handing scoring to the nitpicker engine over the CLI boundary.

No judgment lives here. CLI subcommands mirror the skills.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

__version__ = "0.1.0"


class _NoDatesSafeLoader(yaml.SafeLoader):
    """SafeLoader that keeps ISO dates/timestamps as strings.

    Plain YAML resolves ``captured: 2026-06-04`` to a ``datetime.date``, which then
    fails our string-typed schema fields. Authors (and skills) write dates
    unquoted, so we keep timestamps as strings rather than force quoting.
    """


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
    arbitrary Python objects (no ``!!python/object``); it only drops the implicit
    timestamp resolver. Safe to use on untrusted input.
    """
    return yaml.load(text, Loader=_NoDatesSafeLoader) or {}


def docket_root() -> Path | None:
    """The explicit production-docket root, if the caller set one (mirrors the
    other studios' ``$STUDIOS_DOCKET_ROOT`` contract)."""
    env = os.environ.get("STUDIOS_DOCKET_ROOT")
    return Path(env).expanduser().resolve() if env else None


def resolve_context_root(studio_name: str = "audience") -> Path:
    """Where this studio's critique sessions live — same override chain the other
    studios use:

    1. ``$STUDIOS_DOCKET_ROOT`` (if set) → the docket root itself.
    2. ``$STUDIOS_PROJECT_ROOT`` → ``<env>/agents/claude/outbox/<studio>/``.
    3. Walk upward from ``cwd`` for ``.wip/config.yml``.
    4. Legacy global ``~/context/studios/<studio>/``.
    """
    docket = docket_root()
    if docket:
        return docket

    env = os.environ.get("STUDIOS_PROJECT_ROOT")
    if env:
        return Path(env).expanduser() / "agents" / "claude" / "outbox" / studio_name

    d = Path.cwd().resolve()
    while d != d.parent:
        if (d / ".wip" / "config.yml").is_file():
            return d / "agents" / "claude" / "outbox" / studio_name
        d = d.parent

    return Path.home() / "context" / "studios" / studio_name


def audience_root_base() -> Path:
    """Base dir holding per-slug reader models — a shared, studios-level resource
    exactly parallel to the brand store (``design.brand_root_base``).

    Docket-local and authoritative when a docket root is set
    (``<docket>/audience/``); otherwise the shared studios-level store
    (``~/context/studios/audience/``), reusable across studios and projects.
    """
    docket = docket_root()
    if docket:
        return docket / "audience"
    return Path.home() / "context" / "studios" / "audience"


PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent  # .../audience/
SCHEMAS = Path(__file__).resolve().parent / "schemas"

# Global, cross-studio configs (the SAME review policy the nitpicker uses, so a
# reader-fit verdict reads identically to a nitpicker verdict).
CONFIGS_ROOT = PLUGIN_ROOT.parent / "configs"
REVIEW_POLICY = CONFIGS_ROOT / "default" / "review-policy.yml"
