# Studios

A Claude Code plugin marketplace for branded creative work — one brief, routed
across studios.

| Plugin | What it does |
|---|---|
| **studios** | Creative-director. `/studio <brief>` plans a brief, routes each job to a studio, chains artifacts between studios, and is the one place that delivers to external services (Gamma, Canva, Slack, Gmail). |
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

### Cross-studio (the creative-director)

```
/studio <your brief>
```

The director reads `studios.yml`, plans the brief into jobs, dispatches each to
a studio by capability, then asks before publishing to any external service.

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

## Repository structure

```
.
├── .claude-plugin/
│   ├── marketplace.json         # marketplace manifest (this repo)
│   └── plugin.json              # root creative-director plugin
├── skills/creative-director/    # the orchestrator skill
├── commands/studio.md           # the /studio slash command
├── studios.yml                  # registry of active studios + external services
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

## Plugin authoring notes

A couple of gotchas worth recording for anyone forking this or building a new
studio:

- `plugin.json` **must not** list `skills:` or `commands:` — Claude Code
  auto-discovers them from the `skills/` and `commands/` directories.
- In `.claude-plugin/marketplace.json`, the marketplace-root plugin's source
  must be `"./"` — a bare `"."` is rejected as an unsupported source type.
- Each studio ships its own `studio.yaml` capability manifest and is listed in
  the root `studios.yml`; the creative-director isn't edited to add a studio.

## Licence

(Add a licence file before depending on this in anything you care about.)
