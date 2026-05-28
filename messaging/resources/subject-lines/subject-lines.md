# Subject-line library

Patterns for email subjects, by purpose. The `compose` skill picks a pattern and
fills it in the brand's voice. **Hard limit: ≤ 60 characters** (enforced by
`message lint`). Avoid spam triggers (ALL CAPS, "free", "act now", excess `!`).

Each pattern lists its slug, the shape, and a filled example.

## Outreach (cold)

| Slug | Pattern | Example |
|------|---------|---------|
| `observation` | `{their thing} → {implied gap}` | `Your pricing page vs. your demo flow` |
| `mutual` | `{shared connection / context}` | `Saw your talk at RevOps Summit` |
| `question` | `{specific yes/no question}` | `Worth a look at your onboarding drop-off?` |
| `number` | `{metric} {audience} care about` | `3 ways teams cut trial churn` |

## Follow-up

| Slug | Pattern | Example |
|------|---------|---------|
| `reply-thread` | `Re: {original subject}` | `Re: Your onboarding drop-off` |
| `one-more` | `One more thought on {topic}` | `One more thought on trial churn` |
| `bump` | `{short nudge}` | `Bad time?` |

## Announcement

| Slug | Pattern | Example |
|------|---------|---------|
| `whats-new` | `{thing} is here` | `Sequences are here` |
| `benefit-led` | `{outcome}, now {easier}` | `Multi-step campaigns, now one command` |

## Nurture

| Slug | Pattern | Example |
|------|---------|---------|
| `how-to` | `How to {do the thing}` | `How to write a follow-up that lands` |
| `insight` | `{counterintuitive claim}` | `Shorter emails get more replies` |

> Add patterns by appending rows. Keep examples within 60 chars so they double as
> length checks.
