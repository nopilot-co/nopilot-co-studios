"""context-studio orchestrator.

Deterministic glue for the **infrastructural** context studio: scaffold
the per-engagement store, chain the tools/ tier over the CLI boundary,
record what ran when. The LLM judgment — what to ingest, the theme
framework, the per-theme synthesis — lives in the plugin's skills
(markdown). The materialiser stops are caller-supplied JSON, just like
the tool-bench tools.

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


def context_root() -> Path:
    """Shared studios-level context store."""
    docket = docket_root()
    if docket:
        return docket / "context"

    env = os.environ.get("STUDIOS_PROJECT_ROOT")
    if env:
        return Path(env).expanduser() / "context"

    d = Path.cwd().resolve()
    while d != d.parent:
        if (d / ".wip" / "config.yml").is_file():
            return d / "context"
        d = d.parent

    return Path.home() / "context" / "studios" / "context"


# Tool-bench tools we orchestrate. Keys are the CLI binary names; values are
# the friendly names used in `context doctor` output.
TOOLS = {
    "notion-sources": "notion-sources",
    "source-enrich": "source-enrich",
    "source-summarise": "source-summarise",
    "theme-propose": "theme-propose",
    "theme-cluster": "theme-cluster",
    "theme-entity": "theme-entity",
    "yt-transcript": "youtube-transcript",
}

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent  # .../context-studio/
SCHEMAS = Path(__file__).resolve().parent / "schemas"
