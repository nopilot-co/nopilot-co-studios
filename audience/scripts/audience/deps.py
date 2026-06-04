"""``audience doctor`` checks: is the studio wired up to model + score?

The audience studio's only hard dependency is the nitpicker ``nit`` CLI, which it
shells out to for reader-fit scoring (the engine is single-sourced there). Research
tooling (transcript/web review) lives in the LLM host, not this package.
"""

from __future__ import annotations

from . import __version__, audience_root_base, nit_bridge, store


def doctor() -> dict:
    return {
        "version": __version__,
        "nit_cli": nit_bridge.nit_cli(),  # path or None
        "store": str(audience_root_base()),
        "models": store.list_models(),
    }
