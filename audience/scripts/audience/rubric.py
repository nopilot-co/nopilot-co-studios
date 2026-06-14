"""Derive + validate the reader-fit rubric (``rubric.yml``).

The rubric is **derived from** the reader model's ``need_state``: each need
becomes one weighted scored test in the nitpicker test-definition shape, so the
audience studio scores against the nitpicker engine with no duplicate math. The
deterministic part — one test per need, priority→weight, gates from critical
needs — lives here; the *judgment* (the question wording + the concrete criteria
the reader judges by) is the scoring-rubric skill's, filled into the draft.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from . import SCHEMAS, load_yaml, store

RUBRIC_FILE = "rubric.yml"

# Need priority → rubric test weight. Critical needs also become gates.
PRIORITY_WEIGHT = {"critical": 2.0, "high": 1.5, "medium": 1.0, "low": 0.5}

_CRITERIA_STUB = (
    "<!-- fill: the concrete signals THIS reader uses to judge this need is met -->"
)


def rubric_path(slug: str) -> Path:
    return store.slug_dir(slug) / RUBRIC_FILE


def exists(slug: str) -> bool:
    return rubric_path(slug).is_file()


def read(slug: str) -> dict:
    p = rubric_path(slug)
    if not p.is_file():
        raise FileNotFoundError(
            f"no rubric for '{slug}' — run `audience rubric derive --audience {slug}`"
        )
    return load_yaml(p.read_text())


def write(slug: str, data: dict) -> None:
    rubric_path(slug).write_text(yaml.safe_dump(data, sort_keys=False))


# ----------------------------------------------------------------- validation
def _schema() -> dict:
    return json.loads((SCHEMAS / "rubric.schema.json").read_text())


def validate(data: dict) -> list[str]:
    validator = Draft202012Validator(_schema())
    errors = [
        (".".join(str(p) for p in e.absolute_path) or "<root>") + ": " + e.message
        for e in sorted(
            validator.iter_errors(data), key=lambda e: list(e.absolute_path)
        )
    ]
    # Cross-checks the schema can't express:
    test_slugs = {t.get("test") for t in data.get("tests", [])}
    for g in data.get("gates", []):
        if g not in test_slugs:
            errors.append(f"gates: '{g}' is not one of the rubric's test slugs")
    for t in data.get("tests", []):
        if _CRITERIA_STUB in (t.get("criteria") or []):
            errors.append(
                f"tests/{t.get('test')}: criteria still has the unfilled stub "
                "(the scoring-rubric skill must replace it)"
            )
    return errors


def validate_slug(slug: str) -> list[str]:
    if not exists(slug):
        return [f"no rubric for '{slug}' — run `audience rubric derive`"]
    return validate(read(slug))


# ----------------------------------------------------------------- derive
def _title(need_id: str) -> str:
    return need_id.replace("-", " ").capitalize()


def derive(slug: str) -> dict:
    """Build a draft ``rubric.yml`` from the model's need-state. One test per real
    need; weight by priority; gates from critical needs. Idempotent overwrite."""
    model = store.read(slug)
    needs = [
        n
        for n in model.get("need_state", {}).get("needs", [])
        if n.get("id") and n.get("id") != "placeholder" and n.get("statement")
    ]
    if not needs:
        raise ValueError(
            f"reader model '{slug}' has no real needs yet — the psychographic-profile "
            "skill must fill need_state.needs before deriving a rubric"
        )

    tests = []
    gates = []
    for n in needs:
        priority = n.get("priority", "medium")
        weight = PRIORITY_WEIGHT.get(priority, 1.0)
        if priority == "critical":
            gates.append(n["id"])
        tests.append(
            {
                "test": n["id"],
                "name": _title(n["id"]),
                "question": f"Does the work meet the reader's need: «{n['statement']}»?",
                "dimension": "reader-fit",
                "scale": {"min": 1, "max": 5},
                "criteria": [_CRITERIA_STUB],
                "weight": weight,
                "threshold": {"pass": 4, "warn": 3},
            }
        )

    data = {
        "rubric": slug,
        "derived_from": store.AUDIENCE_FILE,
        "scale": {"min": 1, "max": 5},
        "gates": gates,
        "tests": tests,
    }
    write(slug, data)
    return data
