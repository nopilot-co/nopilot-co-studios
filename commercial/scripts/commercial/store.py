"""The shared commercial store: rate cards, pricing policy, per-client models.

Mechanics for the studios-level commercial store (parallel to brand /
audience). No judgment.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from . import CONFIGS_LOCAL, SCHEMAS, commercial_root, load_yaml

RATE_CARD_FILE = "rate-card.yml"
POLICY_FILE = "pricing-policy.yml"
CLIENT_FILE = "_client.yml"
ASSESSMENT_FILE = "assessment.yml"
CLIENT_STATUSES = ("draft", "active", "archived")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text())


def _validate(kind: str, data: dict) -> list[str]:
    validator = Draft202012Validator(_schema(kind))
    return [
        (".".join(str(p) for p in e.absolute_path) or "<root>") + ": " + e.message
        for e in sorted(
            validator.iter_errors(data), key=lambda e: list(e.absolute_path)
        )
    ]


# ----------------------------------------------------------------- org-wide


def rate_card_path() -> Path:
    return commercial_root() / RATE_CARD_FILE


def policy_path() -> Path:
    return commercial_root() / POLICY_FILE


def rate_card_exists() -> bool:
    return rate_card_path().is_file()


def policy_exists() -> bool:
    return policy_path().is_file()


def read_rate_card() -> dict:
    return load_yaml(rate_card_path().read_text())


def read_policy() -> dict:
    return load_yaml(policy_path().read_text())


def write_rate_card(data: dict) -> None:
    errs = _validate("rate-card", data)
    if errs:
        raise ValueError("invalid rate card:\n  " + "\n  ".join(errs))
    rate_card_path().parent.mkdir(parents=True, exist_ok=True)
    rate_card_path().write_text(yaml.safe_dump(data, sort_keys=False))


def write_policy(data: dict) -> None:
    errs = _validate("pricing-policy", data)
    if errs:
        raise ValueError("invalid pricing policy:\n  " + "\n  ".join(errs))
    policy_path().parent.mkdir(parents=True, exist_ok=True)
    policy_path().write_text(yaml.safe_dump(data, sort_keys=False))


def validate_rate_card() -> list[str]:
    if not rate_card_exists():
        return [f"no rate card at {rate_card_path()} — run `commercial policy init`"]
    return _validate("rate-card", read_rate_card())


def validate_policy() -> list[str]:
    if not policy_exists():
        return [f"no pricing policy at {policy_path()} — run `commercial policy init`"]
    return _validate("pricing-policy", read_policy())


# Templates we copy on `policy init`. Hand-edit after copy.
_RATE_CARD_TEMPLATE = {
    "currency": "USD",
    "unit": "day",
    "roles": [
        {"role": "principal", "rate": 2500, "cost": 1500},
        {"role": "lead", "rate": 1800, "cost": 1100},
        {"role": "senior", "rate": 1400, "cost": 850},
        {"role": "mid", "rate": 1000, "cost": 600},
        {"role": "junior", "rate": 700, "cost": 400},
    ],
}

_POLICY_TEMPLATE = {
    "margin_floor": 0.40,  # 40% gross margin floor
    "max_ratios": {
        # role → max share of total days (0-1)
        "principal": 0.20,
        "lead": 0.30,
    },
    "min_ratios": {
        # role → min share (0-1) — none by default
    },
    "notes": "Hand-edit after `commercial policy init`. Floors + ratios drive the beancounter rubric.",
}


def policy_init(*, force: bool = False) -> dict:
    """Scaffold rate-card + pricing-policy + the checks rubric. Idempotent."""
    out = {"rate_card": False, "policy": False, "checks": []}
    if force or not rate_card_exists():
        write_rate_card(_RATE_CARD_TEMPLATE)
        out["rate_card"] = True
    if force or not policy_exists():
        write_policy(_POLICY_TEMPLATE)
        out["policy"] = True
    # Copy bundled checks into <commercial_root>/configs/checks/ so they live
    # alongside the org policy and can be hand-edited per org.
    dest = commercial_root() / "configs" / "checks"
    dest.mkdir(parents=True, exist_ok=True)
    src = CONFIGS_LOCAL / "checks"
    if src.is_dir():
        for p in src.glob("*.yaml"):
            d = dest / p.name
            if force or not d.exists():
                shutil.copy2(p, d)
                out["checks"].append(p.name)
    return out


# ----------------------------------------------------------------- per-client


def client_dir(slug: str) -> Path:
    return commercial_root() / "clients" / slug


def client_path(slug: str) -> Path:
    return client_dir(slug) / CLIENT_FILE


def client_exists(slug: str) -> bool:
    return client_path(slug).is_file()


def read_client(slug: str) -> dict:
    if not client_exists(slug):
        raise FileNotFoundError(
            f"no client '{slug}' — run `commercial client new --client {slug}`"
        )
    return load_yaml(client_path(slug).read_text())


def write_client(slug: str, data: dict) -> None:
    errs = _validate("client", data)
    if errs:
        raise ValueError("invalid client model:\n  " + "\n  ".join(errs))
    client_dir(slug).mkdir(parents=True, exist_ok=True)
    client_path(slug).write_text(yaml.safe_dump(data, sort_keys=False))


def scaffold_client(slug: str, *, name: str | None = None) -> dict:
    if client_exists(slug):
        raise ValueError(f"client '{slug}' already exists at {client_path(slug)}")
    (client_dir(slug) / "research" / "sources").mkdir(parents=True, exist_ok=True)
    data = {
        "client": slug,
        "name": name or slug.replace("-", " ").title(),
        "status": "draft",
        "financial_profile": {},
        "spend_capacity": {},
        "addressable_market": {},
        "provenance": {"created": _now(), "sources": []},
    }
    write_client(slug, data)
    return data


def list_clients() -> list[str]:
    base = commercial_root() / "clients"
    if not base.exists():
        return []
    return sorted(p.name for p in base.iterdir() if (p / CLIENT_FILE).is_file())


def assessment_path(slug: str) -> Path:
    return client_dir(slug) / ASSESSMENT_FILE


def write_assessment(slug: str, data: dict) -> dict:
    """Materialise a caller-supplied assessment with provenance.

    Mirrors the materialiser pattern used in the tools tier (theme-entity,
    source-summarise). Validates against the assessment schema, stamps
    provenance + skill_version, writes <clients/<slug>/assessment.yml.
    """
    errs = _validate("assessment", data)
    if errs:
        raise ValueError("invalid assessment:\n  " + "\n  ".join(errs))
    if not client_exists(slug):
        raise FileNotFoundError(
            f"no client '{slug}' — run `commercial client new --client {slug}`"
        )
    data = dict(data)
    data["client"] = slug
    data.setdefault("provenance", {})["assessed"] = _now()
    data["provenance"].setdefault("assessed_by", "commercial-studio")
    assessment_path(slug).write_text(yaml.safe_dump(data, sort_keys=False))
    return data
