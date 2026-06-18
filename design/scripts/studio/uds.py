"""Universal Design System (UDS) — load + resolve (ADR-006, Slice 0).

The UDS is the nopilot brand-v3 system. Its token VALUES are the single source of
truth in a **W3C Design Tokens** file (``tokens.yaml``) in the brand store,
transformed by Style Dictionary v4 into per-format artifacts. This module is the
studio's adoption layer:

- ``load_uds`` / ``validate_uds`` — the brand-agnostic GRAMMAR (format set, the
  px→pt type rule, aspect classes, the contract register) authored in ``uds/``.
- ``resolve_tokens`` / ``resolve_uds`` — read the W3C ``tokens.yaml``, resolve its
  ``{a.b.c}`` references and light/dark semantic sets, and pair each web px size
  with its document pt (the cross-format type rule).

Render-inert in Slice 0: nothing in ``render.py`` / ``components.py`` reads this
yet. Style Dictionary becomes the artifact generator at the wiring slice; here we
only read the source of truth natively so the grammar is testable.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from . import FORMATS, PLUGIN_ROOT, SCHEMAS
from . import brand as brand_mod

UDS_ROOT = PLUGIN_ROOT / "uds"
_ASSETS_DIR = FORMATS / "assets"

# Which face each size token is set in (design.md): Newsreader carries every
# heading + cover title; Inter the body; Geist Mono the instrument micro-text.
_SIZE_FACE = {
    "display": "display", "h1": "display", "h2": "display", "h3": "display",
    "h4": "display", "body": "body", "small": "body",
    "eyebrow": "mono", "caption": "mono",
}

_REF = re.compile(r"^\s*\{(.+)\}\s*$")


# ----------------------------------------------------------------- grammar (uds/)
def _read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_uds() -> dict[str, Any]:
    """Merge the grammar manifest (``uds.yml`` + ``aspect-classes.yml`` +
    ``archetypes.yml``) into one document. Token *values* are NOT here — they live
    in the brand-store ``tokens.yaml`` (one source of truth)."""
    doc = _read_yaml(UDS_ROOT / "uds.yml")
    doc.update(_read_yaml(UDS_ROOT / "aspect-classes.yml"))  # adds `aspect_classes`
    doc.update(_read_yaml(UDS_ROOT / "archetypes.yml"))  # adds `markdown_mapping`, `archetypes`
    return doc


def _schema() -> dict[str, Any]:
    return json.loads((SCHEMAS / "uds.schema.json").read_text())


def aspect_classes(uds: dict[str, Any] | None = None) -> dict[str, Any]:
    return (uds if uds is not None else load_uds()).get("aspect_classes", {})


def archetypes(uds: dict[str, Any] | None = None) -> dict[str, Any]:
    return (uds if uds is not None else load_uds()).get("archetypes", {})


def validate_uds(uds: dict[str, Any] | None = None) -> list[str]:
    """Schema + cross-reference errors. Empty list == valid.

    Beyond JSON-Schema this enforces the contracts the engines will rely on: the
    format set is internally consistent, the aspect classes partition the full
    format set, every archetype renders within the full set, Layer-C contracts are
    HTML-canonical, archetype→asset references resolve, and reflow keys are known
    aspect classes.
    """
    uds = uds if uds is not None else load_uds()
    errors: list[str] = []

    for e in sorted(Draft202012Validator(_schema()).iter_errors(uds), key=lambda e: list(e.path)):
        loc = "/".join(map(str, e.path))
        errors.append(f"{loc}: {e.message}" if loc else e.message)

    formats = uds.get("formats", {})
    full = set(formats.get("full", []))
    if not set(formats.get("critical", [])) <= full:
        errors.append("formats.critical is not a subset of formats.full")
    if formats.get("composition") and formats.get("composition") not in full:
        errors.append("formats.composition is not in formats.full")

    classes = set(uds.get("aspect_classes", {}))
    covered: set[str] = set()
    for c in uds.get("aspect_classes", {}).values():
        covered |= set(c.get("formats", []))
    if full and covered != full:
        errors.append(f"aspect_classes cover {sorted(covered)} but full set is {sorted(full)}")

    arch = uds.get("archetypes", {}) or {}
    names = set(arch)
    for name, a in arch.items():
        af = set(a.get("formats", []))
        if full and not af <= full:
            errors.append(f"archetype '{name}': formats {sorted(af - full)} not in the full set")
        # Infrastructure (the app scaffold) is HTML-canonical.
        if a.get("tier") == "infrastructure" and "html" not in af:
            errors.append(f"archetype '{name}': infrastructure tier must render in html")
        if unknown := (set(a.get("reflow", {})) - classes):
            errors.append(f"archetype '{name}': reflow references unknown aspect class {sorted(unknown)}")
        for ref_key in ("item", "links_to"):
            ref = a.get(ref_key)
            if ref and ref not in names:
                errors.append(f"archetype '{name}': {ref_key} '{ref}' is not a known archetype")
        asset = a.get("asset")
        if asset and not (_ASSETS_DIR / f"{asset}.yml").exists():
            errors.append(f"archetype '{name}': asset '{asset}' has no formats/assets/{asset}.yml")

    # The markdown spine must map every construct to a known archetype.
    for mm in uds.get("markdown_mapping", []):
        el = mm.get("element")
        if el and el not in names:
            errors.append(f"markdown_mapping '{mm.get('md')}': element '{el}' is not a known archetype")

    return errors


# ----------------------------------------------------------------- W3C tokens
def _flatten(doc: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten a W3C token tree to ``{dotted.path: $value}`` for every leaf token."""
    out: dict[str, Any] = {}
    for k, v in doc.items():
        if k.startswith("$"):
            continue
        if isinstance(v, dict) and "$value" in v:
            out[f"{prefix}{k}"] = v["$value"]
        elif isinstance(v, dict):
            out.update(_flatten(v, f"{prefix}{k}."))
    return out


