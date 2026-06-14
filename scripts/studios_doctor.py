"""Unified readiness check across orchestrators and studio CLIs (issue #104)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _which(name: str) -> str | None:
    return shutil.which(name)


def _cli_version(cmd: str) -> str | None:
    path = _which(cmd)
    if not path:
        return None
    try:
        out = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        line = (out.stdout or out.stderr or "").strip().splitlines()
        return line[0] if line else path
    except (OSError, subprocess.TimeoutExpired):
        return path


def _studio_cli_for(path: str) -> tuple[str | None, str]:
    """Return (cli_name, install_hint) for a studio directory."""
    hints = {
        "design": "cd design && ./install.sh",
        "messaging": "cd messaging && ./install.sh",
        "nitpicker": "cd nitpicker && ./install.sh",
        "audience": "cd audience && ./install.sh",
        "motion": "cd motion && ./install.sh",
        "commercial": "cd commercial && ./install.sh",
        "delivery": "cd delivery && ./install.sh",
        "architecture": "cd architecture && ./install.sh",
        "context-studio": "cd context-studio && ./install.sh",
        "analytics": "cd analytics && ./install.sh",
        "growth": "cd growth && ./install.sh",
    }
    cli_map = {
        "design": "studio",
        "messaging": "message",
        "nitpicker": "nit",
        "audience": "audience",
        "motion": "motion",
        "commercial": "commercial",
        "delivery": "delivery",
        "architecture": "architecture",
        "context-studio": "context",
        "analytics": "analytics",
        "growth": "growth",
    }
    cli = cli_map.get(path)
    if not cli:
        return None, hints.get(path, f"see {path}/README.md")
    return _which(cli), hints.get(path, f"see {path}/README.md")


def doctor() -> dict:
    """Check planner, engagement, and each active studio CLI from studios.yml."""
    import yaml

    registry = yaml.safe_load((REPO_ROOT / "studios.yml").read_text())
    orchestrators = {
        "planner": _which("planner"),
        "engagement": _which("engagement"),
    }
    studios: list[dict] = []
    for entry in registry.get("studios", []):
        if entry.get("status") != "active":
            continue
        cli_path, hint = _studio_cli_for(entry["path"])
        studios.append(
            {
                "slug": entry["slug"],
                "cli": cli_path,
                "ready": cli_path is not None,
                "install": hint,
            }
        )
    return {
        "orchestrators": orchestrators,
        "studios": studios,
        "all_ready": all(orchestrators.values()) and all(s["ready"] for s in studios),
    }


def main() -> None:
    rep = doctor()
    print("Studios doctor")
    for name, path in rep["orchestrators"].items():
        if path:
            print(f"  ✓ {name:<12} {path}")
        else:
            print(f"  ✗ {name:<12} →  pip install -e scripts/{name}")
    print("\nActive studios:")
    for s in rep["studios"]:
        if s["ready"]:
            print(f"  ✓ {s['slug']:<14} {s['cli']}")
        else:
            print(f"  ✗ {s['slug']:<14} →  {s['install']}")
    if not rep["all_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
