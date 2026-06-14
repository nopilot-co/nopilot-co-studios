KICKOFF: Build out the nopilot-co-studios operating model

  You are taking over a multi-phase build for the nopilot-co-studios repo. The hard design work is done and documented; your job is execution against an agreed framework. Work autonomously, issue-first, one PR per phase.

  0. Onboard (do this first)

  git clone https://github.com/nopilot-co/nopilot-co-studios.git
  cd nopilot-co-studios
  gh auth status                       # need GitHub CLI authed for issues/PRs

  # Install the deterministic CLIs so cross-studio + end-to-end tests can run:
  ./design/install.sh                  # 'studio' CLI (creates design/.venv)
  NITPICKER_NO_CAPTURE=1 ./nitpicker/install.sh   # 'nit' CLI (fast, no browser)
  ./messaging/install.sh               # 'message' CLI
  pre-commit --version || pipx install pre-commit

  Then read, in this order:
  1. docs/operating-framework.md — the spec/canon ("the Bible"). Everything you build conforms to it.
  2. The top HANDOFF comment + the "Owner decisions" comment on PR #60 (gh pr view 60 --comments) — current state, locked naming, merge policy.
  3. The root CLAUDE.md and design/CLAUDE.md — repo conventions (judgment-in-skills, mechanics-in-CLIs, manifests, data roots).
  4. Study the audience/ studio as your canonical template for a new studio, and skills/planner/ + scripts/planner/ as the template for an orchestration skill. The merged arc to mirror: issues #39, #41, #46, #48, #51, #53.

  1. Locked decisions (do not relitigate)

  - Naming: Principal (front-of-house, the role the user talks to), Producer (orchestrator = today's creative-director, renamed), Proposition (the assembled work-winning deliverable).
  - Autonomy: supervised-autonomous — L0 gather / L1 draft autonomous; L2 decide / L3 deliver gated (Bible §6).
  - Systems of record: docket is canonical; GitHub Projects is the live projection (one-way + optional inbound; pluggable adapters) (Bible §8).

  2. Architecture rules (every phase obeys these)

  - A studio = skills (<studio>/skills/<name>/SKILL.md) + a deterministic CLI package (<studio>/scripts/<cli>/ with pyproject.toml, entry point) + <studio>/studio.yaml capability manifest + a studios.yml registry entry +
  .claude-plugin/plugin.json + install.sh + CLAUDE.md + a data root under ~/context/studios/<studio>/ + a standalone tests/test_<studio>.py. Mirror audience/ exactly.
  - Review-class roles reuse the nitpicker engine over the CLI boundary — do NOT re-implement scoring. Pattern: nit aggregate --scores --tests-from + audience/scripts/audience/nit_bridge.py. Rubrics use the nitpicker test-definition
  schema.
  - Cross-studio reuse is always over a CLI boundary (shutil.which + a .venv fallback), never a package import. Patterns: scripts/planner/docket_bridge.py, audience/scripts/audience/nit_bridge.py.
  - Classification rule (Bible §4): studio = durable artifact + data root + mechanics worth a CLI + routable capability; review-class = judges another artifact, reuses nitpicker; skill = one judgment step; orchestration skill =
  coordinates, owns no artifact.
  - Keep everything backward-compatible and registry-extensible — adding a capability must not require editing unrelated orchestrators.

  3. The program (each phase = its own issue → branch → PR)

  Phase 0 — Finalize the Bible. On the existing branch docs/54-operating-framework (continue PR #60, don't branch anew): find-replace Strategist→Principal and Engagement Response→Proposition across docs/operating-framework.md and
  README.md; keep Producer. ⚠️  Request owner approval before merge (canon).

  Phase 1 — Front-of-house (identity).
  - 1a. Rename the creative-director skill/role → Producer (domain-neutral orchestrator). Update skills/, studios.yml, commands/studio.md, plugin/marketplace manifests, references. ⚠️  Request owner approval before merge (identity).
  - 1b. Add the Principal root orchestration skill (front door): intake → objective clarification → client/audience/market mapping → value-based scoping → cast selection → hands a shaped brief to the Producer. Wire /studio to enter at
  the Principal. ⚠️  Request owner approval before merge (changes the user-facing entry).

  Phase 2 — Commercial studio (highest-leverage first new studio): capabilities check-commercials (beancounter — deterministic validation vs rate cards / margin floors / skill-set ratios, review-class, reuses nitpicker engine) and
  assess-commercial-value (commercial officer — client financial research, spend capacity, addressable market, value-based opportunity sizing). Shared data root (rate cards, client financials, pricing policy). Mergeable when green.

  Phase 3 — The rest of the cast (one studio per issue/PR, each mergeable when green): Delivery (plan-delivery — swimlanes, phasing, resourcing, contingency, RAID), Architecture (design-architecture — systems, data flows,
  integrations; reuse design for diagrams), Analytics (analyse-data), Growth/BD (lead-gen, market research/mapping), Context (ingest-context/map-context/extend-context, infrastructural).

  Phase 4 — QA + brand-guardian batteries in the nitpicker (new configs/tests/ batteries + dimensions for technical/delivery quality and brand integrity). Mergeable when green.

  Phase 5 — Engagement manifest: engagement.json (the engagement-level analogue of composition.json) with first-class questions / blockers / risks, jobs, decisions, checkpoints, and a deterministic status rollup command. Mergeable
  when green.

  Phase 6 — Autonomy ladder as an enforced contract: L0–L3 action classes + checkpoint surfacing (Bible §6). Mergeable when green.

  Phase 7 — Observability + SoR bridge: job ledger.jsonl, ADR-style decision records, uniform artifact provenance (Bible §7); and the docket → GitHub Projects bridge (adapter-based; engagement→Project, job→issue/card,
  question→question issue, blocker→blocked, gate→check; one-way default + optional inbound; conflict rule per Bible §8). Mergeable when green.

  Respect dependencies (Phase 5 before 7; 1 before 2 is ideal but 2 can proceed in parallel). Keep docs/operating-framework.md updated from Target → Today as each capability lands.

  4. Process & quality bar (every PR)

  - Issue-first: gh issue create for each phase before coding; reference it in commits (feat(<area>): … (#N)); one feature branch per issue (feat/<n>-… / docs/<n>-…) off main.
  - Tests: add a standalone tests/test_<thing>.py (mirror tests/test_audience.py / tests/test_planner.py); run via design/.venv/bin/python tests/test_<thing>.py. Cross-studio reuse paths should degrade/skip cleanly if a sibling CLI is
  absent.
  - Lint: pre-commit run --files <changed files> until clean (ruff/ruff-format/prettier/yamllint/shellcheck all pass).
  - Smoke-test the CLI end-to-end against a throwaway docket (use $STUDIOS_DOCKET_ROOT=$(mktemp -d) to redirect data roots) before opening the PR.
  - Honesty bar: docs must mark Today (built) vs Target (roadmap) accurately.
  - Commits end with a Co-Authored-By: trailer; PR bodies end with 🤖 Generated with [Claude Code](https://claude.com/claude-code).
  - Merge policy: additive/code phases (2–7) — merge when green + self-reviewed, then delete the branch and sync main. Identity/canon (Phase 0, 1a, 1b) — open the PR and stop for the owner's explicit approval; never auto-merge those.

  5. When to ask vs proceed

  Proceed autonomously on anything mechanical or additive, surfacing choices as issue/PR comments. Stop and ask the owner only for: the three identity/canon merges (Phase 0, 1a, 1b), anything outward-facing, or a genuine fork in a
  studio's domain model you can't resolve from the Bible + existing patterns. Default to the audience studio's shape when unsure.

  Start now: onboard (§0), then open the Phase 0 issue-continuation on PR #60 with the naming find-replace.
