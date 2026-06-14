"""Format contracts: purpose × layout × export, resolved by layered merge.

A format slug is ``<purpose>-<export>`` (e.g. ``pitch-pdf``). Its contract is the
deep-merge of, in order:

    purposes/<purpose>.yml
        ← layouts/<layout>.yml      (defaults to ``linear`` if the slug omits it)
        ← exports/<export>.yml
        ← the slug file's ``overrides`` block

The purpose centralises intent (style guide, execution brief, ruleset); the
**layout** governs structural navigation (frame / linear / carousel — the third
orthogonal tier added in ADR-005); the export layers on asset-type specifics.

Any layer may declare ``seals:`` — a list of dotted paths that later layers may
not override. A conflict raises ``SealedKeyConflict`` (fail-closed; no silent
drift). The session is then expected to fork the contract (local-frozen or
global PR) and record the fork in ``version.json::built_against``.

This module is deterministic glue only — no judgment. Subjective rules
(required sections, tone, CTA presence) are enforced by the ``visual-qa`` skill.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator

from . import FORMATS, SCHEMAS

DEFAULT_LAYOUT = "linear"

# Fields stamped onto the resolved contract by ``resolve()`` for identity /
# display — excluded from ``contract_hash`` because they're derived, not
# governance terms. The hash governs the contract itself, not its label.
_HASH_EXCLUDE = {"slug", "name", "purpose_name", "layout_name", "export_name"}


class SealedKeyConflict(ValueError):
    """A layer attempted to override a key sealed by an earlier layer."""


def _purposes_dir() -> Path:
    return FORMATS / "purposes"


def _layouts_dir() -> Path:
    return FORMATS / "layouts"


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


def list_layouts() -> list[str]:
    """All defined layout slugs (the *.yml files at formats/layouts/)."""
    d = _layouts_dir()
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.yml"))


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge overlay onto base. Dicts merge; everything else replaces.

    Pure dict merge — does NOT enforce seals. Use ``_merge_layers`` for that.
    """
    out = copy.deepcopy(base)
    for key, val in (overlay or {}).items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


def _walk_paths(d: Any, prefix: str = "") -> Iterable[str]:
    """Yield dotted paths to every leaf and intermediate dict in ``d``.

    Used to detect whether an overlay writes to a sealed path.
    """
    if isinstance(d, dict):
        for k, v in d.items():
            path = f"{prefix}.{k}" if prefix else k
            yield path
            if isinstance(v, dict):
                yield from _walk_paths(v, path)