def _resolve_path(path: str, raw: dict[str, Any], cache: dict[str, Any]) -> Any:
    if path in cache:
        return cache[path]
    cache[path] = None  # cycle guard
    v = raw.get(path)
    if isinstance(v, str) and (m := _REF.match(v)):
        v = _resolve_path(m.group(1), raw, cache)
    cache[path] = v
    return v


def resolve_tokens(doc: dict[str, Any]) -> dict[str, Any]:
    """Resolve a W3C token document into concrete, structured values.

    References (``{color.neutral.100}``) are dereferenced; the light/dark semantic
    sets are flattened to hex; composite values (shadow) pass through.
    """
    raw = _flatten(doc)
    cache: dict[str, Any] = {}
    res = {p: _resolve_path(p, raw, cache) for p in raw}

    def group(prefix: str) -> dict[str, Any]:
        n = len(prefix) + 1
        return {p[n:]: v for p, v in res.items() if p.startswith(prefix + ".")}

    dataviz = [res[f"color.dataviz.{i}"] for i in range(1, 7) if f"color.dataviz.{i}" in res]
    icon: dict[str, Any] = {}
    if any(p.startswith("icon.") for p in res):
        icon = {"set": res.get("icon.set"), "stroke": res.get("icon.stroke"), "size": group("icon.size")}
    return {
        "semantic": {"light": group("semantic.light"), "dark": group("semantic.dark")},
        "font": {
            "family": group("font.family"),
            "weight": group("font.weight"),
            "size": group("font.size"),
            "lineHeight": group("font.lineHeight"),
            "letterSpacing": group("font.letterSpacing"),
        },
        "space": group("space"),
        "radius": group("radius"),
        "border": group("border"),
        "shadow": group("shadow"),
        "dataviz": dataviz,
        "icon": icon,
    }


def brand_tokens_path(brand: str) -> Path:
    """Where a brand's W3C ``tokens.yaml`` lives (the graduated canonical home)."""
    return brand_mod.brand_root(brand) / "tokens.yaml"


