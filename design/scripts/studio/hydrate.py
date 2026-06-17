"""Application-UI hydration (ADR-006, Slice C0 / #125).

The UDS UI archetypes are STRICT CONTRACTS in the canonical register
(``uds/archetypes.yml``, validated by ``studio.uds``). They are rendered as
greyscale-default HTML + ``uds/ui/base.css``, which references only
``var(--uds-*)`` custom properties. A **theme** defines those properties on
``:root``. This module is the deterministic hydration layer that sits *on top of*
the register (it does not redefine it):

- ``vars_greyscale`` — the brand-agnostic default (the contract, signals neutralised).
- ``vars_for_brand`` — HYDRATION: a brand's resolved ``tokens.yaml`` (via
  ``studio.uds.resolve_uds``) projected onto the same ``--uds-*`` surface.
- ``theme_css`` / ``write_themes`` — emit ``theme-greyscale.css`` + ``theme-<brand>.css``.
  Same archetype HTML + base.css; swap the theme, re-skin.
- ``render_document`` — wrap an authored body (the worked examples under
  ``uds/ui/examples/``) in a full HTML document: webfonts + base.css + a theme.
- ``validate`` — defer the contract to ``studio.uds.validate_uds`` and add the two
  checks the hydration layer owns: theme-contract **closure** (every ``--uds-*``
  used in base.css is emitted by a theme) and **selector coverage** (every
  ``.uds-<slug>`` styled in base.css is a real archetype).

No judgment here: the archetype markup is AUTHORED under ``uds/ui/examples/``; this
module only generates themes from token values and assembles documents. Token
values come solely from ``tokens.yaml`` (one source of truth); the only literals
below are the neutral default scale — the greyscale baseline IS the default.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from . import PLUGIN_ROOT
from . import formats as formats_mod   # ADR-005 sealing engine — reused, not reinvented
from . import uds as uds_mod

UI_ROOT = PLUGIN_ROOT / "uds" / "ui"
THEMES_DIR = UI_ROOT / "themes"
BASE_CSS = UI_ROOT / "base.css"
APP_JS = UI_ROOT / "app.js"
LOCK_FILE = THEMES_DIR / "uds-ui.lock.json"

_VAR_PREFIX = "--uds-"


# ----------------------------------------------------------------- the register
def canonical_archetypes() -> dict[str, Any]:
    """The canonical UI archetype register (uds/archetypes.yml), via studio.uds."""
    return uds_mod.archetypes()


# ----------------------------------------------------------------- the default scale
# The greyscale baseline IS the brand-agnostic default — the only literals here.
# Geometry (type scale, space, radius, border, shadow) is the UDS default; a brand's
# tokens.yaml may match or override it. Colour neutralises the two signals
# (crimson→graphite, yellow→neutral highlight) so the system is "quiet until branded".
_SYS_DISPLAY = "Georgia, 'Times New Roman', serif"
_SYS_BODY = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
_SYS_MONO = "ui-monospace, 'SFMono-Regular', 'Geist Mono', monospace"

_DEFAULT_STATIC: dict[str, str] = {
    "font-display": _SYS_DISPLAY, "font-body": _SYS_BODY, "font-mono": _SYS_MONO,
    "weight-regular": "400", "weight-medium": "500", "weight-semibold": "600", "weight-bold": "700",
    "size-eyebrow": "12px", "size-caption": "12.5px", "size-small": "14px", "size-body": "16px",
    "size-h4": "20px", "size-h3": "24px", "size-h2": "32px", "size-h1": "48px", "size-display": "64px",
    "leading-tight": "1.12", "leading-snug": "1.25", "leading-normal": "1.4", "leading-relaxed": "1.6",
    "tracking-eyebrow": "0.2em", "tracking-tight": "-0.01em", "tracking-normal": "0em",
    "space-0": "0px", "space-xs": "4px", "space-sm": "8px", "space-md": "12px", "space-lg": "16px",
    "space-xl": "24px", "space-2xl": "32px", "space-3xl": "48px", "space-4xl": "64px", "space-5xl": "96px",
    "radius-sm": "6px", "radius-md": "10px", "radius-lg": "14px", "radius-pill": "999px",
    "border-hair": "1px", "border-medium": "2px", "border-accent": "3px",
    "shadow-card": "0px 18px 40px -24px rgba(20,24,26,0.22)",
    # data-viz ramp — neutral by default (greyscale); a brand supplies its own order.
    "dataviz-1": "#353C40", "dataviz-2": "#6E747A", "dataviz-3": "#A6AAB0",
    "dataviz-4": "#CDCCD2", "dataviz-5": "#495258", "dataviz-6": "#272C2F",
}

_GREYSCALE_LIGHT: dict[str, str] = {
    "color-bg": "#F1F1F4", "color-surface": "#FFFFFF", "color-surface-sunk": "#F8F8FA",
    "color-border": "#E6E4E8", "color-line": "#CDCCD2",
    "color-text": "#1C2022", "color-text-muted": "#6E747A", "color-text-subtle": "#A6AAB0",
    "color-primary": "#353C40", "color-primary-hover": "#1C2022", "color-on-primary": "#FFFFFF",
    "color-active": "#E6E4E8", "color-on-active": "#1C2022", "color-active-wash": "#F1F1F4",
    "color-link": "#353C40", "color-eyebrow": "#6E747A",
}
_GREYSCALE_DARK: dict[str, str] = {
    "color-bg": "#14181A", "color-surface": "#16191C", "color-surface-sunk": "#101315",
    "color-border": "#2A2F33", "color-line": "#2D3236",
    "color-text": "#F1F5F9", "color-text-muted": "#9AA0A6", "color-text-subtle": "#6E747A",
    "color-primary": "#A6AAB0", "color-primary-hover": "#CDCCD2", "color-on-primary": "#14181A",
    "color-active": "#3A4045", "color-on-active": "#F1F5F9", "color-active-wash": "#23282B",
    "color-link": "#CDCCD2", "color-eyebrow": "#9AA0A6",
}


def vars_greyscale() -> dict[str, dict[str, str]]:
    """The greyscale default theme — the contract with no brand applied."""
    return {"static": dict(_DEFAULT_STATIC), "light": dict(_GREYSCALE_LIGHT), "dark": dict(_GREYSCALE_DARK)}


# ----------------------------------------------------------------- hydration
def _shadow_to_css(v: Any) -> str:
    if isinstance(v, dict):
        return (
            f"{v.get('offsetX', '0px')} {v.get('offsetY', '0px')} "
            f"{v.get('blur', '0px')} {v.get('spread', '0px')} {v.get('color', 'rgba(0,0,0,0.2)')}"
        )
    return str(v)


def vars_for_brand(brand: str) -> dict[str, dict[str, str]]:
    """HYDRATION — a brand's resolved ``tokens.yaml`` projected onto the --uds-*
    surface. Type/space/radius/border/shadow from the brand tokens (screen aspect
    class → web px); colour from the light/dark semantic sets."""
    u = uds_mod.resolve_uds(brand)

    static: dict[str, str] = {}
    fam = u["font"]["family"]
    for role in ("display", "body", "mono"):
        if role in fam:
            static[f"font-{role}"] = ", ".join(fam[role]) if isinstance(fam[role], list) else str(fam[role])
    for w, val in u["font"]["weight"].items():
        static[f"weight-{w}"] = str(val)
    for name, t in u["type"].items():            # screen canvas → px
        static[f"size-{name}"] = str(t["px"])
    for name, val in u["font"]["lineHeight"].items():
        static[f"leading-{name}"] = str(val)
    for name, val in u["font"]["letterSpacing"].items():
        static[f"tracking-{name}"] = str(val)
    for name, val in u["space"].items():
        static[f"space-{name}"] = str(val)
    for name, val in u["radius"].items():
        static[f"radius-{name}"] = str(val)
    for name, val in u["border"].items():
        static[f"border-{name}"] = str(val)
    for name, val in u["shadow"].items():
        static[f"shadow-{name}"] = _shadow_to_css(val)
    for i, hexv in enumerate(u.get("dataviz", []), start=1):   # the brand's categorical ramp (crimson leads)
        static[f"dataviz-{i}"] = str(hexv)

    light = {f"color-{k}": str(v) for k, v in u["semantic"]["light"].items()}
    dark = {f"color-{k}": str(v) for k, v in u["semantic"]["dark"].items()}
    return {"static": static, "light": light, "dark": dark}


def emitted_var_names(v: dict[str, dict[str, str]]) -> set[str]:
    names = set(v["static"]) | set(v["light"]) | set(v["dark"])
    return {f"{_VAR_PREFIX}{n}" for n in names}


def theme_css(v: dict[str, dict[str, str]], *, label: str = "") -> str:
    """Render a theme to CSS: static + light on :root; dark on [data-theme=dark]
    and via prefers-color-scheme (unless the user pinned light)."""
    def block(selector: str, items: dict[str, str], indent: str = "  ") -> str:
        lines = "\n".join(f"{indent}{_VAR_PREFIX}{k}: {val};" for k, val in items.items())
        return f"{selector} {{\n{lines}\n}}"

    head = f"/* UDS theme{(' — ' + label) if label else ''}. Generated by studio.hydrate — do not edit. */\n"
    root = block(":root", {**v["static"], **v["light"]})
    dark_explicit = block('[data-theme="dark"]', v["dark"])
    dark_auto = (
        "@media (prefers-color-scheme: dark) {\n  "
        + block(':root:not([data-theme="light"])', v["dark"]).replace("\n", "\n  ")
        + "\n}"
    )
    return f"{head}\n{root}\n\n{dark_explicit}\n\n{dark_auto}\n"


def write_themes(brand: str = "nopilot") -> list[Path]:
    """Write themes/theme-greyscale.css (default) + themes/theme-<brand>.css (hydrated)."""
    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    grey = THEMES_DIR / "theme-greyscale.css"
    grey.write_text(theme_css(vars_greyscale(), label="greyscale (default contract)"), encoding="utf-8")
    out.append(grey)
    p = THEMES_DIR / f"theme-{brand}.css"
    p.write_text(theme_css(vars_for_brand(brand), label=f"{brand} (hydrated)"), encoding="utf-8")
    out.append(p)
    out.append(write_lock(brand))   # stamp what the themes were built_against
    return out


# ----------------------------------------------------------------- base.css introspection
_VAR_RE = re.compile(r"var\(\s*(--uds-[a-z0-9-]+)")
_CLASS_RE = re.compile(r"\.uds-([a-z0-9-]+)")


def referenced_var_names(css: str | None = None) -> set[str]:
    """Every --uds-* custom property referenced in base.css (for the closure test)."""
    text = css if css is not None else (BASE_CSS.read_text(encoding="utf-8") if BASE_CSS.exists() else "")
    return set(_VAR_RE.findall(text))


def styled_archetypes(css: str | None = None) -> set[str]:
    """Canonical archetype slugs that have a ``.uds-<slug>`` rule in base.css.

    A class like ``.uds-card__title`` or ``.uds-card--featured`` counts towards
    ``card`` (longest canonical-slug prefix), so variant/part classes don't read
    as orphans."""
    text = css if css is not None else (BASE_CSS.read_text(encoding="utf-8") if BASE_CSS.exists() else "")
    slugs = set(canonical_archetypes())
    hit: set[str] = set()
    for raw in _CLASS_RE.findall(text):
        # match the longest canonical slug that the class name starts with
        cands = [s for s in slugs if raw == s or raw.startswith(s + "__") or raw.startswith(s + "--")]
        if cands:
            hit.add(max(cands, key=len))
    return hit


# ----------------------------------------------------------------- document assembly
_FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '  <link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,600;0,700;1,400'
    "&family=Newsreader:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Geist+Mono:wght@400;500&display=swap"
    '" rel="stylesheet">'
)


def render_document(
    body: str,
    *,
    title: str,
    theme: str = "nopilot",
    mode: str = "light",
    base_href: str = "../base.css",
    theme_href: str | None = None,
) -> str:
    """Wrap an authored archetype body in a full HTML document: webfonts + the
    chosen theme + base.css. The theme is a ``<link id="uds-theme">`` so hydration
    can be demonstrated by swapping its href (greyscale ↔ brand) with nothing else
    changed."""
    href = theme_href if theme_href is not None else f"themes/theme-{theme}.css"
    if not href.startswith(("../", "http", "/", "./")):
        href = f"../{href}"
    return f"""<!doctype html>
