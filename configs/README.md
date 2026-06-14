# configs — global, cross-studio configuration

The **studios-level** configuration store. Everything here is **global and
brand-agnostic**: it applies across every studio (design, messaging, nitpicker,
…) and irrespective of any brand slug. Brand-specific identity stays in the
shared brand store (`~/context/studios/brand/<slug>/`); _baselines_ and _policy_
live here.

```
configs/
  default/   # baseline "bootstrap" values — the standard used when nothing
             # more specific (a brand override) is supplied
  tests/     # the nitpicker's extensible test templates (scored YAML)
```

## `default/` — baselines

Brand-agnostic defaults the studios fall back to. These are the floor every
asset is held to even before a brand's own guidance is layered on. A brand may
*overlay* a baseline (e.g. its own `tone-of-voice.md` in the brand store
specialises `default/tone-of-voice.yml`); absent a brand, the default **is** the
standard.

| File | What it bootstraps |
|------|--------------------|
| `tone-of-voice.yml` | Standardised tone-of-voice principles (attributes, do/don't, forbidden, mechanics) |
| `design-principles.yml` | Visual + creative baselines (contrast, hierarchy, type, whitespace, concept clarity) |
| `review-policy.yml` | Verdict bands + default weights the nitpicker aggregates scores against |

## `tests/` — nitpicker test templates

Each file is one **scored test** — a configurable, extensible scoring mechanism
the nitpicker runs an asset through. A test poses a question (e.g. *"will this
change the reader's mind?"*), defines a 1–5 scale with labelled anchors, lists
the criteria the score is judged against, and declares its weight + pass/warn
thresholds. Add a `<name>.yaml` to extend the battery — the nitpicker discovers
it automatically (`nit tests list`).

Shipped tests:

| Test | Dimension | Gate? | Question |
|---|---|---|---|
| `the-so-what-test` | `impact` | | Will this change the reader's mind? |
| `the-yawn-test` | `engagement` | | Is it interesting, readable, engaging? |
| `the-sniff-test` | `credibility` | ✓ | Does it sound credible, authoritative, believable? |
| `the-correctness-test` | `technical-quality` | ✓ | Are the facts, numbers, references, and technical claims accurate? |
| `the-completeness-test` | `technical-quality` | | Are all required parts present, and are caveats and edge cases addressed? |
| `the-readiness-test` | `delivery-quality` | | Could this ship to its audience as-is? |
| `the-actionability-test` | `delivery-quality` | | Can the reader act on this without coming back with structural questions? |
| `the-voice-fidelity-test` | `brand-integrity` | | Does the language sound like *this brand*, not generic brand voice? |
| `the-brand-recognition-test` | `brand-integrity` | ✓ | Would a reader who knows the brand recognise this as theirs? |

Phase 4 added the **technical-quality**, **delivery-quality**, and
**brand-integrity** dimensions (and 6 corresponding tests) so the nitpicker
reviews — and every studio that reuses the engine (audience reader-fit,
commercial check-commercials, etc.) — score on technical correctness,
delivery readiness, and brand fit on top of the original relevance /
readability / credibility battery. The new gates are `the-correctness-test`
(wrong numbers / fabricated claims) and `the-brand-recognition-test`
(off-brand assets).

Validated against `nitpicker/scripts/nit/schemas/test.schema.json`
(`nit tests validate --test <slug>`).

## Who reads this

- **nitpicker** consumes all of it (baselines to critique against, tests to
  score with, policy to aggregate a verdict).
- Other studios may read the same baselines so their own QA agrees with the
  nitpicker's standard (e.g. the design studio's visual-qa can reference
  `default/design-principles.yml`). The point of putting it here rather than in
  any one studio is that the standard is **shared and single-sourced**.
