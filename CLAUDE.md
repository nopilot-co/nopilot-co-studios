# Studios

**Studios** is a collection of plugin-based *services* — each "studio" is a
self-contained service offering (e.g. the **design** studio). A studio is built
from two layers:

- **Skills** (markdown) — the LLM-driven judgment. These are the unit of work and
  the *contract* a studio exposes.
- **Deterministic glue** (a Python package + CLI) — file ops, subprocess
  orchestration (e.g. Quarto + Typst), versioning, validation, rasterization. No
  judgment lives here; CLI subcommands mirror the skills 1:1.

## Invocation modes

A studio can be driven three ways. The trigger, transport, and LLM host differ —
**the processing does not.** In every mode the work is performed by the *same
studio skills* over the *same deterministic CLI*, so outputs are identical
regardless of how the run was started.

1. **Local plugin (laptop).** Claude Code loads the studio as a plugin and runs
   its skills directly against the local filesystem root
   (`~/context/studios/<studio>/`). No network round-trip.
2. **Local CLI from a server installation.** The server dispatches a job to a
   local Claude installation; the same skills + CLI process it locally, and the
   outputs are sent back to the server as results. (Compute is local; the server
   is just the orchestrator/store.)
3. **Server-side / programmatic.** A UI trigger, automation, or schedule invokes
   the studio on the server using the server's configured LLM service. Same
   skills, run server-side.

**Consistency invariant:** the studio skills are the single source of processing
behavior. Modes differ only in *who triggers the run* and *which LLM host
executes the skills* — never in what the skills do. Keep all judgment in skills
and all mechanics in the deterministic package so this holds.

> **Status:** mode 1 (local plugin) is implemented today — the `studios`
> Producer plugin (formerly `creative-director`) and the `design-studio` plugin.
> Modes 2–3 are the intended server surfaces and are not built yet; the
> invariant above is what they must preserve (invoke the *same* skills, never
> reimplement the logic server-side).

## Orchestration — the Producer

`/studio <brief>` is the **single point of contact** across studios (until the
Principal front door ships — see `docs/operating-framework.md` §4). The
`producer` skill (`skills/producer/`, formerly `creative-director`) is a *thin
coordinator*: it reads the studio registry, plans the brief into jobs, routes
each to a studio's own orchestrator **by capability**, chains artifacts between
studios, and is the one place that delivers to external services (Gamma, Canva,
Slack, Gmail). It holds no domain judgment — the studios' skills do the work,
which is what keeps results identical across the three invocation modes.

- **Registry:** `studios.yml` (root) lists active studios + the external services
  the Producer may deliver through.
- **Per-studio contract:** each studio ships a `<studio>/studio.yaml` capability
  manifest (capabilities, entry points, inputs, outputs). A studio becomes
  routable the moment it's in `studios.yml` with a manifest — the Producer isn't
  edited to add one.
- **Outward actions** (publish/post/email) require explicit user confirmation;
  local rendering does not.

## Layout

Each studio lives under its own top-level directory and is independently usable.

### `design/` — Design Studio

The `design-studio` Claude Code plugin: Markdown → branded, versioned
**PDF / PPTX / HTML / RevealJS** from one `_brand.yml` (Posit brand.yml
standard) via **Quarto + Typst**. Full details in
[`design/CLAUDE.md`](design/CLAUDE.md).

- **Skills** (`design/skills/<name>/SKILL.md`) — the LLM judgment / contract:
  `brand-pick`, `brand-ingest`, `session-init`, `render`, `visual-qa`. The
  `/design-studio` command (`design/commands/`) orchestrates them; the plugin
  manifest is `design/.claude-plugin/plugin.json`.
- **Glue** (`design/scripts/studio/`, the `studio` CLI) — deterministic file
  ops, Quarto/Typst orchestration, versioning, validation, rasterization. Each
  skill drives its matching `studio` subcommand. No judgment here.
- **Formats** (`design/formats/`) — the canonical `<purpose>-<export>` contracts
  (e.g. `pitch-pdf`); each session locks one and renders/QAs against it. See
  `design/formats/README.md`.
- **Resources** (`design/resources/`) — canonical template assets that must
  represent 100% of design choices: `design-systems/`, `iconography/`,
  `brand-voice/`. Referenced by slug so designs stay normalised and
  interchangeable. See `design/resources/README.md`.
