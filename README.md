# Studios

A Claude Code plugin marketplace for branded creative work — one brief, routed
across studios.

> **Operating model:** how the studio wins and delivers work — its vision, roles,
> method, autonomy, observability, and systems of record — is the canon in
> [`docs/operating-framework.md`](docs/operating-framework.md) (the "Bible").

| Plugin | What it does |
|---|---|
| **studios** | Principal (front-of-house) + Producer (orchestrator, was creative-director). `/studio <brief>` enters at the Principal — who shapes the engagement (objective, audience, scope, cast) and gets L2 sign-off — then hands a focused brief to the Producer, who routes each job to a studio, chains artifacts, and delivers to external services (Gamma, Canva, Slack, Gmail) on L3 authorisation. |
| **design-studio** | Markdown → branded **PDF / PPTX / HTML / RevealJS** via **Quarto + Typst**, driven by one `_brand.yml` (Posit brand.yml standard). Versioned outputs + visual QA. |
| **messaging-studio** | Brand communications — **email, outreach, announcements, multi-step sequences** — composed in a brand's voice. **HTML email via MJML.** |
| **nitpicker-studio** | Rigorous asset review — **visual/format QA, brief fulfilment, audience/ICP fit, standardised tone-of-voice**, plus a configurable scored test battery (so-what / yawn / sniff) — returning a weighted verdict. Reviews; never edits. |

## Install

```bash
# 1. Register the marketplace
claude plugin marketplace add github:nopilot-co/nopilot-co-studios

# 2. Install the plugins (skills + slash commands)
claude plugin install studios@nopilot-co-studios
claude plugin install design-studio@nopilot-co-studios
claude plugin install messaging-studio@nopilot-co-studios
claude plugin install nitpicker-studio@nopilot-co-studios

# 3. Install the deterministic CLIs (the skills call into these)
git clone https://github.com/nopilot-co/nopilot-co-studios.git
cd nopilot-co-studios
./design/install.sh        # 'studio'  CLI (Quarto/Typst)
./messaging/install.sh     # 'message' CLI (MJML optional)
./nitpicker/install.sh     # 'nit'     CLI (review/scoring)
```

`./install.sh` at the repo root runs steps 1 + 2 in one go and reports which
native dependencies are present. Re-run it any time.

## Quickstart

### Cross-studio (Principal + Producer)

```
/studio <your brief>
```

Enters at the **Principal**, the front-of-house skill: it shapes the
opportunity into an engagement (objective, audience, value-based scope, cast),
confirms scope with you (L2), and hands a focused brief to the **Producer**.
The Producer reads `studios.yml`, plans the brief into jobs, dispatches each
to a studio by capability, then asks before publishing to any external
service (L3 — the Principal carries it back). See
[`docs/operating-framework.md`](docs/operating-framework.md) §4 for the role
split.

### Design studio

```bash
# pick / build / lock a brand
studio brand list
studio ingest --brand acme --sources brand-guidelines.pdf logo.svg

# lock a format and render
studio session init --brand acme --name pitch-q3 \
  --format pitch-pdf --source pitch.md
studio render --session ~/context/studios/design/acme/outputs/pitch-q3
studio qa capture --session ~/context/studios/design/acme/outputs/pitch-q3
```

Slash entry: `/design-studio <path/to/source.md>`. Full docs: [`design/CLAUDE.md`](design/CLAUDE.md).

### Messaging studio

```bash
# one message
message formats list
message new --brand acme --name outreach-q3 --format outreach-email
$EDITOR ~/context/studios/messaging/outreach-q3/inputs/message.md
message lint   --session ~/context/studios/messaging/outreach-q3
message render --session ~/context/studios/messaging/outreach-q3

# multi-step campaign
message sequence new --brand acme --name fall-campaign \
  --step cold:outreach-email \
  --step value:followup-email \
  --step breakup:followup-email
message sequence status --sequence ~/context/studios/messaging/fall-campaign
```

Slash entry: `/messaging-studio`. Full docs: [`messaging/CLAUDE.md`](messaging/CLAUDE.md)
and [`messaging/SPEC.md`](messaging/SPEC.md).

## Data layout

Each studio writes outputs **outside** this repo, so the repo stays content-free
and brand work lives with you. Brand is a studios-level entity, shared by design
and messaging:

