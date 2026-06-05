"""``commercial doctor`` — is the studio wired up to do real work?

The commercial studio has no native render tooling of its own. Its only hard
dependency is the nitpicker ``nit`` CLI (used to aggregate scores into a
verdict). This reports its reachability.
"""

from __future__ import annotations

from . import __version__, commercial_root
from . import nit_bridge
from . import store


def doctor() -> dict:
    """Status of the studio's wiring: nit reachable, store present, policy valid."""
    rc = store.validate_rate_card()
    pol = store.validate_policy()
    return {
        "version": __version__,
        "commercial_root": str(commercial_root()),
        "nit_reachable": nit_bridge.reachable(),
        "rate_card_ok": not rc,
        "rate_card_issues": rc,
        "policy_ok": not pol,
        "policy_issues": pol,
        "client_count": len(store.list_clients()),
    }