def _merge_layers(layers: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    """Merge layers in order, honouring ``seals:`` declared by earlier layers.

    Each entry is ``(layer_name, layer_dict)``. A layer's own ``seals:`` list is
    consumed (stripped from the merge) and registered so any LATER layer that
    writes to a sealed path hard-fails with ``SealedKeyConflict``. Writes within
    the same layer that declares the seal are permitted (the layer owns the
    sealed value).
    """
    result: dict[str, Any] = {}
    sealed_by: dict[str, str] = {}
    for name, raw in layers:
        layer = copy.deepcopy(raw or {})
        my_seals = layer.pop("seals", []) if isinstance(layer, dict) else []
        for path in _walk_paths(layer):
            if path in sealed_by:
                raise SealedKeyConflict(
                    f"layer '{name}' attempts to override sealed key '{path}' "
                    f"(sealed by layer '{sealed_by[path]}'). Fork the layout "
                    f"(local-frozen contract or global PR) instead of overriding."
                )
        result = _deep_merge(result, layer)
        for seal_path in my_seals:
            sealed_by[seal_path] = name
    return result


def resolve(slug: str) -> dict[str, Any]:
    """Resolve a format slug into its merged contract.

    Order: ``purposes/<extends>`` ← ``layouts/<layout|linear>`` ← ``exports/<export>``
    ← slug overrides. Raises ``FileNotFoundError`` if a referenced layer is
    missing, ``ValueError`` if the slug is mis-declared, and
    ``SealedKeyConflict`` if a later layer would write to a sealed key.
    """
    spec = _load_yaml(slug_path(slug))
    purpose = spec.get("extends")
    export = spec.get("export")
    if not purpose or not export:
        raise ValueError(f"{slug}.yml must set both `extends` (purpose) and `export`")
    layout = spec.get("layout", DEFAULT_LAYOUT)

    purpose_layer = _load_yaml(_purposes_dir() / f"{purpose}.yml")
    layout_layer = _load_yaml(_layouts_dir() / f"{layout}.yml")
    export_layer = _load_yaml(_exports_dir() / f"{export}.yml")
    slug_overlay = spec.get("overrides", {}) or {}

    # Each carries a `name`; the merge would let later layers clobber the
    # purpose's. Capture them up front so the final identity is composed.
    purpose_name = purpose_layer.get("name", purpose)
    layout_name = layout_layer.get("name", layout)
    export_name = export_layer.get("name", export)

    merged = _merge_layers(
        [
            ("purpose", purpose_layer),
            ("layout", layout_layer),
            ("export", export_layer),
            ("slug", slug_overlay),
        ]
    )

    # Canonical identity always reflects the slug, not whatever layers said.
    merged["slug"] = slug
    merged["purpose"] = purpose
    merged["layout"] = layout
    merged["export"] = export
    merged["purpose_name"] = purpose_name
    merged["layout_name"] = layout_name
    merged["export_name"] = export_name
    merged["name"] = f"{purpose_name} · {export_name}"
    return merged


def validate_resolved(resolved: dict[str, Any]) -> list[str]:
    """Schema-validate an already-resolved contract (used at render time).

    Returns a list of human-readable errors (empty = valid). Splitting this
    from ``validate(slug)`` lets ``render.py`` fail-closed against the
    *effective* contract (which may be a local lock), not just the slug's
    global resolve.
    """
    schema_path = SCHEMAS / "format.schema.json"
    if not schema_path.exists():
        return ["format.schema.json missing from plugin"]
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for e in validator.iter_errors(resolved):
        loc = ".".join(str(p) for p in e.absolute_path) or "<root>"
        errors.append(f"{loc}: {e.message}")
    return errors


def validate(slug: str) -> list[str]:
    """Return a list of validation errors for a slug (empty = valid)."""
    try:
        resolved = resolve(slug)
    except (FileNotFoundError, ValueError) as e:
        return [str(e)]
    return validate_resolved(resolved)


def validate_asset_refs(resolved: dict[str, Any]) -> list[str]:
    """Each asset a format references must exist and support the format's export."""
    from . import assets as assets_mod

    export = resolved.get("export")
    known = set(assets_mod.list_assets())
    errors: list[str] = []
    for slug in resolved.get("assets", []) or []:
        if slug not in known:
            errors.append(f"unknown asset '{slug}'")
            continue
        asset = assets_mod.load_asset(None, slug)
        if export and not assets_mod.supports_export(asset, export):
            errors.append(f"asset '{slug}' does not support export '{export}'")
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


# ----------------------------------------------------------------- provenance


def contract_hash(resolved: dict[str, Any]) -> str:
    """Stable SHA-256 hex of a resolved contract.

    Excludes derived/identity fields so the hash governs the *contract* (the
    enforceable terms), not its display label. Sorts keys so the hash is stable
    across runs and Python versions.
    """
    governance = {k: v for k, v in resolved.items() if k not in _HASH_EXCLUDE}
    canonical = json.dumps(governance, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_local_lock(session_path: Path) -> dict[str, Any] | None:
    """Load ``<session>/contract.lock.yml`` if present.

    A local lock is the **frozen** full contract a session committed to render
    against — written when an override would conflict with a sealed key but the
    user wants to fork locally. The lock shape:

        scope: local
        derived_from: <slug>
        created: <iso8601>
        contract: { ...full resolved dict... }

    Returns the parsed dict or ``None``. The lock is authoritative — no further
    merging is applied — so rendering against it bypasses ``resolve()``.
    """
    lock_path = session_path / "contract.lock.yml"
    if not lock_path.exists():
        return None
    with lock_path.open() as f:
        data = yaml.safe_load(f) or {}
    if data.get("scope") != "local" or "contract" not in data:
        raise ValueError(
            f"{lock_path}: malformed local lock — needs `scope: local` and a "
            "`contract:` block carrying the full resolved dict."
        )
    return data


def resolve_for_session(
    slug: str, session_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve the contract the session will actually render against.

    Returns ``(resolved, built_against)``:

    - If ``<session>/contract.lock.yml`` exists, the frozen lock IS the
      contract (scope=local, derived_from=<lock.derived_from>).
    - Otherwise, the global ``resolve(slug)`` is the contract
      (scope=global, derived_from=null).

    ``built_against`` is the provenance stamp persisted to ``version.json`` so
    every rendered artifact carries one version of the truth.
    """
    lock = load_local_lock(session_path)
    if lock is not None:
        resolved = lock["contract"]
        built_against = {
            "id": resolved.get("slug", slug),
            "hash": contract_hash(resolved),
            "scope": "local",
            "derived_from": lock.get("derived_from", slug),
            "locked_at": lock.get("created"),
        }
        return resolved, built_against

    resolved = resolve(slug)
    built_against = {
        "id": slug,
        "hash": contract_hash(resolved),
        "scope": "global",
        "derived_from": None,
        "locked_at": None,
    }
    return resolved, built_against


def freeze_local_lock(
    session_path: Path, resolved: dict[str, Any], derived_from: str
) -> Path:
    """Write a ``<session>/contract.lock.yml`` capturing the current contract.

    Used when a session needs to diverge from the global contract on a
    non-sealed key but the user wants the divergence recorded and frozen
    rather than left as a per-render override. Returns the lock path.
    """
    lock_path = session_path / "contract.lock.yml"
    payload = {
        "scope": "local",
        "derived_from": derived_from,
        "created": datetime.now(timezone.utc).isoformat(),
        "contract": resolved,
    }
    with lock_path.open("w") as f:
        yaml.safe_dump(payload, f, sort_keys=False, default_flow_style=False)
    return lock_path


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
