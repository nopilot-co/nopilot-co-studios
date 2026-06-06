# Showcase template — `showcase-html`

The canonical template for the **`showcase-html`** format: an interactive,
two-axis *master-detail* showcase as a single self-contained web page. The
reader scrolls **down** through topics (each a whole overview) and **right**
into each topic's detail.

- Format contract: `../../formats/showcase-html.yml` (→ `purposes/showcase.yml` × `exports/html.yml`)
- Reference build that defined it: the 360 GTM proposition (`360-proposition-v5.html`)

## How the design studio reproduces it

One session = one format: `studio session init --format showcase-html`. The
design-studio skill then fills this template:

1. **Brand — uniform, from `_brand.yml`.** Overwrite the `BRAND TOKENS` block in
   `<head>`. Nothing brand-specific is hardcoded in the body; every colour and
   font resolves through these tokens, so a different brand re-skins the whole
   asset uniformly.

   | Template token | `_brand.yml` key |
   |---|---|
   | `ink` | `color.foreground` |
   | `paper` | `color.background` |
   | `teal` (primary accent / CTA) | `color.primary` |
   | `amber` (highlight) | `color.accent` |
   | `serif` (headings) | `typography.headings` |
   | `sans` (body) | `typography.base` |
   | `mono` (labels/figures) | `typography.monospace` |
   | `.dot360` brandmark | `logo.*` (swap when a brand supplies a logo) |

2. **Content — per engagement.** Replace the `CONTENT SLOT` (the `<section
   class="topic">` blocks). Each topic's *whole* overview is one
   `.panel.master`; the script auto-provisions the horizontal **stub** detail
   panels (`STUBS`, default 2) — fill or extend them with real detail. Keep one
   idea per panel; never fragment a topic across panels.

3. **Machinery — keep as-is.** The top nav, two-axis CSS, navigation mechanics
   (cue / chevrons / dots / arrow-keys / swipe), reveal-on-scroll, and the
   **viewer contract** are format machinery.

## Viewer contract (load-time commentary)

The asset is *dumb content + anchor hooks* — **no embedded auth, no comment
store**. A gated viewer (e.g. `<access-code>.nopilot.co`) loads it and injects
commentary against:

- `data-page-key="<topicId>:<panelIndex>"` on every commentable panel
- a `document` `np:pagechange` CustomEvent on the panel in view
- `window.NP_ASSET` — `{ docId, pages[], currentPageKey, setCommentCounts(map) }`

## Rules (enforced by `visual-qa` against the contract)

- `structure: master-detail` — vertical topics, horizontal detail
- `master_holds_whole_topic: true` — never spread one topic across panels
- `detail_pages_per_topic`: target 2, 1–5
- `must_expose_viewer_contract: true`; `no_embedded_auth`; `no_embedded_comment_store`
- `brand_tokens_from: _brand.yml`

## Dependencies

Self-contained; CDN at open time for Tailwind, the icon set, and web fonts.
**Hardening for production:** pin + add SRI (`integrity` / `crossorigin`) to the
CDN `<script>` tags before a public deploy.