```
~/context/studios/
  brand/<slug>/                       # shared brand store
    _brand.yml                        #   (Posit brand.yml standard)
    tone-of-voice.md, style-guide.md  #   voice (consumed by messaging too)
    assets/, reference.pptx, css/
  design/<slug>/outputs/<session>/    # design render sessions (versioned)
  messaging/<name>/                   # messaging sessions / sequences
```

Brands created before this layout (under `~/context/studios/design/<slug>/brand/`)
still work — both studios fall back to the legacy location transparently.

## Dependencies

Each plugin **declares** what it needs and **detects** what's missing — render
and QA fail at the point of use with the exact install command. Run the
doctors to see status:

```
studio doctor      # Quarto, Typst, LibreOffice
message doctor     # MJML
```

| Tool | Used by | Install | Required? |
|---|---|---|---|
| Quarto | design-studio | `brew install --cask quarto` | yes (to render anything) |
| Typst | design-studio | bundled with Quarto, or `brew install typst` | yes (PDF engine) |
| LibreOffice | design-studio | `brew install --cask libreoffice` | optional (PPTX→PDF for QA) |
| MJML | messaging-studio | `npm install -g mjml` | optional (HTML email only) |
| Python ≥ 3.10 | both | `brew install python@3.12` | yes |

Set `MESSAGING_INSTALL_MJML=1 ./messaging/install.sh` to auto-install MJML.

## Tools tier

Alongside the studios, this repo hosts a **tool-bench** — a peer tier of small,
dumb, deterministic CLIs that any caller (a studio, an agent, a cron job, a
shell user) can discover and invoke from the same manifest contract. Tools are
**not** studios: they own no judgment, no data root, no artefacts; they
materialise structured input into structured output.

A CI invariant (`scripts/check_tools_standalone.py`) ensures `tools/*` never
imports a studio package, references `studios.yml`, or hardcodes a studio
path. See [`tools/README.md`](tools/README.md) for the contract +
[`docs/architecture/DECISIONS.md`](docs/architecture/DECISIONS.md) ADR-004 for
the rationale.

| Tool | CLI | What it does |
|---|---|---|
| [`notion-sources`](tools/notion-sources) | `notion-sources` | Extract a Notion database → per-source `.md` batch + manifest. Schema-agnostic, incremental. |
| [`source-enrich`](tools/source-enrich) | `source-enrich` | Enrich a sources batch in place — fetch each source, populate front matter, extract body (HTML/PDF/text) + assets, tidy bylines. |
| [`source-summarise`](tools/source-summarise) | `source-summarise` | Materialise caller-supplied summaries (`--summary-json`) into front matter + a "Core summary" section. |
| [`theme-propose`](tools/theme-propose) | `theme-propose` | Non-destructive theme-framework proposal; materialise a caller-supplied proposal; `--adopt` freezes into `theme-manifest.json`. |
| [`theme-cluster`](tools/theme-cluster) | `theme-cluster` | Materialise caller-supplied theme `--assignments` → `themes.json` + optional source-tag updates. |
| [`theme-entity`](tools/theme-entity) | `theme-entity` | Render per-theme dossiers from `themes.json` + caller-supplied `--spec`; author backlinks + a timeline per theme. |
| [`youtube-transcript`](tools/youtube-transcript) | `yt-transcript` | YouTube URL → transcript `.txt`/`.md`. Captions fast-path with Whisper fallback. Optional front matter / paragraphs / timestamps / chapters. |

Each tool is a **standalone installable plugin**:

```bash
# install one
claude plugin install notion-sources@nopilot-co-studios
# or get all tool CLIs on PATH at once
STUDIOS_INSTALL_TOOLS=1 ./install.sh
```

Tools are registered in [`tools.yml`](tools.yml) (the discovery index, shape
mirrors `studios.yml`) and each ships a `tool.yaml` capability manifest with
`actions[]`, `invoke` templates, IO shape, exit codes, idempotency, and
side-effects — the function-schema agents need.

## Repository structure

