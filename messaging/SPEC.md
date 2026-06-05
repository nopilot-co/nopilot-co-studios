# Messaging Studio — Specification

> **Status:** v1 and most of v2 are **built** — purpose×channel formats, the four
> skills (`message-intake`, `compose`, `message-qa`, `sequence`), the `message`
> CLI (`formats`/`new`/`lint`/`render`/`status`/`sequence`/`doctor`), versioned
> sessions, MJML HTML email, sequence glue, and the `resources/` libraries. Brand
> has been elevated to a studios-level store (§12.1). Remaining: v3 (A/B variants,
> analytics). The `(proposed)`/`(exists)` markers below are kept for provenance;
> see §13 for the authoritative phasing.

## 1. Purpose & scope

The messaging studio composes **brand communications** — the words that carry a
brand to people: outreach, follow-ups, announcements, nurture, newsletters,
internal comms. It writes in the brand's voice and shapes each message to its
channel.

- **In scope:** composition, channel-fit, voice adherence, multi-step sequences,
  and deterministic linting against channel rules.
- **Out of scope:** *sending* (the Producer delivers via the Gmail/Slack MCP,
  with confirmation); *visual design* (design studio); *contact/CRM data*.
- **Relationship to design:** a parallel studio. Design makes the artifact;
  messaging makes the words around it. They chain through the Producer and
  **share one brand voice**.

The studios invariant holds: messaging's **skills are the single source of
processing behavior**, identical across all three invocation modes.

## 2. Core model — communication formats (purpose × channel)

Mirror the design studio's `formats` exactly, so comms are **normalised,
interchangeable, extensible, consistent**. A communication format is a *purpose*
crossed with a *channel*, named `<purpose>-<channel>`.

```
messaging/formats/                         (proposed)
  purposes/<purpose>.yml   # intent: objective, audience, required parts, voice emphasis, ruleset
  channels/<channel>.yml   # medium: render target + hard limits (subject, char budget, links, CTAs)
  <purpose>-<channel>.yml  # composes the two + overrides   (same deep-merge as design)
```

| Format slug | Purpose | Channel |
|-------------|---------|---------|
| `outreach-email` | cold outreach | email |
| `followup-email` | follow-up in a sequence | email |
| `announcement-email` | launch / news | email |
| `announcement-linkedin` | launch / news | linkedin-post |
| `nurture-email` | educate / warm | email |
| `newsletter-email` | recurring digest | email |

Each resolved format carries the same three components as a design format:

- **style_guide** — voice emphasis, length register, structure.
- **execution_brief** — `objective`, `audience`, `required_sections`
  (e.g. `subject`, `hook`, `body`, `cta`).
