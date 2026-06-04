"""Reuse the nitpicker's scoring engine — over the CLI boundary.

The audience studio owns **zero** scoring math. Its per-reader rubric is scored by
the nitpicker's single-sourced aggregation via ``nit aggregate --scores <scores>
--tests-from <rubric>``, against the same ``configs/default/review-policy.yml`` —
so a reader-fit verdict reads identically to a nitpicker verdict.

Rather than importing the ``nitpicker-studio`` package (a local editable plugin
with its own venv, not a PyPI dep), we invoke the ``nit`` CLI — the same decoupled
pattern the planner uses for ``studio docket`` (``scripts/planner/docket_bridge.py``).
If ``nit`` is absent, scoring fails with an install hint; ``audience doctor`` flags it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

_REPO_ROOT = (
    Path(__file__).resolve().parent.parent.parent.parent
)  # .../nopilot-co-studios/
_FALLBACK_BINS = (_REPO_ROOT / "nitpicker" / ".venv" / "bin" / "nit",)


def nit_cli() -> str | None:
    """Resolve the nitpicker ``nit`` CLI, or None if it isn't installed."""
    found = shutil.which("nit")
    if found:
        return found
    for cand in _FALLBACK_BINS:
        if cand.is_file():
            return str(cand)
    return None


def available() -> bool:
    return nit_cli() is not None


def aggregate(scores_path: Path, rubric_path: Path) -> dict:
    """Run ``nit aggregate`` over the boundary; return the parsed scorecard dict."""
    cli = nit_cli()
    if cli is None:
        raise RuntimeError(
            "the nitpicker `nit` CLI is not installed, but the audience studio "
            "scores reader-fit through it. Install it: run `nitpicker/install.sh`."
        )
    proc = subprocess.run(
        [
            cli,
            "aggregate",
            "--scores",
            str(scores_path),
            "--tests-from",
            str(rubric_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"`nit aggregate` failed: {msg}")
    return json.loads(proc.stdout)
