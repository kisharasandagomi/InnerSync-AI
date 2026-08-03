# Ethical AI Skill

Trigger: any task touching user data collection, storage, consent, model
training on personal/mental-health-adjacent data, or public-facing system
behaviour (chatbot responses, dashboard wording).

This project handles self-reported, mental-health-adjacent data from
university students. Treat every data-handling decision as a governance
decision, not just an engineering one. Check `docs/governance/` before
building anything new that touches user data.

Always verify:
- Consent: is there a clear, documented consent step before any assessment or
  data collection, and is it referenced in `data_management_plan.md`?
- Anonymisation: can this data be traced back to an individual more easily
  than necessary? If not required for the feature, don't store identifiers
  alongside sensitive fields.
- Scope boundary: does any output (chatbot message, explanation, dashboard
  label) risk reading as a diagnosis, medical advice, or treatment? If so,
  rewrite it — the system supports wellbeing, it does not diagnose or treat.
- Escalation: if a stress pattern is severe/persistent, does the flow
  recommend contacting real university wellbeing services rather than
  quietly continuing automated recommendations indefinitely?
- Provenance: if using a public dataset, is its collection method, consent
  status, and any known limitations documented? (A directly comparable
  published study in this research area was retracted for skipping exactly
  this — see docs/research/literature_review.md, Section 2.4/2.9.)

When unsure whether something crosses an ethical line, flag it explicitly
rather than silently proceeding — this is one area where asking first is
always cheaper than fixing it later.
