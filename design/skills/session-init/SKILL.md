---
name: session-init
description: Create a versioned session folder under ~/context/studios/design/<brand-slug>/outputs/<session-folder>/, lock in a format slug, and copy the source Markdown into it. Initialises version.json. Use after brand-pick and before render.
---

# session-init

Creates the per-session workspace and **locks in the format** the session will
produce. A session is one brand × one format slug × one source document.

## Steps

1. **Lock in the format slug.** Every session targets exactly one format
   (`<purpose>-<export>`, e.g. `pitch-pdf`). List the options:
   ```bash
   studio formats list
   ```
   - If the user named a purpose and an export (e.g. "a pitch as a PDF"), use
     `pitch-pdf`. If they named only a purpose, ask which export, or default to
     `pdf`. If they named neither, ask.
   - If the user wants the **same content in multiple exports** (e.g. PDF *and*
     HTML), that is **multiple sessions** — one per format slug. Create them in
     turn; do not try to render two exports from one session.
   - Read the contract you are committing to so later steps can enforce it:
     ```bash
     studio formats show --format <slug>
     ```

2. Determine the session name:
   - If the user gave one (e.g. "q3-board-deck"), use it kebab-cased.
   - Otherwise generate `YYYY-MM-DD-<slug-from-md-title>`. If the Markdown has no H1, use `YYYY-MM-DD-untitled`.
   - Including the format in the name (e.g. `q3-board-deck-pitch-pdf`) keeps
     sibling sessions for the same content distinguishable.

3. Run:
   ```bash
   studio session init --brand <slug> --name <session-name> --format <format-slug> --source <path/to/source.md>
   ```
   This:
   - **Validates the format slug** against the contracts and refuses an invalid one.
   - Creates the session under the resolved root (see below), as
     `<root>/{inputs,outputs,qa}/`
   - Copies the source Markdown to `inputs/source.md`
   - Writes `version.json` with `{ "brand", "session", "format", "source_filename", "created", "current": "0.0.0", "history": [] }`
   - Prints the session path

4. Pass the session path to subsequent skills as `--session <path>`. They read
   the locked format from `version.json` — never re-pick it.

## Where the session lives (root resolution)

The session root resolves by this precedence (no env vars needed for the common
case):

1. **Explicit docket env** (`$STUDIOS_DOCKET_ROOT` + `$STUDIOS_DOCKET_SESSION`) —
   server modes / self-contained dockets.
2. **The slug's persistent working folder** — if set via
   `studio config set-folder --slug <slug> --path <dir>`, the session is created
   at `<dir>/<session-name>` and the brand resolves to `<dir>/brand/<slug>` (the
   canonical brand home inside the slug's own folder structure). Inspect with
   `studio config show [--slug <slug>]`.
3. **Legacy global** — `~/context/studios/design/<brand>/outputs/<session-name>/`.

Set a slug's working folder once and every later session/brand for that slug
honours it — no per-invocation env vars.

## Conventions

- One source Markdown **and one format slug** per session. Multiple exports of
  the same content = multiple sessions.
- The format is immutable once the session exists. To change format, create a
  new session.
- Session folders are immutable historical record. Never delete or rename them. If the user wants to start over, create a new session.
