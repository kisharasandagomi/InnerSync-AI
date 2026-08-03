# Ethical Framework — InnerSync AI

## Intended Use

InnerSync AI is a wellbeing-support decision-aid for university students. It
predicts an early-stage stress level from questionnaire and conversational
data, explains that prediction in plain language, and suggests personalised,
adaptive self-help interventions (sleep hygiene, study planning, physical
activity, social/journaling prompts).

It is intended to be used voluntarily by students as a self-monitoring and
early-awareness tool, alongside — not instead of — existing university
wellbeing services.

## Non-Intended Use

InnerSync AI must **not** be used, presented, or relied upon as:
- A clinical diagnostic tool for depression, anxiety, or any other mental
  health condition
- A replacement for a psychologist, counsellor, GP, or psychiatrist
- A basis for university administrative decisions about a student (e.g.
  academic standing, extenuating circumstances, disciplinary matters)
- A treatment or medication-recommendation system

Any output must be phrased to avoid the impression of diagnosis. Approved
vocabulary: "wellbeing support," "stress management," "personalised
intervention," "emotional wellbeing." Avoided vocabulary: "diagnosis," "cure,"
"treatment," "you have [condition]."

## Privacy Principles

- Data collection is opt-in and follows informed consent (see
  `data_management_plan.md`).
- Self-reported data is stored under a pseudonymous user ID; direct
  identifiers (name, email) are stored separately from behavioural/emotional
  data where technically feasible.
- No data is shared with third parties beyond the services strictly required
  to run the system (e.g. the LLM API used for chatbot conversation), and any
  such service is disclosed to the user.
- Users can request data deletion at account level.

## Consent Process

Before the first questionnaire or conversational assessment, the user is
shown a plain-language consent screen stating: what data is collected, how it
is used (model input, research evaluation), that it is not medical care, and
that participation is voluntary and can be withdrawn at any time. No
assessment data is processed before this consent is recorded.

## Mental Health Boundaries and Escalation

If a stress prediction remains at the highest severity level across multiple
consecutive check-ins despite recommendations being engaged with, the system
must surface a clear, non-alarming prompt to contact university wellbeing
services or a relevant crisis resource, rather than continuing to offer only
automated self-help content indefinitely (see Adaptive Recovery Framework,
Module 8 Component 5).

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| User over-relies on the tool instead of seeking help | Persistent, non-intrusive signposting to real support after sustained high stress |
| Explanation is misunderstood as a diagnosis | Language review against the approved/avoided vocabulary list above; no clinical terms |
| Dataset lacks consent/provenance (as happened in a directly comparable retracted study) | Public dataset used only for training/benchmarking, documented as such; local data collection follows the consent process above |
| Model bias across demographic groups | Evaluate model performance across available demographic subgroups (age, gender, degree) where sample size allows; document any disparity found |
| Data breach | Standard secure storage (hashed credentials, environment-based secrets, no plaintext sensitive fields in logs) |
