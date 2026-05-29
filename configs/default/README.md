# configs/default — baselines

Brand-agnostic "bootstrap" values. These are the standard an asset is held to
when nothing more specific is supplied, and the floor it is held to even when a
brand override exists. Each file is structured YAML so the nitpicker's
deterministic glue can load it and its skills can critique against it.

- `tone-of-voice.yml` — standardised ToV principles. A brand's own
  `tone-of-voice.md` (in `~/context/studios/brand/<slug>/`) overlays this; the
  nitpicker's `tone-of-voice` skill scores against the resolved result.
- `design-principles.yml` — visual + creative baselines used by the nitpicker's
  `visual-qa` skill (and available to the design studio's own visual-qa).
- `review-policy.yml` — global verdict bands and default weights the
  `nit score` aggregation uses to turn per-test/per-dimension scores into a
  single verdict.

Extend by editing these files or adding new baselines; keep them brand-agnostic.
Anything brand-specific belongs in the brand store, not here.
