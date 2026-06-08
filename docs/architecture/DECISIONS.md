# Architecture Decision Records

Chronological ADRs for the Studios monorepo. One entry per significant,
hard-to-reverse decision. Link back from the issue that prompted it.

> ADR-001 (server surfaces — modes 2–3: runner, transport, gatekeeper) is
> introduced by #23 on the `docs/23-server-modes-spec` branch; it merges into
> this file when that work lands.

---

## ADR-002 — Motion Studio rendering: Remotion + declarative hybrid; provider-agnostic avatar/TTS

- **Status:** accepted (2026-06-04)
- **Issue:** #42 (Motion Studio)
- **Context.** The motion studio must produce animated video, embeddable web
  motion, *and* photorealistic talking-head presenters — all on-brand,
  reproducible, and identical across the three invocation modes (local plugin,
  CLI-from-server, server-side). No single renderer covers cinematic video,
  lightweight embeds, and a digital twin at once, and the talking-head path needs
  capabilities that only exist as cloud services today.

- **Decision.**
  1. **Hybrid render engine.** **Remotion** (React/Node, via `npx`) for video and
     animated infographics; a **declarative SVG/CSS** path for self-contained
     animated HTML and **Lottie** (needs no node); **Playwright** capture →
     **ffmpeg** as a fallback and for GIF/keyframes.
  2. **Provider-agnostic adapter** for the digital-twin presenter: avatar
     (**D-ID** first) and TTS (**ElevenLabs** first, for a cloned twin voice),
     behind one interface, with an optional **local low-fidelity** avatar fallback.
  3. **`storyboard.json` is the single source of truth** — one spec, many exports.
     Brand colour/type tokens are **reused** from the design studio's token layer;
     motion tokens (easing/duration/transitions) come from a locked
     **motion-system**. Nothing is re-declared.
  4. **External renders are render-time, not delivery.** Avatar/TTS calls are part
     of `produce`, distinct from the Producer's delivery externals. Keys
     come from the **environment**, never the docket. Results are **cached by
     `hash(twin + script + provider + params)`** and stored as versioned session
     inputs, so re-composites are reproducible and free.
  5. **Consent gate.** No avatar render without a recorded consent in the twin's
     `presenter.yaml`; third-party twins require explicit recorded consent.

- **Consequences.**
  - Node/Remotion is the heaviest server-image dependency — isolated behind the
    declare/detect/degrade deps model (`motion doctor` / `Brewfile`); the
    declarative path is the no-Node fallback.
  - The presenter archetype depends on external services + credits + consent
    gating — the first studio capability that is not fully local. The invariant
    becomes "same skills + same provider adapter across modes."
  - Determinism of video requires pinned fps, embedded fonts, and seeded
    randomness.
  - Static "infographics" are produced as a storyboard's frame-0/poster, keeping
    one pipeline and avoiding overlap with the design studio.

- **Alternatives considered.**
  - *Single code engine (Remotion-only, or Manim-only).* Rejected: misses
    lightweight embeds/Lottie (Remotion) or general branded motion (Manim), and
    over-weights the server image.
  - *External-tool orchestration only (Gamma/Canva/cloud).* Rejected: breaks the
    local-render invariant and cedes brand-token control.
  - *Single avatar provider, hard-wired.* Rejected: cost/lock-in and no offline
    dev path; the adapter keeps providers swappable.

---

## ADR-004 — Consolidate `nopilot-co-utilities` → `nopilot-co-studios/tools` as a dumb tool-bench

- **Status:** proposed (2026-06-05) — pending owner sign-off on §8 decisions before P1
- **Issue:** #66; supersedes the separate `nopilot-co-utilities` repository
- **Brief:** `context/briefs/02-consolidate.md`

- **Context.** `nopilot-co-utilities` is seven deterministic CLIs that materialise
  caller-supplied data into structured artefacts: `notion-sources`,
  `source-enrich`, `source-summarise`, `theme-propose`, `theme-cluster`,
  `theme-entity`, `youtube-transcript`. They were originally written for an LLM
  caller to drive (the `--summary-json` / `--assignments` / `--spec`
  materialiser pattern), and were framed as "stubs" awaiting a higher-level
  studio. They are in fact *complete deterministic tools* — the caller supplies
  the judgment, the tools materialise it.

  Studios needs to orchestrate these tools (a `research-studio` is on the
  roadmap), and the tools themselves benefit from the studios repo's CI, tests
  (utilities has 0; studios has 14), pyproject/pre-commit, and marketplace
  surface. Keeping the two repositories separate forces duplication of all of
  the above and forces every studio that wants a tool to take a cross-repo
  dependency.

  But the *tools must not become studios.* They are dumb by design — no
  operational, functional, or contextual dependency on a studio, a director, or
  a docket. Conflating the two tiers is the trap.

