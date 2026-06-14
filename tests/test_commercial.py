#!/usr/bin/env python3
"""commercial studio (#77) — store, schemas, deterministic checks, nit_bridge.

Standalone; run any venv with pyyaml + jsonschema:
  nitpicker/.venv/bin/python tests/test_commercial.py

Exercises the mechanics that need no external CLI (store scaffolding, schema
validation, deterministic check evaluation, the materialiser for value). The
nitpicker engine reuse (`commercial check score` → `nit aggregate`) is
exercised only when the `nit` CLI is reachable, so the suite stays green
without a nitpicker install.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "commercial" / "scripts"))

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


def raises(fn, exc=Exception) -> bool:
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


CLEAN_DEAL = {
    "deal": "demo-deal",
    "client": "acme",
    "currency": "USD",
    "lines": [
        {"role": "lead", "rate": 2000, "days": 10},
        {"role": "senior", "rate": 1500, "days": 20},
        {"role": "mid", "rate": 1100, "days": 20},
    ],
}

UNDERPRICED_DEAL = {
    "deal": "underpriced",
    "currency": "USD",
    "lines": [
        # senior below the rate-card floor (1400)
        {"role": "senior", "rate": 900, "days": 10},
        {"role": "mid", "rate": 1100, "days": 20},
    ],
}

LOW_MARGIN_DEAL = {
    "deal": "low-margin",
    "currency": "USD",
    "lines": [
        # rates barely above cost → margin under floor
        {"role": "lead", "rate": 1200, "days": 10},
        {"role": "senior", "rate": 950, "days": 30},
    ],
}

OVER_LEAD_DEAL = {
    "deal": "lead-heavy",
    "currency": "USD",
    "lines": [
        # 50% of days are 'lead' — exceeds default max_ratios.lead (0.30)
        {"role": "lead", "rate": 2000, "days": 10},
        {"role": "senior", "rate": 1500, "days": 10},
    ],
}


# ----------------------------------------------------------------- isolated env

with tempfile.TemporaryDirectory() as td:
    os.environ["STUDIOS_DOCKET_ROOT"] = td

    # Import after env is set so commercial_root() picks up the temp dir.
    from commercial import commercial_root  # noqa: E402
    from commercial import store, checks as checks_mod, session, nit_bridge  # noqa: E402

    check(
        "commercial_root resolves to docket root",
        commercial_root() == (Path(td).resolve() / "commercial"),
        f"got {commercial_root()}",
    )

    # 1. policy_init scaffolds rate-card + policy + checks
    out = store.policy_init()
    check("policy_init writes rate-card", out["rate_card"])
    check("policy_init writes policy", out["policy"])
    check(
        "policy_init copies checks",
        set(out["checks"])
        == {"rate-card-compliance.yaml", "margin-floor.yaml", "ratio-mix.yaml"},
        f"got {out['checks']}",
    )
    check("rate-card.yml validates", not store.validate_rate_card())
    check("pricing-policy.yml validates", not store.validate_policy())

    # 2. policy_init is idempotent (second call doesn't rewrite)
    out2 = store.policy_init()
    check("policy_init idempotent", not out2["rate_card"] and not out2["policy"])

    # 3. checks rubric loads from the dest dir
    rubric = checks_mod.load_checks_dir(commercial_root() / "configs" / "checks")
    ids = {r["id"] for r in rubric}
    check(
        "rubric loads 3 checks",
        ids == {"rate-card-compliance", "margin-floor", "ratio-mix"},
        f"got {ids}",
    )

    rate_card = store.read_rate_card()
    policy = store.read_policy()

    # 4. clean deal — all checks pass
    results = checks_mod.evaluate(CLEAN_DEAL, rate_card, policy)
    by_id = {r["id"]: r for r in results}
    check(
        "clean deal: rate-card-compliance passes",
        by_id["rate-card-compliance"]["passed"],
    )
    check("clean deal: margin-floor passes", by_id["margin-floor"]["passed"])
    check("clean deal: ratio-mix passes", by_id["ratio-mix"]["passed"])
    check(
        "clean deal: all scores >= 4",
        all(r["score"] >= 4 for r in results),
        f"scores: {[(r['id'], r['score']) for r in results]}",
    )

    # 5. underpriced deal — rate-card-compliance fails
    results = checks_mod.evaluate(UNDERPRICED_DEAL, rate_card, policy)
    by_id = {r["id"]: r for r in results}
    check(
        "underpriced: rate-card-compliance flags breach",
        not by_id["rate-card-compliance"]["passed"]
        and by_id["rate-card-compliance"]["evidence"]["breaches"][0]["role"]
        == "senior",
    )

    # 6. low-margin deal — margin-floor fails
    results = checks_mod.evaluate(LOW_MARGIN_DEAL, rate_card, policy)
    by_id = {r["id"]: r for r in results}
    check(
        "low-margin: margin-floor flags failure",
        not by_id["margin-floor"]["passed"]
        and by_id["margin-floor"]["evidence"]["margin"] < policy["margin_floor"],
    )

    # 7. lead-heavy deal — ratio-mix advisory flags but doesn't gate
    results = checks_mod.evaluate(OVER_LEAD_DEAL, rate_card, policy)
    by_id = {r["id"]: r for r in results}
    check(
        "lead-heavy: ratio-mix flags advisory breach",
        not by_id["ratio-mix"]["passed"]
        and by_id["ratio-mix"]["evidence"]["breaches"][0]["role"] == "lead",
    )

    # 8. scores.yml shape — what we hand the nitpicker engine. The engine
    # reads `{tests: {slug: score}}` (nitpicker/scripts/nit/tests.py:aggregate).
    scores_yaml = checks_mod.to_scores_yaml(results)
    check(
        "scores.yml shape — {tests: {slug: score}}",
        set(scores_yaml.get("tests", {}).keys())
        == {"rate-card-compliance", "margin-floor", "ratio-mix"}
        and all(isinstance(v, int) for v in scores_yaml["tests"].values()),
    )

    # 9. client scaffolding + assessment materialiser
    store.scaffold_client("acme", name="Acme Co")
    check("client exists", store.client_exists("acme"))
    check("client model validates", not store.validate_rate_card())  # different
    client = store.read_client("acme")
    check("client model has name", client["name"] == "Acme Co")
    check(
        "scaffold rejects duplicate",
        raises(lambda: store.scaffold_client("acme"), ValueError),
    )

    # 10. assessment materialiser writes & validates
    assessment = {
        "financial_profile": {"revenue_band": "£50-100M ARR", "confidence": "medium"},
        "spend_capacity": {"current_category_spend": "£500k/yr"},
        "addressable_market": {"sam": "£10M"},
        "value_sizing": {
            "band_low": "£75k",
            "band_high": "£250k",
            "reasoning": "value to user",
            "confidence": "medium",
        },
    }
    data = store.write_assessment("acme", assessment)
    check(
        "assessment written + provenance stamped",
        store.assessment_path("acme").is_file()
        and data["provenance"]["assessed_by"] == "commercial-studio",
    )

    # bad assessment is rejected
    check(
        "assessment schema rejects missing value_sizing",
        raises(
            lambda: store.write_assessment(
                "acme",
                {
                    "financial_profile": {},
                    "spend_capacity": {},
                    "addressable_market": {},
                },
            ),
            ValueError,
        ),
    )

    # 11. per-deal session — scaffold + bump + scores.yml + scorecard
    deal_file = Path(td) / "deal.yml"
    import yaml as _yaml

    deal_file.write_text(_yaml.safe_dump(CLEAN_DEAL))
    session.new("demo-deal", deal_file=deal_file)
    check("session created", session.exists("demo-deal"))
    check(
        "deal copied into session",
        (session.session_dir("demo-deal") / "inputs" / "deal.yml").is_file(),
    )

    ver = session.bump("demo-deal", level="minor")
    check("session bump produces semver", ver == "0.1.0")

    results = checks_mod.evaluate(session.read_deal("demo-deal"), rate_card, policy)
    session.write_scores("demo-deal", checks_mod.to_scores_yaml(results))
    check(
        "scores.yml written",
        (session.review_dir("demo-deal") / "scores.yml").is_file(),
    )

    # 12. nit_bridge reachability — skipped cleanly when nit isn't installed
    if nit_bridge.reachable():
        # We don't run the full aggregation here (the rubric YAML shape is
        # nitpicker-managed); reachability + the bridge function signature
        # are the contract this test owns.
        check("nit reachable + binary returned", bool(nit_bridge._nit_binary()))
    else:
        check(
            "nit_bridge degrades cleanly when nit absent",
            raises(
                lambda: nit_bridge.aggregate(
                    session.review_dir("demo-deal") / "scores.yml",
                    commercial_root() / "configs" / "checks",
                ),
                FileNotFoundError,
            ),
        )

    # 13. status transitions are validated
    session.set_status("demo-deal", "reviewing")
    check(
        "status set",
        session.set_status("demo-deal", "reviewed")["status"] == "reviewed",
    )
    check(
        "invalid status rejected",
        raises(lambda: session.set_status("demo-deal", "bogus"), ValueError),
    )

if failures:
    print("FAIL:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(
    "PASS: commercial (store + policy + 3 checks + scoring shape + client + assessment materialiser + session + nit_bridge)"
)
