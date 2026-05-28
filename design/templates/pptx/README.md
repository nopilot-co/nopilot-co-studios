# PPTX templates

This folder is intentionally light on content. Per-brand PPTX templates
("reference decks") live in each brand's folder:

```
~/context/studios/design/<brand-slug>/brand/reference.pptx
```

## Two ways the reference.pptx gets there

1. **Ingested from a real brand deck.** When `studio ingest` finds a `.pptx`
   among the source materials, it copies the first one as `reference.pptx`.
   The brand's existing master slides, fonts, colors, and placeholder layouts
   are preserved — Quarto will populate content into them on render.

2. **Synthesized from `_brand.yml`.** If no source deck exists, run:

   ```
   studio ingest synthesize-pptx --brand <slug>
   ```

   This renders a minimal 5-slide deck (title / section / content / two-col /
   closing) using `_brand.yml` tokens, and saves it as `reference.pptx`. It's
   functional but generic — replace it with a real brand deck when available.

## reference-skeleton.md

`reference-skeleton.md` (auto-created by `synthesize-pptx` when missing) is
the Markdown source used to render the synthetic deck. Edit it if you want
the synthesized deck to include more layouts.
