"""learnings — append-only plugin-improvement learnings for the studios plugin.

Deterministic glue behind the ``reflect`` skill
(``skills/reflect/SKILL.md``). Each learning is one markdown file with YAML
frontmatter under ``learnings/<YYYY>/<YYYY-MM-DD>-<studio>-<slug>.md`` — captured
at the close of a run, recording how the plugin/studio *itself* could improve
(its skills, CLIs, formats, assets, orchestration, or docs).

No judgment lives here — that's the skill's job. This package only writes,
reads, lists, and status-transitions the records, and validates them against
``schemas/learning.schema.json``. The CLI subcommands mirror the skill.
"""

from __future__ import annotations

import os
from pathlib import Path

__version__ = "0.1.0"

PACKAGE_ROOT = Path(__file__).resolve().parent
SCHEMAS = PACKAGE_ROOT / "schemas"


def repo_root() -> Path:
    """Repo / plugin root — scripts/learnings/__init__.py → parents[2]."""
    return Path(__file__).resolve().parents[2]


def learnings_dir() -> Path:
    """Where learning records live.

    Learnings are *about the plugin*, so they live with the plugin (repo root),
    not the run's cwd. ``$STUDIOS_LEARNINGS_DIR`` overrides — used by tests and
    alternative installs.
    """
    env = os.environ.get("STUDIOS_LEARNINGS_DIR")
    if env:
        return Path(env).expanduser()
    return repo_root() / "learnings"