- **Decision.**
  1. **Two tiers, one repo.** Move the seven utilities into a new top-level
     `tools/` directory inside `nopilot-co-studios`. `tools/` is a peer of the
     `studios/` directories, not a child of them.
  2. **Dumb-tool invariant (load-bearing, CI-enforced).** A tool has **no**
     studio dependency: no imports of a studio's package, no references to
     `studios.yml` / `creative-director` / `producer` / `planner`, no hardcoded
     studio/context paths (e.g. `~/context/studios/…`), no assumption a director
     exists. All input via flags / env / JSON; all output to a caller-specified
     location. A `scripts/check_tools_standalone.py` check in CI fails the build
     if any `tools/*/scripts/*` violates this, or if a `tool.yaml` is missing or
     sets `depends_on_studio: true`. Plus a smoke test: each tool installs and
     runs in a clean temp dir with **no studios on disk**.
  3. **Discovery + invocation contract (mirrors studios).** A new top-level
     `tools.yml` is the tool-bench discovery index — the same shape as
     `studios.yml`, with one entry per tool (`slug`, `path`, `manifest`,
     `summary`, `cli`, `actions`, `standalone`, `status`). Each tool ships a
     `tool.yaml` capability manifest — the same shape as `studio.yaml`, minus
     the orchestrator entrypoint, plus per-action `invoke` template, `inputs`,
     `outputs`, `exit_codes`, `idempotent`, `side_effects`. An agent reads
     `tools.yml` → picks a tool/action → reads `tool.yaml` for the `invoke`
     template and IO shape; runs the CLI; consumes files/stdout/exit-code. This
     *is* the function-schema agents need — deterministic, idempotent where
     marked. (Can later be generated into MCP/tool schemas; not in scope.)
  4. **Standalone-first preserved.** Each tool's `install.sh` keeps linking its
     CLI to `~/.local/bin` so direct shell use still works. Tools remain
     installable Claude plugins via the merged marketplace
     (`claude plugin install notion-sources@nopilot-co-studios`). The thin
     per-tool skill is kept for natural-language discoverability — but it
     describes *how to invoke the action*; it contains no studio orchestration.
  5. **Reversible, branch-bound migration in seven phases:** P0 (this ADR +
     tracking issue) → P1 (scaffold `tools/`, empty `tools.yml`, CI invariant
     check, marketplace/install wiring) → P2 (move the seven dirs with
     `git subtree add` to preserve history, then `git mv` into place; add each
     `tool.yaml`; drop the "STUB" framing) → P3 (marketplace + registry +
     install + README wiring) → P4 (adopt pyproject/pre-commit; add focused
     tests for the highest-risk tool logic — Notion id/url parsing,
     `tidy_author`, PDF/control-char handling, the materialisers,
     dedupe/append; migrate **ADR-001..003** from the utilities repo into this
     file; CI invariant + version consistency green) → P5 (verify each tool
     end-to-end in a studios-free temp dir; agent discover-and-invoke dry-run
     purely from `tools.yml`/`tool.yaml`) → P6 (cutover: open PR, merge;
     archive `nopilot-co-utilities` with a redirect; repoint installs). P7
     (the `research-studio` that orchestrates these tools) is a **separate
     effort** and explicitly out of scope.

