---
name: audience-research
description: Conduct background research and review supplied context (meeting transcripts, docs, URLs) about the reader, using available tools, to surface their stated and implied needs, challenges, objectives, attitudes, and approach. Files each source via `audience research add` and writes a cited review per source. Use after persona-intake, before psychographic-profile.
---

# audience-research

Build the evidence base for the reader model. The persona says *who* they are;
research establishes *what they need and how they think* — from what they've
actually said and from informed background research. Everything the profile later
claims must trace back to something here.

## Steps

1. **Review supplied context.** For each artifact the user provides — meeting
   transcripts, call notes, emails, docs, a website — read it as evidence about
   the reader. File it and record provenance:
   ```bash
   audience research add --audience <slug> --source <path-or-url> --kind transcript|doc|url|interview
   ```
   Then write a short, cited review at `research/<source>.md`: what this source
   says about the reader's needs, challenges, objectives, attitudes, approach.
   Pull **direct quotes** where they reveal a need or objection.

2. **Use tools for background research.** Where context is thin, research the
   reader's role/segment/situation with the host's tools — meeting/notes tools
   (Krisp, Notion, Drive transcripts), web research, CRM. Record each as a source
   (`--kind web-research`) and review it the same way. Don't invent; mark
   inferences as inferences.

3. **Separate stated from implied.** Note what the reader explicitly says they
   need versus what's implied by their situation, role pressures, and objections.
   Both matter; the profile will weight them.

4. **Surface objections + decision factors.** What would make this reader say no?
   What do they weigh when deciding? These become the sharpest rubric tests later.

5. Hand off to `psychographic-profile` to synthesize the reviews into the
   structured `_audience.yml`. Keep each claim attributable to a `research/` source.

## Conventions

- Evidence-first: every need/attitude the profile asserts should cite a source in
  `research/`. No source → it's a hypothesis, labelled as one.
- The CLI files the raw source + provenance; the **review** (judgment) is yours,
  written to `research/<source>.md`.
- Respect confidentiality — transcripts and docs stay in the local store; don't
  send them outward.
