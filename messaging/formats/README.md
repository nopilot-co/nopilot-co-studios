# Communication formats — library

A **communication format** is a *purpose* × *channel*, named `<purpose>-<channel>`
(e.g. `outreach-email`). The purpose centralises intent (style guide, execution
brief, ruleset); the channel layers on the medium's constraints. This is the
direct analog of the design studio's purpose × export `formats/`.

## Layout

```
formats/
  purposes/<purpose>.yml   # intent: style_guide, execution_brief, ruleset
  channels/<channel>.yml   # medium: render target + hard limits
  <purpose>-<channel>.yml  # composes the two + optional overrides
```

## Composition

Resolves by deep-merge: `purposes/<extends>.yml` ← `channels/<channel>.yml` ←
the slug file's `overrides`. Dicts merge recursively; scalars/lists replace.
Resolution + validation live in `../scripts/message/formats.py`, validated
against `../scripts/message/schemas/format.schema.json`.

```yaml
# outreach-email.yml
extends: outreach
channel: email
overrides:
  ruleset:
    max_body_words: 140
```

## Components

- **style_guide** — voice, length register, do/don't.
- **execution_brief** — `objective`, `audience`, `required_sections`.
- **ruleset** — enforceable constraints. Count-based ones (`max_subject_chars`,
  `max_body_words`, `max_body_chars`, `max_links`) and `forbidden` phrases are
  enforced deterministically by `message lint`; the rest (`required_sections`,
  `must_include_cta`, voice) are judged by the `message-qa` skill.

## Lifecycle

A session locks one format at `message new` (stored in `version.json`); `compose`
drafts to its brief; `message lint` enforces the count/forbidden rules; `render`
emits the channel target(s); `message-qa` critiques against the full contract.
One session = one format = one message. Same content for two channels = two
sessions (`announcement-email`, `announcement-linkedin`).

## CLI

```
message formats list
message formats show --format outreach-email
message formats validate --format outreach-email
```