```
.
├── .claude-plugin/
│   ├── marketplace.json         # marketplace manifest (this repo)
│   └── plugin.json              # root orchestration plugin
├── skills/principal/            # front-of-house skill (/studio enters here)
├── skills/producer/             # orchestrator skill (was creative-director)
├── commands/studio.md           # the /studio slash command
├── studios.yml                  # registry of active studios + external services
├── tools.yml                    # tool-bench registry (ADR-004; scaffold)
├── tools/                       # dumb deterministic CLIs (tool-bench tier)
├── scripts/check_tools_standalone.py  # CI invariant: tools/ stays studio-free
├── install.sh                   # marketplace registration + dep report
├── design/                      # design-studio plugin
│   ├── .claude-plugin/plugin.json
│   ├── skills/                  # brand-pick, brand-ingest, session-init, render, visual-qa
│   ├── commands/design-studio.md
│   ├── scripts/studio/          # the deterministic 'studio' CLI
│   ├── formats/                 # <purpose>-<export> format contracts
│   ├── resources/               # design-systems, iconography, brand-voice
│   ├── templates/               # Quarto/Typst/CSS/PPTX templates
│   └── install.sh
└── messaging/                   # messaging-studio plugin
    ├── .claude-plugin/plugin.json
    ├── skills/                  # message-intake, compose, message-qa, sequence
    ├── scripts/message/         # the deterministic 'message' CLI
    ├── formats/                 # <purpose>-<channel> format contracts
    ├── resources/               # message-templates, subject-lines, ctas, sequences
    └── install.sh
```

## Invocation modes & status

Studios is designed to run in three modes — the **skills are the single source
of processing behavior** in all of them; only the trigger and the LLM host
change:

1. **Local plugin** (this repo, today) — Claude Code loads the plugins and runs
   their skills against the local filesystem.
2. **Local CLI from a server installation** *(not built)* — a server dispatches
   a job to a local Claude installation; the same skills + CLI process it
   locally and the outputs are returned to the server.
3. **Server-side / programmatic** *(not built)* — a UI trigger, automation, or
   schedule invokes the studio on the server using the server's configured LLM.

The invariant for modes 2–3 is: invoke the **same** skills, never reimplement
the logic server-side. See [`CLAUDE.md`](CLAUDE.md) for the studios model.

## Running in cowork (or any cloud sandbox)

cowork is a **hosted, account-bound environment** — there's no local `cowork`
CLI on your machine, and its sandbox can't read your laptop's filesystem. So you
don't point it at a local path; you bootstrap it **from inside cowork**, and it
pulls the repo from GitHub.

**1. Install the studios (gets skills + slash commands in):**

```bash
# inside cowork's environment
git clone https://github.com/nopilot-co/nopilot-co-studios.git
cd nopilot-co-studios
cowork plugin marketplace add ./        # cowork's CLI, inside cowork
# …then install the plugins (studios, design-studio, messaging-studio, nitpicker-studio)
```

**2. Provision the native render tools — this is the real gate.** `git clone`
gets the *plugin* in, but `studio render` still needs binaries that aren't
pip-installable, and a locked sandbox typically **blocks the download** (the
HTTP 403 you'll see fetching Quarto). Minimum set:

| Tool | Needed for | Notes |
|---|---|---|
| **Quarto** | rendering anything | **mandatory** — bundles Typst, so PDF needs only Quarto |
| Typst | PDF engine | bundled inside Quarto — no separate install |
| LibreOffice | **PPTX QA only** | optional; skip it for PDF / HTML / RevealJS (it's the big one) |

Getting Quarto past a sandbox proxy — pick whichever cowork's settings allow:

1. **Bake it into cowork's environment image** — pre-install Quarto so nothing
   downloads at runtime. Cleanest; this is the modes 2–3 "compute image ships
   the native tools" contract (`design/Brewfile` is that contract).
2. **Allowlist the download host** — the 403 is a proxy *policy*; permit
   `quarto.org` / the GitHub release CDN and the normal install works.
3. **Vendor it through an allowed channel** — GitHub git is reachable, so pull
   the Quarto release tarball from GitHub releases (or commit the binary into a
   clonable repo) and unpack it.

Until one of those is in place, cowork can run the **non-render** steps (planning,
brand-ingest drafting, content/message composition, nitpicker review of existing
assets) but **cannot produce a rendered asset** — by design, the studio fails at
point of use rather than emitting a non-conforming substitute.

## Plugin authoring notes

A couple of gotchas worth recording for anyone forking this or building a new
studio:

- `plugin.json` **must not** list `skills:` or `commands:` — Claude Code
  auto-discovers them from the `skills/` and `commands/` directories.
- In `.claude-plugin/marketplace.json`, the marketplace-root plugin's source
  must be `"./"` — a bare `"."` is rejected as an unsupported source type.
- Each studio ships its own `studio.yaml` capability manifest and is listed in
  the root `studios.yml`; the Producer isn't edited to add a studio.

## Licence

(Add a licence file before depending on this in anything you care about.)