- **Consequences.**
  - One repo, one CI, one marketplace, one test runner — closes the test-gap
    (0 → focused coverage of the bug-prone tool logic) and removes the cross-
    repo dependency for any studio that wants a tool.
  - Tools become trivially composable by an agent: it loads `tools.yml`, picks
    an action from `tool.yaml`, and runs the CLI. Discovery is no longer
    "tribal knowledge."
  - The dumb-tool invariant is now a *load-bearing rule* — a tool importing a
    studio module or hardcoding a studio path is a CI failure, not a stylistic
    nit. This is what prevents the tools tier from drifting into a hidden
    studio dependency.
  - The "STUB" framing is dropped: these are complete deterministic tools whose
    contract is "caller supplies intelligence (a JSON spec), tool materialises
    it." That contract is preserved as-is.
  - The `research-studio` becomes *just another caller* — it gets no special
    access path. If the manifest contract can't drive a tool, the tool is
    wrong, not the studio.
  - History preservation via `git subtree add` is one-way once merged — the
    fallback (copy + history note in the archived repo's README) is available
    if subtree is messy.

- **Decisions to confirm before P1** (raised in §8 of the brief).
  1. **History strategy:** `git subtree add` (heavier, full history under
     `tools/`) vs. copy + archive old repo for history (simpler). **Lean:
     subtree.**
  2. **Tool plugin names:** keep as-is (`notion-sources`, …) — no `-studio`
     suffix, since they're tools, not studios. **Recommended.**
  3. **Discovery file:** a separate `tools.yml` (clean tier separation,
     recommended) vs. a `tools:` section inside `studios.yml`. **Lean:
     separate file.**
  4. **Skill retention:** keep each tool's thin skill for natural-language
     discoverability — **recommended; stays studio-free.**

- **Alternatives considered.**
  - *Leave `nopilot-co-utilities` as a separate repo, depend on it via a
    submodule or PyPI release.* Rejected: cross-repo install friction, no
    shared CI/tests, duplicate marketplace, and every consumer studio takes a
    dependency on a moving target. We're choosing one repo for the same reason
    `studios.yml` already lives next to the studios it indexes.
  - *Promote the tools to studios (give each a `studio.yaml`, put each under
    `<tool>/`).* Rejected: a tool has no durable artefact, no data root, no
    routable capability beyond a single CLI action. Forcing studio shape on
    them invents structure they don't need and dilutes the studio classification
    in the Bible (§4).
  - *Embed each tool inside the `research-studio` that will use them.*
    Rejected: locks the tools to one consumer and breaks the standalone-CLI
    promise (cron jobs, ad-hoc shell use, other studios). The tool-bench tier
    exists *so that* the research-studio is not the only caller.
  - *Skip the `tool.yaml` manifest; expect agents to read the README.*
    Rejected: discovery becomes tribal knowledge, MCP/tool-schema generation
    needs a structured contract anyway, and the consistency with `studio.yaml`
    is the whole point — one mental model for both tiers.

---

## ADR-005 — Format contracts: purpose × layout × format × brand, with sealed keys and governed forks

- **Status:** accepted (2026-06-08)
- **Issue:** #98 (format-contract architecture, epic); spine #99–#101;
  gate #102; composer #103; ergonomics #104–#105
- **Supersedes:** the implicit `<purpose>-<export>` two-layer model in
  `design/scripts/studio/formats.py::resolve` (still valid as a special case:
  `layout: linear` is the default).

- **Context.** The studios exist to release a creator from the format
  conversation — they bring the message; brand execution, navigation structure,
  and header/footer usage should be **baked-in contracts that cannot be
  abrogated**. In practice this was not holding. Building the 360 GTM proposition
  (2026-06-06), the locked `showcase-html` format silently regressed from the
  agreed two-axis "frame" navigation to a single-axis scroll, sections were
  stubbed and passed off as a finished build, and the output differed run to run.
  Three root causes, all verified in code:
  1. **Layout was never a concept.** A slug resolves as `purposes/<purpose>.yml`
     ← `exports/<export>.yml` ← slug `overrides` — i.e. `purpose × format`. The
     navigation/structure governance lived *inside* one purpose
     (`purposes/showcase.yml`), so "showcase" meant "the frame thing" and no
     other purpose could reuse it and nothing stated the layout as a contract.
  2. **`_deep_merge` lets any later layer clobber any key** — there is no notion
     of a sealed/non-overridable governance term. Drift is *permitted by design*.
  3. **Nothing fails closed.** `check_output()` validates counts only; the render
     path never reads `engine`/`template`; a contract can say "frame" and the
     output be anything, with no error. The declared `engine: showcase-template`
     is dead — render routes everything to Quarto.

- **Decision.**
  1. **Four orthogonal layers, composed — content / structure / medium / skin.**
     - `purposes/<purpose>.yml` — **WHAT**: messaging intent, `required_sections`,
       narrative arc, tone brief, completeness definition. (Strip layout out.)
     - `layouts/<layout>.yml` — **HOW it is navigated** (new tier): navigation
       model, spine/detail structure, header/footer **slots + placement**, and the
       **structural invariants** a render must exhibit (`must_contain`). Declared
       once; reused by every purpose. Siblings: `linear`, `frame`, `carousel`, …
     - `exports/<export>.yml` — **WHICH medium** + which engine implements the
       layout for that medium (pdf/html/pptx/png/mp4/…).
     - brand (`_brand.yml`) — **SKIN**: fills the slots; never defines them.
     Resolve order: `defaults ← purpose ← layout ← export ← brand ← session`.
  2. **The slug is a thin, optional binding — not a fat spec.**
     `<purpose>-<layout>-<format>.yml` (e.g. `showcase-frame-html.yml`) references
     the three layers and declares only genuine deltas. A session may also lock a
     **triple directly** (`--purpose … --layout … --format …`) and resolve on the
     fly; a binding file is *curation* (pinned overrides / catalogue
     discoverability), written only when wanted. The matrix is sparse — invalid
     combinations (`frame × csv`) are rejected at lock time, never enumerated as
     files.
  3. **Sealed keys make governance unabrogable.** A layer may declare `seals:` —
     keys that no lower layer (export, slug, brand, session) may override.
     `_deep_merge` honours seals and **hard-fails** on a sealed-key conflict. To
     change a sealed term you must edit the *owning layer* — a global, reviewed
     act. Forking is allowed on the open surface; the contract terms are not.
  4. **Layout-keyed render engines + fail-closed validation.** Render engines are
     keyed off `layout` (`frame-engine`, `linear-engine`, `carousel-engine`),
     load the layout's `template`, and a post-render validator asserts the
     layout's `must_contain` (e.g. for `frame`: `.track`, `data-page-key`,
     `window.NP_ASSET`, `np:pagechange`). Missing structure → **non-zero exit**,
     not a soft QA note. The fidelity/completeness gate consumes the same
     `must_contain` + seals — one declaration, enforced at render *and* at the
     gate.
  5. **A deep-merge that changes the contract is a FORK, and a fork must declare
     itself.** Identity + provenance, on the lockfile model — the global spec is
     `package.json` (live, layered); a local resolved contract is
     `package-lock.json` (exact, frozen, committed, travels with the asset). On
     lock/render, compare `hash(resolve(slug))` with the effective contract; if
     it materially diverges, **halt and force a conscious L2 *contract-fork
     decision*** with three outcomes:
     - **sealed-key conflict → rejected** (edit the owning layer instead);
     - **open-key divergence, one-off → local fork**: materialise a
       **fully-resolved, frozen** `<docket>/contract.lock.yml`
       (`scope: local`, `derived_from: <slug>@<hash>`, `diverged_keys: […]`).
       Frozen, not an overlay — so a later change to the global spec cannot
       silently re-mutate the asset. `version.json` points the asset at it;
       render + validator key off it identically to a catalogue spec;
     - **open-key divergence, reusable → global fork**: write a new thin binding
       `formats/<newslug>.yml` and surface it as *"a new contract is being
       written into your production catalogue"* — committed via the normal
       PR/review path, because changing the catalogue changes production.
  6. **Provenance stamp on every output.** `version.json` records
     `built_against: {id, hash, scope, derived_from}` so any future thread knows
     exactly which contract is the truth, whether it is a fork, and its lineage.
     There is structurally one version of the truth per asset.

