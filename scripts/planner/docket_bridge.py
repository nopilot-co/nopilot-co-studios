"""Reuse the design studio's production-docket scaffolding — over the CLI boundary.

The planner operates **in place** over a production docket. Rather than importing
the ``design-studio`` package (a local editable plugin, not a PyPI dependency),
we reuse it the same way the creative-director reuses any studio: by invoking its
entry point. ``studio docket init`` builds (or tops up) the docket tree
(``specs/`` ``assets/`` ``brand/`` + the production/session manifests); the
planner then writes ``composition.json`` + ``sections/`` on top.

This keeps the planner decoupled and installable on its own, and keeps the docket
model design-owned (single source of truth) — no reinvention.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

# Where the design CLI may live if it isn't on PATH. Editable `pip install --user`
# normally puts `studio` on PATH; these are best-effort fallbacks for a repo
# checkout that hasn't been installed user-wide.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # .../nopilot-co-studios/
_FALLBACK_BINS = (_REPO_ROOT / "design" / ".venv" / "bin" / "studio",)


def studio_cli() -> str | None:
    """Resolve the design ``studio`` CLI, or None if it isn't installed."""
    found = shutil.which("studio")
    if found:
        return found
    for cand in _FALLBACK_BINS:
        if cand.is_file():
            return str(cand)
    return None


def available() -> bool:
    return studio_cli() is not None


def _run(args: list[str]) -> subprocess.CompletedProcess:
    cli = studio_cli()
    if cli is None:
        raise RuntimeError(
            "the design `studio` CLI is not installed, but the planner needs it to "
            "scaffold a docket and (later) render. Install it: run `design/install.sh`."
        )
    return subprocess.run([cli, *args], capture_output=True, text=True, check=False)


def init_docket(root: Path, *, brand: str | None, session: str | None) -> None:
    """Create (or top up) the production docket under ``root`` via ``studio docket init``."""
    args = ["docket", "init", str(root)]
    if brand:
        args += ["--brand", brand]
    if session:
        args += ["--session", session]
    proc = _run(args)
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"`studio docket init` failed: {msg}")


def format_valid(fmt: str) -> bool | None:
    """Best-effort check that ``fmt`` is a real design format slug.

    Returns True/False if the design CLI is available to ask, else None
    (unknown — caller should warn rather than block).
    """
    if not available():
        return None
    proc = _run(["formats", "validate", "--format", fmt])
    return proc.returncode == 0
