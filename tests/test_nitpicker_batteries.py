#!/usr/bin/env python3
"""nitpicker phase 4 batteries (#89) — new QA + brand-guardian tests.

Standalone; run any venv with pyyaml + jsonschema:
  nitpicker/.venv/bin/python tests/test_nitpicker_batteries.py

Verifies:
- All shipped tests in configs/tests/ load and validate against the
  nitpicker's test.schema.json.
- The 6 new Phase-4 tests are present.
- Each new test declares the right dimension and (for gates) is wired into
  review-policy.yml's gates list.
- review-policy.yml has weights for the 3 new dimensions (technical-quality,
  delivery-quality, brand-integrity).
- The aggregation engine treats the new gates as gates: a critical-gate
  failure on `the-correctness-test` or `the-brand-recognition-test` flips
  the verdict to `fail` even when the rest of the battery scores well.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "nitpicker" / "scripts"))

from nit import tests as nit_tests  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


CONFIGS = REPO / "configs"
TEST_SCHEMA = json.loads(
    (
        REPO / "nitpicker" / "scripts" / "nit" / "schemas" / "test.schema.json"
    ).read_text()
)
TEST_VALIDATOR = Draft202012Validator(TEST_SCHEMA)

# Phase 4 — the six new tests + dimensions + gates
PHASE_4_TESTS = {
    "the-correctness-test": {"dimension": "technical-quality", "gate": True},
    "the-completeness-test": {"dimension": "technical-quality", "gate": False},
    "the-readiness-test": {"dimension": "delivery-quality", "gate": False},
    "the-actionability-test": {"dimension": "delivery-quality", "gate": False},
    "the-voice-fidelity-test": {"dimension": "brand-integrity", "gate": False},
    "the-brand-recognition-test": {"dimension": "brand-integrity", "gate": True},
}
PHASE_4_DIMENSIONS = {"technical-quality", "delivery-quality", "brand-integrity"}

# 1. All shipped tests load + validate
test_files = sorted((CONFIGS / "tests").glob("*.yaml"))
check("at least 9 tests shipped (3 original + 6 phase-4)", len(test_files) >= 9)

loaded = {}
for p in test_files:
    data = yaml.safe_load(p.read_text()) or {}
    errors = list(TEST_VALIDATOR.iter_errors(data))
    check(
        f"{p.name}: schema-valid",
        not errors,
        f"errors: {[e.message for e in errors]}",
    )
    loaded[data.get("test")] = data

# 2. Every Phase 4 test is present with the right dimension
for slug, expected in PHASE_4_TESTS.items():
    check(f"phase-4 test present: {slug}", slug in loaded, f"loaded: {sorted(loaded)}")
    if slug not in loaded:
        continue
    spec = loaded[slug]
    check(
        f"{slug}: dimension == {expected['dimension']}",
        spec.get("dimension") == expected["dimension"],
        f"got {spec.get('dimension')}",
    )

# 3. review-policy.yml — gates + dimension weights
policy = yaml.safe_load((CONFIGS / "default" / "review-policy.yml").read_text())
gates = set(policy.get("gates") or [])
check(
    "policy gates include the-correctness-test",
    "the-correctness-test" in gates,
    f"gates: {gates}",
)
check(
    "policy gates include the-brand-recognition-test",
    "the-brand-recognition-test" in gates,
    f"gates: {gates}",
)
# Existing gates not regressed
check("existing gate the-sniff-test preserved", "the-sniff-test" in gates)
check("existing gate brief-fulfilment preserved", "brief-fulfilment" in gates)

dim_weights = (policy.get("weights") or {}).get("dimensions") or {}
for dim in PHASE_4_DIMENSIONS:
    check(
        f"policy weights include dimension '{dim}'",
        dim in dim_weights,
        f"got: {sorted(dim_weights)}",
    )
    check(
        f"policy weight for '{dim}' > 0",
        float(dim_weights.get(dim, 0)) > 0,
    )

# Existing dimensions still weighted
for dim in ("visual-qa", "brief-fulfilment", "audience-fit", "tone-of-voice"):
    check(f"existing dimension '{dim}' weight preserved", dim in dim_weights)

# 4. Gate behaviour — a critical-gate failure flips the verdict to 'fail'
# even when the rest of the battery scores 5/5. The engine reads gates from
# policy + per-call additions; we hand a synthetic scores payload to the
# aggregation function and check the verdict.

# All 5s except the correctness gate at 1 → must fail
all_tests = list(loaded)
scores_all_high_but_correctness = {
    "tests": {t: 5 for t in all_tests},
    "dimensions": {},
}
scores_all_high_but_correctness["tests"]["the-correctness-test"] = 1

# Build a `specs` dict so the engine knows each test's metadata (weight,
# scale, etc.) without re-loading from disk:
specs = {slug: data for slug, data in loaded.items()}
result = nit_tests.aggregate(
    scores_all_high_but_correctness,
    specs=specs,
    policy=policy,
)
check(
    "correctness gate failure forces verdict=fail (even with rest at 5)",
    result["verdict"] == "fail",
    f"got verdict={result['verdict']} overall={result.get('overall')}",
)
check(
    "gates_failed includes the-correctness-test",
    "the-correctness-test" in (result.get("gates_failed") or []),
    f"got gates_failed={result.get('gates_failed')}",
)

# brand-recognition gate failure also forces fail
scores_brand_fail = {
    "tests": {t: 5 for t in all_tests},
    "dimensions": {},
}
scores_brand_fail["tests"]["the-brand-recognition-test"] = 1
result = nit_tests.aggregate(scores_brand_fail, specs=specs, policy=policy)
check(
    "brand-recognition gate failure forces verdict=fail",
    result["verdict"] == "fail",
    f"got verdict={result['verdict']}",
)

# 5. Clean run — all 5s → verdict=pass
all_high = {"tests": {t: 5 for t in all_tests}, "dimensions": {}}
result = nit_tests.aggregate(all_high, specs=specs, policy=policy)
check(
    "all-5s → verdict=pass",
    result["verdict"] == "pass",
    f"got verdict={result['verdict']} overall={result.get('overall')}",
)

# 6. README catalogue mention
readme = (CONFIGS / "README.md").read_text()
for slug in PHASE_4_TESTS:
    check(f"configs/README.md mentions {slug}", slug in readme)

# 7. The studio.yaml dimensions list includes the new dimensions
studio_yaml = yaml.safe_load((REPO / "nitpicker" / "studio.yaml").read_text())
caps = studio_yaml.get("capabilities") or []
review_asset = next((c for c in caps if c.get("id") == "review-asset"), None)
check("nitpicker review-asset capability present", review_asset is not None)
if review_asset:
    dims = set(review_asset.get("dimensions") or [])
    for d in PHASE_4_DIMENSIONS:
        check(f"nitpicker/studio.yaml dimensions includes '{d}'", d in dims)

if failures:
    print("FAIL:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(
    "PASS: nitpicker batteries (9+ tests load/validate + 6 phase-4 tests + "
    "3 new dimensions in policy + new gates wired + aggregate honors gates + "
    "README + studio.yaml updated)"
)
