# Messaging Studio

A studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md)). Same invariant:
its **skills are the single source of processing behavior** across all invocation
modes. Handles **brand communications** — emails, announcements, outreach,
nurture — written in a brand's voice and shaped to a channel. Full target design:
[`SPEC.md`](SPEC.md).

Packaged as the Claude Code plugin **`messaging-studio`** (`.claude-plugin/plugin.json`).
`./install.sh` creates `.venv` and installs the `message` CLI. Text-first and
mostly pure-Python; the only native dependency is **MJML** (`npm i -g mjml`),
needed solely to render HTML email (`.html`/`.eml`). `message doctor` reports it.

## Two layers (judgment vs. mechanics)

- **Skills** (`skills/<name>/SKILL.md`) — the writing/judgment, the contract:
  `message-intake` (pick + lock the format) → `compose` (write the message) →
  `message-qa` (qualitative critique); plus `sequence` (multi-step campaigns).
- **Deterministic glue** (`scripts/message/`, the `message` CLI) — format
  resolution, sessions/versioning, ruleset linting, rendering. No judgment.

## Formats (purpose × channel)

A format is `<purpose>-<channel>` (e.g. `outreach-email`) — the direct analog of
the design studio's purpose × export. Purposes (`outreach`, `followup`,
`announcement`, `nurture`) own intent; channels (`email`, `linkedin-post`,
`slack-post`, `sms`) own medium limits. Composed by deep-merge in `formats/`
(see [`formats/README.md`](formats/README.md)), validated against
`scripts/message/schemas/format.schema.json`. A session locks one slug.

## CLI

```
message formats list | show --format SLUG | validate --format SLUG
message new --brand SLUG --name NAME --format SLUG     # locks format, scaffolds inputs/message.md
message lint --session PATH                            # deterministic ruleset enforcement
message render --session PATH --bump patch|minor|major # emits channel target(s); re-lints
message status --session PATH [--set draft|approved|sent]
message sequence new --brand SLUG --name NAME --step NAME:FORMAT [--step ...]  # linked multi-step campaign
message sequence status --sequence PATH                # per-step status across the campaign
message doctor                                         # native-tool presence + per-format readiness
```

Entry point: `message = message.cli:main` (`pyproject.toml`). `lint` enforces the
count + forbidden-phrase rules; `compose`/`message-qa` skills handle the rest.

## Data root (outside the repo)

`CONTEXT_ROOT = ~/context/studios/messaging/<name>/`

```
inputs/message.md          # the composed message — front-matter (subject, preview, channel, status) + body
outputs/<slug>.v1.0.0.txt  # rendered channel targets (txt, md always; html/eml for email via MJML)
review/v<version>/findings.md
version.json               # { brand, session, format, channel, status, source_filename, created, current, history[] }
```

A **sequence** is a campaign folder holding `sequence.json` (brand, ordered
steps) plus one nested session per step (`step-01-<name>/`, `step-02-<name>/` …);
each step is a normal session with `sequence`/`step` added to its `version.json`.

## Brand & voice

Brand is a **studios-level** entity (SPEC §12.1, resolved), shared with the design
studio. Voice resolves in order: the shared store
`~/context/studios/brand/<brand>/tone-of-voice.md`, then the legacy design-owned
`~/context/studios/design/<brand>/brand/tone-of-voice.md`, then
`design/resources/brand-voice/brand-voice-default.md`. Forbidden phrases from the
voice feed `message lint`.

## Resources (canonical comms assets)

`resources/` holds the reusable, slug-referenced templates the skills compose
against — the messaging analog of the design studio's `resources/`. See
[`resources/README.md`](resources/README.md).

- `message-templates/<format>.md` — per-format skeletons (`compose`).
- `subject-lines/subject-lines.md` — email subject patterns.
- `ctas/ctas.md` — approved call-to-action phrasings.
- `sequences/<slug>.md` — multi-step cadence templates (`sequence`).

Voice is **not** duplicated here — it's the shared `../design/resources/brand-voice/`.

## Code map (`scripts/message/`)

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Click entry point `message <command>` |
| `formats.py` | Resolve/validate format slugs (purpose × channel merge) |
| `session.py` | Sessions + semver versioning + status; locks format into `version.json` |
| `sequence.py` | Multi-step campaigns: a manifest + one linked session per step |
| `lint.py` | Deterministic ruleset enforcement (subject/body/links/forbidden) |
| `render.py` | Emit channel target(s); txt/md pure-Python, html/eml compiled via MJML |
| `voice.py` | Resolve brand voice file + forbidden phrases (shared with design) |
| `deps.py` | Detect native render tools (MJML); backs `message doctor` + render skip-hints |
| `schemas/format.schema.json` | JSON Schema for a resolved format contract |

## Conventions

- One brand × one format per session, locked at `message new`. Same content on
  two channels = two sessions.
- Judgment in skills, mechanics in `scripts/message/`.
- The studio **composes**; it never sends. External delivery (Gmail/Slack) is the
  creative-director's job, with confirmation.
