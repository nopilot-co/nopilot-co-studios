# Tools

The **tool-bench** tier of `nopilot-co-studios`: a directory of small,
deterministic CLIs that any caller — a studio, a cron job, a shell user, an
agent in another repo — can discover and invoke from the same manifest contract.

A *tool* is **not** a studio. The distinction is load-bearing.

| | Tool | Studio |
|---|---|---|
| Owns judgment? | No — caller supplies it | Yes — in the skills |
| Owns a durable artefact / data root? | No | Yes |
| Has a capability manifest? | Yes — `tool.yaml` | Yes — `studio.yaml` |
| Has a CI invariant? | Yes — `scripts/check_tools_standalone.py` | No |
| Knows about studios? | **No — that's the invariant** | Yes (one peer) |

A tool's job is to **materialise structured input into structured output**
deterministically. The caller (studio, agent, human) supplies the judgment via
flags / env / JSON; the tool produces files / stdout / exit code at a
caller-specified location. Tools never read `studios.yml`, never import a
studio package, never assume a director or a docket exists.

## The dumb-tool invariant (CI-enforced)

`scripts/check_tools_standalone.py` runs on every PR and fails the build if any
`tools/*/scripts/*` does one of:

- imports a studio module (`studio`, `message`, `nit`, `audience`, `motion`, or
  the root `planner` package),
- references `studios.yml` / `creative-director` / `producer` / `planner` by
  string,
- hardcodes a studio/context path (e.g. `~/context/studios/…`),
- ships without a `tool.yaml`, or
- ships a `tool.yaml` with `depends_on_studio: true`.

The invariant exists so the tools tier cannot drift into a hidden studio
dependency. If you find yourself wanting a tool to "just read the planner's
manifest", that's a sign the work belongs in a studio, not in `tools/`.

## Discovery + invocation contract

Two YAML files, one shape mirror of the studios tier:

- **`tools.yml`** (at the repo root) — the index a caller loads first. One
  entry per tool: `slug`, `path`, `manifest`, `summary`, `cli`, `actions`,
  `standalone`, `status`. Same shape as `studios.yml`.
- **`tools/<slug>/tool.yaml`** — per-tool capability manifest. Same shape as
  `studio.yaml`, minus the orchestrator entrypoint, plus per-action `invoke`
  template, `inputs`, `outputs`, `exit_codes`, `idempotent`, `side_effects`.

An agent reads `tools.yml` → picks a tool/action → reads `tool.yaml` for the
`invoke` template and IO shape → runs the CLI → consumes files / stdout /
exit-code. This *is* the function-schema agents need — deterministic and
idempotent where marked.

## Adding a tool

1. Create `tools/<slug>/` with at least:
   - `tool.yaml` — capability manifest (see the next live tool for shape; for
     now this scaffold is the template).
   - `install.sh` — installs the CLI to `~/.local/bin/<cli>`.
   - `scripts/<cli>.py` — the deterministic CLI itself (no studio imports).
   - `skills/<name>/SKILL.md` (optional but recommended) — a thin skill that
     describes the action in natural language for LLM callers; **must contain
     no studio orchestration** — only "how to invoke this action".
2. Add an entry to `tools.yml` at the repo root.
3. Add a marketplace plugin entry to `.claude-plugin/marketplace.json` (so
   `claude plugin install <slug>@nopilot-co-studios` works for standalone use).
4. Run `pre-commit run --all-files` — the standalone-invariant check runs as
   part of pre-commit and CI.

## Status

This directory is **scaffolded** (Brief 02 P1) but holds no tools yet. The
seven tools listed in `context/briefs/02-consolidate.md` Appendix
(`notion-sources`, `source-enrich`, `source-summarise`, `theme-propose`,
`theme-cluster`, `theme-entity`, `youtube-transcript`) move in via P2 with
`git subtree add` to preserve history. See
[`docs/architecture/DECISIONS.md`](../docs/architecture/DECISIONS.md) ADR-004
for the full plan.