- **ruleset** — enforceable constraints: `subject_required`, `max_subject_chars`,
  `max_body_words`, `max_links`, `one_cta`, `forbidden` (pulled from the brand
  voice's forbidden list).

## 3. Channels (the export analog)

Each channel declares its medium constraints and render target — the messaging
counterpart of `exports/`:

| Channel | Render target | Key limits |
|---------|---------------|-----------|
| `email` | plain + HTML (`.eml`/`.html`/`.txt`) | subject ≤ ~60 chars, preview text, body budget, ≤2 links |
| `linkedin-post` | markdown/text | ~3000 char cap, no subject, hashtags |
| `linkedin-dm` | text | short, no links in first touch |
| `slack-post` | mrkdwn | concise, thread-friendly |
| `sms` | text | 160-char segments, one link |
| `push` / `in-app` | text | title + body char caps |

Channels may declare a `requires` block like design's exports, but messaging is
text-first — most need no native tools. **Delivery tools (Gmail/Slack MCP) belong
to the Producer, not to a channel.**

## 4. Skills (the pipeline)

| Skill | Role | Analog in design |
|-------|------|------------------|
| `message-intake` *(proposed)* | Pick `purpose`+`channel` (= format), lock it into the session | `session-init` (format lock) |
| `compose` *(proposed; folds in today's `outreach-copy`)* | Draft the message to the format's brief, in the brand voice | `render` |
| `message-qa` *(proposed)* | Critique vs ruleset + brand voice + deliverability; severity-ranked findings | `visual-qa` |
| `sequence` *(proposed)* | Compose an ordered multi-message sequence (cold → follow-up → break-up) | — (messaging-specific) |

Judgment lives here; mechanics live in the CLI (§5).

## 5. Deterministic glue — the `message` CLI *(exists)*

A small Python package + `message` CLI, parallel to design's `studio`, because
channel enforcement is deterministic (counts, lengths, link tallies). A format is
locked by slug (`<purpose>-<channel>`), not by separate `--purpose`/`--channel`.

```
message formats list | show --format SLUG | validate --format SLUG
message new --brand SLUG --name NAME --format SLUG
message lint --session PATH                 # enforce the channel ruleset (counts/limits/forbidden)
message render --session PATH [--bump …]     # emit the channel target(s) (.txt/.md, +.html/.eml via MJML)
message status --session PATH [--set draft|approved|sent]
message sequence new --brand SLUG --name NAME --step NAME:FORMAT [--step …]
message sequence status --sequence PATH
message doctor                              # native-tool presence (MJML) + per-format readiness
```

`version.json` analog: `{ brand, session, format, channel, status,
source_filename, created, current, history[] }` (sequence steps add `sequence`,
`step`, `step_name`). Same "judgment in skills, mechanics in glue" split as design.

## 6. Brand & voice integration

- Reuses the brand's voice from the shared studios-level brand store:
  `~/context/studios/brand/<brand>/tone-of-voice.md` + `style-guide.md`, then the
  legacy `~/context/studios/design/<brand>/brand/`, falling back to
  `design/resources/brand-voice/brand-voice-default.md`.
- The `forbidden`/`preferred` word lists feed the format ruleset, so voice
  violations are caught by `message lint`/`message-qa`.
- **Resolved (§12.1):** brand is now a *studios-level* entity stored at
  `~/context/studios/brand/<slug>/`, shared by design and messaging. Voice
  resolves from the shared store first, then the legacy design-owned location
  (`~/context/studios/design/<slug>/brand/`), then the brand-agnostic default.

## 7. Resources *(exists)*

Shares `design/resources/brand-voice/`. Adds messaging-specific, slug-referenced
resources under `resources/` (extensible, must cover 100% of comms choices):

- `message-templates/` — reusable skeletons per format.
- `subject-lines/` — patterns/library for email subjects.
- `ctas/` — approved call-to-action phrasings.
- `sequences/` — multi-step sequence templates.

## 8. Outputs & data model

```
~/context/studios/messaging/<name>/
  inputs/brief.md
  drafts/<slug>.v1.0.0.md        # front-matter (subject, preview, channel, status) + body
  review/v<version>/findings.md  # message-qa output
  version.json
```

Message artifact = YAML front-matter (`subject`, `preview`, `channel`, `to`/
`segment`, `status`) + markdown body. `message render` produces the channel
target from it.

## 9. Enforcement parity (the normalised/100% aim)

- **Deterministic (`message lint`):** subject length, body word/char budget, link
  count, single-CTA, forbidden words. Mirrors design's render-time ruleset check.
- **Judgment (`message-qa`):** voice adherence, clarity, CTA strength,
  deliverability (spam triggers), required sections present. Mirrors `visual-qa`.

## 10. Creative-director integration

- **Capabilities** (update `studio.yaml`): `compose-message` (purpose×channel),
  `sequence`, `announcement`.
- The director routes briefs and **chains** design → messaging (e.g. a rendered
  deck → an `outreach-email` that references it), then **delivers** externally
  (Gmail/Slack) with explicit confirmation. The studio stays local and pure.

## 11. Invocation modes

Identical guarantee to design: the messaging skills are the consistent processing
layer; local plugin, server-dispatched CLI, and server-side runs differ only in
trigger and LLM host, never in what the skills do.

## 12. Decisions (resolved)

1. **Brand as a shared entity** — ✅ **Resolved:** elevated to a studios-level
   store (`~/context/studios/brand/<slug>/`); design + messaging read one source,
   legacy design-owned brands still read transparently. (§6)
2. **Own `message` CLI vs a shared studios CLI** — ✅ its own, for symmetry with
   `studio`.
3. **Email HTML rendering** — ✅ **Resolved:** MJML (Node CLI). Declared as the
   email channel's `requires.render`, detected by `message doctor`; `render`
   skips `html`/`eml` with an install hint when MJML is absent. (§3, §5)
4. **Sending** — confirmed director-only; studio never sends.

## 13. Phasing

- **v0 (done):** `outreach-copy` skill + capability manifest.
- **v1 (done):** communication formats (purpose×channel) + `message-intake` /
  `compose` / `message-qa` skills + `message` CLI (`new`/`lint`/`render`/`status`)
  + versioned sessions.
- **v2 (done):** `sequence` skill + sequence CLI glue (linked sessions), MJML HTML
  email (`html`/`eml` + `doctor`), `resources/` libraries (`message-templates`,
  `subject-lines`, `ctas`, `sequences`).
- **v3 (next):** A/B variants and feedback/analytics hooks.
