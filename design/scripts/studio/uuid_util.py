"""Crockford-base32 identifiers for docket sync (ADR-0001)."""

from __future__ import annotations

import re
import secrets

# Crockford base32 — excludes I, L, O, U to reduce transcription errors.
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_UUID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{6}$")


def mint_production_uuid(length: int = 6) -> str:
    """Return a random Crockford-base32 production id (default 6 chars)."""
    return "".join(secrets.choice(_CROCKFORD) for _ in range(length))


def is_valid_production_uuid(value: str) -> bool:
    return bool(_UUID_RE.match(value))
