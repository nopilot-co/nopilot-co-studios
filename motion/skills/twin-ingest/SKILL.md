---
name: twin-ingest
description: Register a digital twin for the presenter archetype — a consenting person's likeness (portrait/clip) and voice reference — and record explicit consent before any avatar render. Required before producing a digital-twin presenter.
---

# twin-ingest

**Purpose.** Create a reusable **twin** (parallel to a brand, but for a person):
a portrait or short driving clip, a voice reference (for cloning), provider ids,
default framing, and — **mandatory** — a recorded **consent** entry in
`presenter.yaml`.

**Consent gate (load-bearing).** No avatar is rendered without a consent record.
The skill refuses to register or use a third-party twin without explicit, recorded
consent. Legitimate use = your own twin, or a consenting subject.

**Output.** A twin under `~/context/studios/twin/<slug>/`.

**Drives.** `motion twin ingest --twin <slug>`.

> Status: planned (lands in S3.5). See `motion/CLAUDE.md` build sequence.