def load_brand_tokens(brand: str) -> dict[str, Any]:
    path = brand_tokens_path(brand)
    if not path.exists():
        raise FileNotFoundError(
            f"UDS tokens not found for brand '{brand}': {path}. Graduate the brand's "
            f"W3C tokens.yaml into the brand store first."
        )
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _stack(family: Any) -> str:
    """A W3C fontFamily $value (list or string) → a CSS-style stack string."""
    return ", ".join(family) if isinstance(family, list) else str(family)


def _type_system(res: dict[str, Any], uds: dict[str, Any]) -> dict[str, Any]:
    """Pair each size token's web px with its document pt (the cross-format rule)
    and bind the face per design.md."""
    px = res["font"]["size"]
    pt_map = uds.get("type_px_to_pt", {})
    families = res["font"]["family"]
    out: dict[str, Any] = {}
    for name, px_val in px.items():
        face = _SIZE_FACE.get(name, "body")
        out[name] = {
            "px": px_val,
            "pt": pt_map.get(name),
            "family_role": face,
            "family": _stack(families.get(face)),
        }
    return out


def resolve_uds(brand: str) -> dict[str, Any]:
    """Concrete UDS for a brand: resolved W3C tokens + the cross-format type system
    + the format set. The studio's typography finally comes from the real tokens —
    no invented scale.
    """
    uds = load_uds()
    res = resolve_tokens(load_brand_tokens(brand))
    return {
        "brand": brand,
        "tokens_source": str(brand_tokens_path(brand)),
        "semantic": res["semantic"],
        "font": res["font"],
        "space": res["space"],
        "radius": res["radius"],
        "border": res["border"],
        "shadow": res["shadow"],
        "dataviz": res["dataviz"],
        "icon": res["icon"],
        "type": _type_system(res, uds),
        "formats": uds.get("formats", {}),
        "aspect_classes": uds.get("aspect_classes", {}),
    }


# ----------------------------------------------------------------- render contract
def _num(v: Any) -> float:
    """'40pt' / '16px' / 40 → 40.0."""
    m = re.match(r"\s*([0-9.]+)", str(v)) if v is not None else None
    return float(m.group(1)) if m else 0.0


def render_role(role: str, brand: str, aspect_class: str = "slide", *,
                uds: dict[str, Any] | None = None, resolved: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve a house-style render role (``render_roles``) for a brand × aspect class
    into a concrete text style: ``{family, size, unit, weight, transform, align, colour}``.

    This is the format-specific render *setting*, sourced entirely from the UDS — the
    role's size token (resolved px/pt) scaled by the aspect class's ``type_scale``, its
    ``weight``/``colour`` from the brand's ``tokens.yaml``. ``weight`` is ``None`` when the
    brand omits that weight token (the serialiser then applies its bold default). Change
    a token, ``type_px_to_pt``, or a class ``type_scale`` and every serialiser follows.
    """
    uds = uds if uds is not None else load_uds()
    r = resolved if resolved is not None else resolve_uds(brand)
    spec = (uds.get("render_roles", {}) or {}).get(role, {})
    t = r["type"].get(spec.get("type", "body"), {})
    cls = uds.get("aspect_classes", {}).get(aspect_class, {})
    unit = cls.get("unit", "pt")
    size = _num(t.get("px")) if unit == "px" else round(_num(t.get("pt")) * cls.get("type_scale", 1.0), 1)
    wt = spec.get("weight")
    return {
        "family": t.get("family") or _stack(r["font"]["family"].get(t.get("family_role", "body"))),
        "size": size, "unit": unit,
        "weight": r["font"]["weight"].get(wt) if wt else None,
        "transform": spec.get("transform"),
        "align": spec.get("align", "left"),
        "colour": r["semantic"]["light"].get(spec.get("colour", "text"), "#1C2022"),
    }


def render_contract(brand: str, aspect_class: str = "slide") -> dict[str, dict[str, Any]]:
    """Every render role resolved for a brand × aspect class — the serialiser's table."""
    uds = load_uds()
    r = resolve_uds(brand)
    return {role: render_role(role, brand, aspect_class, uds=uds, resolved=r)
            for role in (uds.get("render_roles", {}) or {})}
