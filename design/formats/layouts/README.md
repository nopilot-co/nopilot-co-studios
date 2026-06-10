# Layouts

A **layout** is *how* an asset is navigated — independent of *what* it says
(purpose), *which medium* carries it (export), and *whose brand* skins it
(brand). It is the third orthogonal tier in the format-contract architecture
(ADR-005).

```
purpose ← layout ← export ← brand ← session
```

A slug declares its layout in the `layout:` field (defaults to `linear` if
absent so existing slugs keep working). The resolver merges
`layouts/<layout>.yml` between the purpose and the export.

## Available layouts

| Slug      | Engine            | Use when |
|-----------|-------------------|----------|
| `linear`  | `linear-engine`   | Single-axis top-to-bottom narrative — articles, reports, decks, most documents. The default. |
| `frame`   | `frame-engine`    | Two-axis master-detail: vertical topics, horizontal detail per topic. Showcases, two-axis explorers. |

> Render engines are keyed off `layout` (#99). Until that lands, `linear` slugs
> route through the Quarto doc pipeline as before; `frame` slugs use the
> showcase-template path declared on the slug.

## Sealed keys

A layout may declare `seals:` — a list of dotted paths that **cannot be
overridden** by later layers (export, slug, session). Sealed terms are the
governance contract: changing them means editing the layout itself (a
reviewed, global change), not silently overriding them per-slug.

A session that needs to diverge from a sealed term must **fork the layout**:
either a local-frozen contract (`<docket>/contract.lock.yml`, `scope: local`)
or a reviewed global new layout (PR). The provenance stamp in `version.json`
records which contract was actually built against.
