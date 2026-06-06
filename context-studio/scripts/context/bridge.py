"""Resolve + invoke each tool CLI over the boundary.

Same pattern as ``audience/scripts/audience/nit_bridge.py`` and
``commercial/scripts/commercial/nit_bridge.py``. We never import a tool's
Python module — that would violate the dumb-tool invariant (ADR-004). We
shell out to the CLI binary, finding it on PATH or in a sibling
``tools/<name>/.venv/bin/<cli>`` for editable dev installs.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import TOOLS


def _tool_binary(cli: str) -> str | None:
    """Resolve a tool CLI. PATH first; sibling venv as a fallback."""
    on_path = shutil.which(cli)
    if on_path:
        return on_path
    here = Path(__file__).resolve()
    # Tools live at <studios>/tools/<name>/ ; venv at <name>/.venv/bin/<cli>.
    for parent in here.parents:
        # walk up to the studios root, then look at tools/
        candidate = parent / "tools" / cli / ".venv" / "bin" / cli
        if candidate.is_file():
            return str(candidate)
    return None


def reachable(cli: str) -> bool:
    return _tool_binary(cli) is not None


def reachability_report() -> dict[str, bool]:
    """Per-tool reachability — backs `context doctor`."""
    return {name: reachable(cli) for cli, name in TOOLS.items()}


def run(cli: str, args: list[str]) -> subprocess.CompletedProcess:
    """Invoke a tool CLI. Raises FileNotFoundError when the tool isn't reachable."""
    binary = _tool_binary(cli)
    if not binary:
        raise FileNotFoundError(
            f"tool CLI '{cli}' not reachable — install it from tools/{cli}/install.sh"
        )
    cmd = [binary, *args]
    return subprocess.run(cmd, check=False, capture_output=True, text=True)
