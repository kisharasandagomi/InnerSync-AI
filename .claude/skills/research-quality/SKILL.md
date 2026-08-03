# Research Quality Skill

Trigger: before implementing any non-trivial feature, and whenever proposing a
new file, module, or dependency.

Before implementing anything, ask:

- Does this improve the research contribution, the evaluation, or the
  dissertation's academic quality?
- If this were removed, would the dissertation's argument actually weaken —
  or would nobody notice?
- Is this the simplest version that still produces defensible evidence, or is
  it complexity for its own sake?

If a feature can't be justified in one sentence against Chapter 2's research
gap (explainability accessibility, adaptive recommendations, validated
evaluation), flag it and ask before building it.

Every feature requires a one-line justification recorded in a commit message
or docs/decisions/ADR.md entry — "why is this academically valuable" is not
optional.

Avoid: adding models, metrics, or UI features purely because they are
technically possible or impressive-looking. Prefer fewer, better-justified,
better-evaluated components over a longer feature list.
