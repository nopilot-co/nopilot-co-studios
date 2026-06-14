"""Reuse the nitpicker scoring engine over the CLI boundary.

Mirror of ``audience/scripts/audience/nit_bridge.py`` — keeps the verdict math
single-sourced in ``nit.tests.aggregate``. We shell out to ``nit aggregate``
with our ``scores.yml`` and the rubric, so a commercial verdict reads
identically to any other gate.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


def _nit_binary() -> str | None:
    """Find the ``nit`` CLI: PATH first, then the sibling venv (../nitpicker/.venv)."""
    on_path = shutil.which("nit")
    if on_path:
        return on_path
    # repo-relative fallback: <studios>/nitpicker/.venv/bin/nit
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "nitpicker" / ".venv" / "bin" / "nit"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def reachable() -> bool:
    return _nit_binary() is not None


def aggregate(
    scores_yml: Path, tests_from: Path, *, policy: Path | None = None
) -> dict:
    """Run ``nit aggregate --scores <scores.yml> --tests-from <rubric>``.

    Returns the parsed scorecard JSON. Raises FileNotFoundError if ``nit``
    isn't reachable (so the caller can surface a clear install hint instead
    of a generic OS error).
    """
    nit = _nit_binary()
    if not nit:
        raise FileNotFoundError(
            "nit CLI not found — run `../nitpicker/install.sh` "
            "(commercial check score reuses the nitpicker engine)"
        )
    cmd = [
        nit,
        "aggregate",
        "--scores",
        str(scores_yml),
        "--tests-from",
        str(tests_from),
    ]
    if policy is not None:
        cmd += ["--policy", str(policy)]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"`nit aggregate` failed (rc={proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}"
        )
    # `nit aggregate` writes the scorecard to stdout (and/or a file); accept JSON
    # on stdout.
    out = proc.stdout.strip()
    if not out:
        raise RuntimeError("`nit aggregate` produced no stdout")
    return json.loads(out)
