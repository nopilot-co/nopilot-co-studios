---
name: review-intake
description: Start a nitpicker review session — register the asset under review (a file or URL), the brief it must fulfil, the brand whose voice applies, and the target audience / ICP. Use before any critique skill. Creates the session and version.json via `nit new`.
---

# review-intake

Set up a review session. A session is **one target asset × one review**. The
nitpicker reviews; it does not edit — intake just gathers what the later skills
judge against.

## Steps

1. **Identify the target.** The asset under review — a rendered file
   (`.pdf` / `.pptx` / `.html` / image / `.md`) or a live **URL**. If it came
   from another studio (a deck from design, a message from messaging), use that
   artifact path.

2. **Gather the brief.** What was the asset *supposed* to do? If the user has a
   brief, point `--brief` at it. If not, draft a short one with them (objective,
   audience, must-haves) — `brief-fulfilment` is meaningless without it.

3. **Identify the audience / ICP.** Who is this for? Point `--icp` at a profile,
   or draft one (who they are, what they care about, their objections, the
   solution/offering they're being sold). `audience-fit` reads this.

4. **Note the brand** (optional). If the asset belongs to a brand, pass
   `--brand <slug>` so `tone-of-voice` can overlay the brand's voice on the
   default baseline.

5. **Create the session:**
   ```bash
   nit new --name <kebab-name> --target <path-or-url> \
     [--brief <path>] [--brand <slug>] [--icp <path>]
   ```
   This copies a file target into `inputs/target/` (or records the URL),
   scaffolds `inputs/brief.md` + `inputs/icp.md` (stubs if not supplied), and
   writes `version.json`.

6. If `brief.md` / `icp.md` were scaffolded as stubs, **fill them in now** before
   handing off — the critique skills depend on them.

7. Hand the session path to `visual-qa` (which captures the target) and the other
   critique skills. They read the target, brief, brand, and ICP from the session;
   never re-pick them.

## Conventions

- One target × one review per session. The same asset revised and re-reviewed is
  a new version in the same session (`nit capture --bump`), not a new session.
- Reviewing the same content in two formats (a PDF and a web page) is two
  sessions.