- **Data root** (`~/context/studios/design/<slug>/`, outside the repo) —
  `brand/` (with `_brand.yml`, validated against
  `scripts/studio/schemas/brand.schema.json`) and `outputs/<session>/`
  (`inputs/`, `outputs/`, `qa/`, `version.json`; the locked format is recorded
  in `version.json`).

It exposes itself to the Producer via `design/studio.yaml` (its capability
manifest) and its entry in `studios.yml`.

New studios follow the same shape: a plugin manifest + skills as the contract, a
deterministic CLI/package that mirrors them, a `studio.yaml` capability manifest
(plus a `studios.yml` entry so the Producer can route to it), and (optionally) a
data root under `~/context/studios/<studio>/`.

---

<!-- dgc-policy-v11 -->
# Dual-Graph Context Policy

This project uses a local dual-graph MCP server for efficient context retrieval.

## MANDATORY: Always follow this order

1. **Call `graph_continue` first** — before any file exploration, grep, or code reading.

2. **If `graph_continue` returns `needs_project=true`**: call `graph_scan` with the
   current project directory (`pwd`). Do NOT ask the user.

3. **If `graph_continue` returns `skip=true`**: project has fewer than 5 files.
   Do NOT do broad or recursive exploration. Read only specific files if their names
   are mentioned, or ask the user what to work on.

4. **Read `recommended_files`** using `graph_read` — **one call per file**.
   - `graph_read` accepts a single `file` parameter (string). Call it separately for each
     recommended file. Do NOT pass an array or batch multiple files into one call.
   - `recommended_files` may contain `file::symbol` entries (e.g. `src/auth.ts::handleLogin`).
     Pass them verbatim to `graph_read(file: "src/auth.ts::handleLogin")` — it reads only
     that symbol's lines, not the full file.
   - Example: if `recommended_files` is `["src/auth.ts::handleLogin", "src/db.ts"]`,
     call `graph_read(file: "src/auth.ts::handleLogin")` and `graph_read(file: "src/db.ts")`
     as two separate calls (they can be parallel).

5. **Check `confidence` and obey the caps strictly:**
   - `confidence=high` -> Stop. Do NOT grep or explore further.
   - `confidence=medium` -> If recommended files are insufficient, call `fallback_rg`
     at most `max_supplementary_greps` time(s) with specific terms, then `graph_read`
     at most `max_supplementary_files` additional file(s). Then stop.
   - `confidence=low` -> Call `fallback_rg` at most `max_supplementary_greps` time(s),
     then `graph_read` at most `max_supplementary_files` file(s). Then stop.

## Token Usage

A `token-counter` MCP is available for tracking live token usage.

- To check how many tokens a large file or text will cost **before** reading it:
  `count_tokens({text: "<content>"})`
- To log actual usage after a task completes (if the user asks):
  `log_usage({input_tokens: <est>, output_tokens: <est>, description: "<task>"})`
- To show the user their running session cost:
  `get_session_stats()`

Live dashboard URL is printed at startup next to "Token usage".

## Rules

- Do NOT use `rg`, `grep`, or bash file exploration before calling `graph_continue`.
- Do NOT do broad/recursive exploration at any confidence level.
- `max_supplementary_greps` and `max_supplementary_files` are hard caps - never exceed them.
- Do NOT dump full chat history.
- Do NOT call `graph_retrieve` more than once per turn.
- After edits, call `graph_register_edit` with the changed files. Use `file::symbol` notation (e.g. `src/auth.ts::handleLogin`) when the edit targets a specific function, class, or hook.

## Context Store

Whenever you make a decision, identify a task, note a next step, fact, or blocker during a conversation, call `graph_add_memory`.

**To add an entry:**
```
graph_add_memory(type="decision|task|next|fact|blocker", content="one sentence max 15 words", tags=["topic"], files=["relevant/file.ts"])
```

**Do NOT write context-store.json directly** — always use `graph_add_memory`. It applies pruning and keeps the store healthy.

**Rules:**
- Only log things worth remembering across sessions (not every minor detail)
- `content` must be under 15 words
- `files` lists the files this decision/task relates to (can be empty)
- Log immediately when the item arises — not at session end

## Session End

When the user signals they are done (e.g. "bye", "done", "wrap up", "end session"), proactively update `CONTEXT.md` in the project root with:
- **Current Task**: one sentence on what was being worked on
- **Key Decisions**: bullet list, max 3 items
- **Next Steps**: bullet list, max 3 items

Keep `CONTEXT.md` under 20 lines total. Do NOT summarize the full conversation — only what's needed to resume next session.