- **Consequences.**
  - `purposes/showcase.yml` splits into `purposes/showcase.yml` (intent) +
    `layouts/frame.yml` (master-detail nav, viewer contract, slots). Every
    existing slug gains `layout: linear` for back-compat — nothing breaks.
  - "Format" stops being a static catalogue and becomes a small
    provenance/versioning system: contracts get identity (name + hash + scope +
    lineage); assets cite the contract they were built against.
  - The system may deep-merge freely, but it may **never diverge silently** —
    every fork is named, scoped (local-frozen or global-new), recorded with
    lineage, and cited by the asset it produced. This is the mechanism that
    delivers the original aim: the creator owns the message; brand, navigation,
    and header/footer are baked-in and provably present or the build fails.

- **Alternatives considered.**
  - *Just lengthen the slug to `<purpose>-<layout>-<format>` (the original
    suggestion).* Adopted as the **handle**, rejected as the **fix** — the name
    alone changes nothing; the cause is the absence of a layout layer, sealed
    keys, and fail-closed validation. Naming is cosmetic; layering + sealing +
    enforcement is the contract.
  - *Forbid overrides entirely (contracts are immutable).* Rejected — legitimate
    one-off divergence is necessary; the requirement is that it be conscious,
    scoped, and recorded, not impossible.
  - *Store a local fork as a thin overlay on the global spec.* Rejected —
    reintroduces drift: a later global change silently re-mutates the asset. Local
    forks must be frozen, resolved snapshots with a lineage pointer.
  - *Treat header/footer as its own axis.* Rejected — it is a shared contract:
    layout owns slot presence/placement (sealed); brand owns fill/style.
