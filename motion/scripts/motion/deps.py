"""Runtime dependency + provider detection for the motion studio.

Native render tools (node/npx for Remotion, ffmpeg) and external render
providers (avatar, TTS) can't be pip-installed or vendored, so the studio
*declares* what it needs, *detects* presence here, and *degrades* with
actionable messages. `motion doctor` reports status. This module never installs
anything and never reads secrets out of the docket — provider keys come from the
environment only.

(Later slices will move the per-format `requires` declarations into
`formats/exports/<export>.yml`, mirroring the design studio; S0 keeps the tool
set inline since formats aren't defined yet.)
"""

from __future__ import annotations

import os
import shutil

# Local render tools (binaries on PATH).
TOOLS = {
    "node": "brew install node            # Remotion (React) video render via npx",
    "ffmpeg": "brew install ffmpeg          # encode MP4/WebM/GIF + extract QA keyframes",
}

# Optional — enables the HTML→frames capture fallback when Remotion is overkill.
OPTIONAL_TOOLS = {
    "playwright": "pip install 'motion-studio[capture]' && playwright install chromium",
}

# External render providers — render-time services, configured via env secrets.
# (name -> (env var, what it provides))
PROVIDERS = {
    "d-id": ("DID_API_KEY", "avatar lip-sync video (digital-twin presenter)"),
    "elevenlabs": ("ELEVENLABS_API_KEY", "text-to-speech / cloned twin voice"),
}


def have(tool: str) -> bool:
    """Is the tool available? (playwright is a Python package, not a binary.)"""
    if tool == "playwright":
        try:
            import playwright  # noqa: F401

            return True
        except ImportError:
            return False
    return bool(shutil.which(tool))


def provider_configured(name: str) -> bool:
    env = PROVIDERS.get(name, (None, None))[0]
    return bool(env and os.environ.get(env))


def doctor() -> dict:
    """Tool presence + provider configuration."""
    return {
        "tools": {t: have(t) for t in TOOLS},
        "optional": {t: have(t) for t in OPTIONAL_TOOLS},
        "providers": {
            name: {
                "configured": provider_configured(name),
                "env": PROVIDERS[name][0],
                "use": PROVIDERS[name][1],
            }
            for name in PROVIDERS
        },
    }
