# Messaging Studio

A studio for **brand communications** — emails, announcements, outreach, and
one-pager messaging, written in a brand's voice. Paired with `design/`, it shows
the Producer chaining studios.

- **Skills** (`skills/<name>/SKILL.md`): `message-intake` → `compose` →
  `message-qa`, plus `sequence` for multi-step campaigns.
- **`message` CLI** (`scripts/message/`): `formats`, `new`, `lint`, `render`,
  `status` — deterministic glue. Install with `./install.sh`.
- **Capability manifest** — `studio.yaml` (how the Producer calls it).
- **Shares resources** — reuses the design studio's `resources/brand-voice/` so
  voice stays consistent across the deck and the words around it.

See [`CLAUDE.md`](CLAUDE.md) for the full service descriptor.

Registered in the root `studios.yml`, so `/studio` can route to it. Example
chain: *design* renders a pitch deck → *messaging* drafts the outreach email that
sends it.

**v1 is built** (formats, the `message` CLI with deterministic linting, the
compose/QA skills, brand-voice integration). See [`SPEC.md`](SPEC.md) for the full
design and the v2+ roadmap (sequences/campaigns, HTML email, message templates).

> Minimal by design — no Python glue yet, since its work is composition (judgment
> lives in skills). Add a `scripts/` package + CLI if it ever needs deterministic
> mechanics.