<html lang="en" data-theme="{mode}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  {_FONT_LINK}
  <link id="uds-theme" rel="stylesheet" href="{href}">
  <link rel="stylesheet" href="{base_href}">
</head>
<body class="uds-root">
{body}
</body>
</html>
"""


# Composition helpers that are not themselves archetypes — the frame that arranges
# the infrastructure-tier archetypes, plus shared atoms. Documented in base.css.
_SHELL_HELPERS = {
    "root", "shell", "stack", "cluster", "spacer",
    "field", "eyebrow", "muted", "badge", "avatar", "brand",
}


# ============================================================ GOVERNANCE (ADR-005/006)
# The register DECLARES seals (archetypes.yml `sealed:` + the `seal_rule`); this layer
# ENFORCES them for the screen realisation and reuses the canonical sealing engine
# (studio.formats) — it does not invent a parallel one. Three obligations:
#   1. seals are realised   — a built archetype must implement each sealed term.
#   2. brands skin, never alter — hydrate_archetype() merges through formats._merge_layers,
#      so a brand/session write to a sealed path hard-fails (SealedKeyConflict).
#   3. provenance — themes are stamped with what they were built_against (the ADR-005
#      lockfile model + tokens.provenance.json).

def _selector(slug: str) -> str:
    return f".uds-{slug}"


# Sealed-term → how the screen layer realises it. A predicate (slug, css, js)->bool;
# terms without one are realised by the archetype simply being built (structural seal).
_SEAL_CHECKS: dict[str, Any] = {
    "title-slot":         lambda s, c, j: f".uds-{s}__title" in c,
    "byline-slot":        lambda s, c, j: f".uds-{s}__byline" in c,
    "eyebrow-slot":       lambda s, c, j: f".uds-{s}__eyebrow" in c,
    "scrim":              lambda s, c, j: f".uds-{s}__scrim" in c,
    "focus-trap":         lambda s, c, j: "focusables" in j and "Tab" in j,
    "dismissal":          lambda s, c, j: "data-uds-close" in j and "Escape" in j,
    "sticky-behaviour":   lambda s, c, j: "position: sticky" in c,
    "collapse-behaviour": lambda s, c, j: "[data-collapsed" in c and "data-uds-toggle" in j,
    "position":           lambda s, c, j: "[data-side" in c,
    "focus-ring":         lambda s, c, j: ".uds-control:focus" in c and "--uds-color-active" in c,
    "error-state":        lambda s, c, j: ".uds-control[aria-invalid" in c,
    "colour-split":       lambda s, c, j: ".uds-button--primary" in c and "--uds-color-primary" in c and "--uds-color-active" in c,
    "state-set":          lambda s, c, j: ".uds-button:disabled" in c or ".uds-button.is-loading" in c,
    "accent-edge":        lambda s, c, j: f".uds-{s}" in c and "border-left" in c and "--uds-color-primary" in c,
    "hairline":           lambda s, c, j: f".uds-{s}" in c and "--uds-color-line" in c,
    "full-width":         lambda s, c, j: f".uds-{s}" in c and "width: 100%" in c,
    "header-row":         lambda s, c, j: ".uds-table thead th" in c,
    "rule-style":         lambda s, c, j: ".uds-table td" in c and "--uds-color-line" in c,
    "caption-credit":     lambda s, c, j: f".uds-{s}__caption" in c,
    "mono-sunk":          lambda s, c, j: f".uds-{s}" in c and "--uds-font-mono" in c and "--uds-color-surface-sunk" in c,
    "stroke-1.5px":       lambda s, c, j: ".uds-icon" in c and "stroke-width: 1.5" in c,
    "dataviz-ramp-order":  lambda s, c, j: "--uds-dataviz-1" in c,
    "anchor-mapping":     lambda s, c, j: f".uds-{s} a" in c,
    "figure-label":       lambda s, c, j: f".uds-{s}__value" in c and f".uds-{s}__label" in c,
    "links-to-detail":    lambda s, c, j: "a.uds-card" in c,
    "uniform-cells":      lambda s, c, j: f".uds-{s}" in c and "repeat(" in c,
    "attribution":        lambda s, c, j: f".uds-{s}__attribution" in c,
}


def seal_violations(css: str | None = None, js: str | None = None) -> list[str]:
    """A built archetype must realise each sealed term it declares — else the seal is
    decorative. Only enforced for BUILT archetypes (those styled in base.css)."""
    css = css if css is not None else (BASE_CSS.read_text(encoding="utf-8") if BASE_CSS.exists() else "")
    js = js if js is not None else (APP_JS.read_text(encoding="utf-8") if APP_JS.exists() else "")
    sprite = (UI_ROOT / "icons.svg").read_text(encoding="utf-8") if (UI_ROOT / "icons.svg").exists() else ""
    reg = canonical_archetypes()
    out: list[str] = []
    for slug in sorted(styled_archetypes(css)):
        for term in reg.get(slug, {}).get("sealed", []) or []:
            if term == "set-lucide":   # the locked icon set is realised by the vendored sprite
                if "lucide" not in sprite.lower():
                    out.append(f"archetype '{slug}': sealed term 'set-lucide' — UI icon sprite is not the vendored Lucide set (seal)")
                continue
            check = _SEAL_CHECKS.get(term)
            if check and not check(slug, css, js):
                out.append(f"archetype '{slug}': sealed term '{term}' is declared but not realised in the UI (seal)")
    return out


_VARNAME_RE = re.compile(
    r"^--uds-(color|font|weight|size|leading|tracking|space|radius|border|shadow|dataviz)-[a-z0-9-]+$"
)


def naming_violations(css: str | None = None) -> list[str]:
    """Naming conventions: tokens are --uds-<group>-<name>; archetype slugs are
    kebab-case (the register's convention)."""
    css = css if css is not None else (BASE_CSS.read_text(encoding="utf-8") if BASE_CSS.exists() else "")
    out: list[str] = []
    for v in sorted(referenced_var_names(css)):
        if not _VARNAME_RE.match(v):
            out.append(f"token var '{v}' is not --uds-<group>-<name> (naming)")
    for slug in canonical_archetypes():
        if slug != slug.lower() or "_" in slug or " " in slug:
            out.append(f"archetype slug '{slug}' is not kebab-case (naming)")
    return out


# ----------------------------------------------------------------- governed hydration
def hydrate_archetype(slug: str, brand: str = "nopilot", overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Hydrate one archetype through the ADR-005 sealing engine (studio.formats).

    Layers: the archetype CONTRACT (declares its seals) ← the BRAND theme (the open
    token surface) ← caller OVERRIDES. A brand may re-skin freely (open `theme`), but
    an override that writes a sealed path (``tier``, ``selector``, ``sealed_terms``)
    raises ``SealedKeyConflict`` — the same fail-closed rule as format contracts.
    Stamps ``built_against.contract_hash`` (the ADR-005 provenance model)."""
    reg = canonical_archetypes()
    if slug not in reg:
        raise KeyError(f"unknown archetype '{slug}'")
    a = reg[slug]
    sealed = list(a.get("sealed", []) or [])
    contract = {
        "tier": a["tier"],
        "selector": _selector(slug),
        "tokens": list(a.get("tokens", []) or []),
        "sealed_terms": {t: "sealed" for t in sealed},
        "seals": ["tier", "selector", "sealed_terms", *[f"sealed_terms.{t}" for t in sealed]],
    }
    v = vars_for_brand(brand)
    layers: list[tuple[str, dict[str, Any]]] = [
        ("contract", contract),
        ("brand", {"theme": {**v["static"], **v["light"]}}),   # the open surface
    ]
    if overrides:
        layers.append(("override", overrides))
    merged = formats_mod._merge_layers(layers)   # raises SealedKeyConflict on a sealed override
    merged["built_against"] = {"contract_hash": "sha256:" + formats_mod.contract_hash(merged)}
    return merged


# ----------------------------------------------------------------- provenance / lock
def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _tokens_provenance(brand: str) -> dict[str, Any]:
    p = uds_mod.brand_tokens_path(brand).parent / "tokens.provenance.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


_LUCIDE_VERSION = "0.469.0"


def _icon_provenance(brand: str) -> dict[str, Any]:
    """The locked icon set the UI realises — the brand `icon` lock + the vendored
    Lucide set (resources/iconography/lucide) + the built sprite."""
    try:
        icon = uds_mod.resolve_uds(brand).get("icon", {})
    except FileNotFoundError:
        icon = {}
    sprite = UI_ROOT / "icons.svg"
    return {
        "set": icon.get("set", "lucide"),
        "stroke": icon.get("stroke"),
        "version": _LUCIDE_VERSION,
        "license": "ISC",
        "vendored": "design/resources/iconography/lucide",
        "sprite": "design/uds/ui/icons.svg",
        "sprite_sha256": _sha256_file(sprite) if sprite.exists() else None,
    }


def provenance(brand: str = "nopilot") -> dict[str, Any]:
    """What the hydration was built_against — the ADR-005 lockfile model applied to the
    UI layer. Cites the register (hash) + the brand tokens (hash), the sealed token
    surface, and carries forward the brand-store `locks` (e.g. icon:lucide@1.5px)."""
    reg_file = uds_mod.UDS_ROOT / "archetypes.yml"
    tokens_file = uds_mod.brand_tokens_path(brand)
    tp = _tokens_provenance(brand)
    css = BASE_CSS.read_text(encoding="utf-8") if BASE_CSS.exists() else ""
    refs = referenced_var_names(css)
    roles = sorted(n[len("--uds-color-"):] for n in refs if n.startswith("--uds-color-"))
    dataviz = sorted(n[len("--uds-dataviz-"):] for n in refs if n.startswith("--uds-dataviz-"))
    tokens_hash = _sha256_file(tokens_file) if tokens_file.exists() else None
    return {
        "scope": "canonical",
        "derived_from": "design/uds/archetypes.yml",
        "built_against": {
            "register": {
                "file": "design/uds/archetypes.yml",
                "sha256": _sha256_file(reg_file),
                "archetypes": len(canonical_archetypes()),
            },
            "tokens": {
                "brand": brand,
                "source": str(tokens_file),
                "sha256": tokens_hash,
                "provenance_hash": tp.get("content_hash"),
                "matches_provenance": tokens_hash == tp.get("content_hash"),
            },
        },
        "token_surface": {"color": roles, "dataviz": dataviz},
        "icons": _icon_provenance(brand),
        "locks": tp.get("locks", []),
        "themes": ["theme-greyscale.css", f"theme-{brand}.css"],
        "generated_with": "studio.hydrate",
    }


def write_lock(brand: str = "nopilot") -> Path:
    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(json.dumps(provenance(brand), indent=2) + "\n", encoding="utf-8")
    return LOCK_FILE


# ----------------------------------------------------------------- validation
def validate() -> list[str]:
    """Fail-closed gate (ADR-005 precedent). The contract (studio.uds.validate_uds) +
    the governance the hydration layer owns: theme **closure**, selector **coverage**,
    **seal** realisation, and **naming**. Empty list == valid."""
    errors = list(uds_mod.validate_uds())

    if not BASE_CSS.exists():
        return errors  # nothing to close over yet

    css = BASE_CSS.read_text(encoding="utf-8")

    # closure — base.css references only tokens a theme emits
    emitted = emitted_var_names(vars_for_brand("nopilot")) & emitted_var_names(vars_greyscale())
    for ref in sorted(referenced_var_names(css) - emitted):
        errors.append(f"base.css references {ref} which no theme emits (closure)")

    # coverage — every .uds-<slug> is a canonical archetype or documented helper
    known = set(canonical_archetypes()) | _SHELL_HELPERS
    for raw in sorted(set(_CLASS_RE.findall(css))):
        if not any(raw == s or raw.startswith(s + "__") or raw.startswith(s + "--") for s in known):
            errors.append(f"base.css styles .uds-{raw} which is neither a canonical archetype nor a documented helper (coverage)")

    # governance — seals realised + naming conventions
    errors += seal_violations(css)
    errors += naming_violations(css)
    return errors


# ----------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="studio-hydrate", description="UDS application-UI hydration (Slice C0).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="fail-closed gate: register + closure + coverage + seals + naming")
    pt = sub.add_parser("themes", help="generate greyscale + brand theme CSS + the provenance lock")
    pt.add_argument("--brand", default="nopilot")
    sub.add_parser("lock", help="write themes/uds-ui.lock.json (built_against provenance)")
    ph = sub.add_parser("hydrate", help="print a governed hydrated archetype (honours seals)")
    ph.add_argument("slug")
    ph.add_argument("--brand", default="nopilot")
    args = ap.parse_args(argv)

    if args.cmd == "validate":
        errs = validate()
        if errs:
            print(f"INVALID ({len(errs)}):")
            for e in errs:
                print("  -", e)
            return 1
        n = len(canonical_archetypes())
        print(f"OK — {n} archetypes; closure + coverage + seals + naming all hold")
        return 0

    if args.cmd == "themes":
        for p in write_themes(args.brand):
            print("wrote", p)
        return 0

    if args.cmd == "lock":
        print("wrote", write_lock(args.brand))
        return 0

    if args.cmd == "hydrate":
        print(json.dumps(hydrate_archetype(args.slug, args.brand), indent=2))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
