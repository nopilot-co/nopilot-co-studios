"""Format contracts: purpose × export, resolved by layered merge.

A format slug is ``<purpose>-<export>`` (e.g. ``pitch-pdf``). Its contract is the
deep-merge of ``purposes/<purpose>.yml`` <- ``exports/<export>.yml`` <- the slug
file's ``overrides`` block. The purpose centralises intent (style guide,
execution brief, ruleset); the export layers on asset-type specifics.

This module is deterministic glue only — no judgment. It resolves, validates, and
applies the *count-based* ruleset (max_pages, max_slides). Subjective rules
(required sections, tone, CTA presence) are enforced by the ``visual-qa`` skill.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from . import FORMATS, SCHEMAS


def _purposes_dir() -> Path:
    return FORMATS / "purposes"


def _exports_dir() -> Path:
    return FORMATS / "exports"


def slug_path(slug: str) -> Path:
    return FORMATS / f"{slug}.yml"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing format file: {path}")
    with path.open() as f:
        return yaml.safe_load(f) or {}


def list_formats() -> list[str]:
    """All defined format slugs (the *.yml files at the formats/ root)."""
    if not FORMATS.exists():
        return []
    return sorted(p.stem for p in FORMATS.glob("*.yml"))


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge overlay onto base. Dicts merge; everything else replaces."""
    out = copy.deepcopy(base)
    for key, val in (overlay or {}).items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


def resolve(slug: str) -> dict[str, Any]:
    """Resolve a format slug into its merged contract.

    Order: purposes/<extends> <- exports/<export> <- slug overrides.
    Raises FileNotFoundError if the slug file or a referenced layer is missing.
    """
    spec = _load_yaml(slug_path(slug))
    purpose = spec.get("extends")
    export = spec.get("export")
    if not purpose or not export:
        raise ValueError(f"{slug}.yml must set both `extends` (purpose) and `export`")

    base = _load_yaml(_purposes_dir() / f"{purpose}.yml")
    overlay = _load_yaml(_exports_dir() / f"{export}.yml")

    # Both layers carry a top-level `name`; compose them instead of letting the
    # export's name clobber the purpose's during the merge.
    purpose_name = base.get("name", purpose)
    export_name = overlay.get("name", export)

    merged = _deep_merge(base, overlay)
    merged = _deep_merge(merged, spec.get("overrides", {}))

    # Canonical identity always reflects the slug, not whatever the layers said.
    merged["slug"] = slug
    merged["purpose"] = purpose
    merged["export"] = export
    merged["purpose_name"] = purpose_name
    merged["export_name"] = export_name
    merged["name"] = f"{purpose_name} · {export_name}"
    return merged


def validate(slug: str) -> list[str]:
    """Return a list of validation errors for a slug (empty = valid)."""
    errors: list[str] = []
    try:
        resolved = resolve(slug)
    except (FileNotFoundError, ValueError) as e:
        return [str(e)]

    schema_path = SCHEMAS / "format.schema.json"
    if not schema_path.exists():
        return ["format.schema.json missing from plugin"]
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)
    for e in validator.iter_errors(resolved):
        loc = ".".join(str(p) for p in e.absolute_path) or "<root>"
        errors.append(f"{loc}: {e.message}")
    return errors


def studio_format(resolved: dict[str, Any]) -> str | None:
    """The short studio render format (pdf|pptx|html|revealjs), or None if unrenderable."""
    return (resolved.get("render") or {}).get("studio_format")


def is_renderable(resolved: dict[str, Any]) -> bool:
    return studio_format(resolved) is not None and (resolved.get("ruleset") or {}).get(
        "supported", True
    )


def show(slug: str) -> str:
    return yaml.safe_dump(resolve(slug), sort_keys=False, default_flow_style=False)


def check_output(resolved: dict[str, Any], outputs: dict[str, Path]) -> list[str]:
    """Deterministic ruleset enforcement against rendered artifacts.

    Returns a list of hard violations (empty = within the ruleset). Only checks
    rules a machine can verify; subjective rules are left to visual-qa.
    """
    ruleset = resolved.get("ruleset") or {}
    violations: list[str] = []

    for fmt, path in outputs.items():
        path = Path(path)
        if not path.exists():
            continue
        if fmt == "pdf" and "max_pages" in ruleset:
            pages = _pdf_page_count(path)
            if pages is not None and pages > ruleset["max_pages"]:
                violations.append(
                    f"{path.name}: {pages} pages exceeds max_pages={ruleset['max_pages']}"
                )
        if fmt == "pptx" and "max_slides" in ruleset:
            slides = _pptx_slide_count(path)
            if slides is not None and slides > ruleset["max_slides"]:
                violations.append(
                    f"{path.name}: {slides} slides exceeds max_slides={ruleset['max_slides']}"
                )
    return violations


def _pdf_page_count(pdf: Path) -> int | None:
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return None
    return len(pdfium.PdfDocument(str(pdf)))


def _pptx_slide_count(pptx: Path) -> int | None:
    try:
        from pptx import Presentation
    except ImportError:
        return None
    return len(Presentation(str(pptx)).slides)
