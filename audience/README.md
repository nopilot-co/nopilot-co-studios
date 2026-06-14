# audience-studio

Model **the reader** — the person a piece of work must satisfy — and critique work
against them. The audience studio builds a reusable, structured psychographic
profile + need-state (a studios-level resource, like a brand), derives a weighted
rubric from it, and assesses an artifact's reader-fit, returning a verdict and a
ranked list of target strengthening areas.

It is a reader-**subjective** review lens, complementary to the
[nitpicker](../nitpicker)'s **objective** one — and it reuses the nitpicker's
scoring engine, so verdicts read identically.

See [`CLAUDE.md`](CLAUDE.md) for the full layout, the skill ↔ CLI contract, and the
data root. Install with [`install.sh`](install.sh); orchestrate with
`/audience-studio`.

```bash
./install.sh
.venv/bin/audience doctor
.venv/bin/audience persona new --audience vp-eng-scaleup
# … research → profile → rubric → critique …
.venv/bin/audience review score --session ~/context/studios/audience/vp-eng-scaleup/sessions/<name>
```
