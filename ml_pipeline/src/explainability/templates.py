"""Plain-language phrase templates — one per feature per direction, for all 14 v2 features.

Every phrase is written to complete the sentence stem "... <phrase>", in second
person, and deliberately hedged ("appears to", "seems to be") rather than
asserted: the model produces a probabilistic estimate, and the language should
not claim more certainty than that.

Vocabulary constraints, per `docs/governance/ethical_framework.md`:
  approved  — "wellbeing support", "stress management", "emotional wellbeing"
  forbidden — "diagnosis", "cure", "treatment", "you have [condition]"

No phrase may contain a feature name, a numeric value, or ML terminology.
"""

from __future__ import annotations

# Direction keys:
#   "raising" — this factor is pushing the student's stress estimate upward
#   "easing"  — this factor is working protectively, pushing it downward
#
# Direction is derived from the SHAP value's sign with respect to the
# high-stress class, NOT from the raw feature value, so a template is only ever
# selected on the model's actual attribution.

FEATURE_PHRASES: dict[str, dict[str, str]] = {
    "self_esteem": {
        "raising": "how you have been feeling about yourself lately appears to be weighing on you",
        "easing": "a steady sense of your own worth seems to be working in your favour",
    },
    "mental_health_history": {
        "raising": "some of what you have carried before around your wellbeing may still be with you",
        "easing": "you do not appear to be carrying a long history of wellbeing difficulties",
    },
    "headache": {
        "raising": "the physical tension you have been noticing, such as frequent headaches, appears to be adding to the strain",
        "easing": "you do not seem to be carrying much physical tension at the moment",
    },
    "breathing_problem": {
        "raising": "the physical signs you have described, such as finding it harder to breathe easily, appear to be adding pressure",
        "easing": "being able to breathe comfortably and settle physically seems to be one of the things going well for you",
    },
    "noise_level": {
        "raising": "the noise around where you live or study appears to be making it harder to settle",
        "easing": "having a reasonably quiet space around you seems to be helping",
    },
    "living_conditions": {
        "raising": "your current living situation appears to be adding to the pressure you are under",
        "easing": "your living situation seems to be giving you a reasonably steady base",
    },
    "safety": {
        "raising": "not feeling entirely secure in your surroundings appears to be taking a toll",
        "easing": "feeling safe where you spend your time seems to be supporting you",
    },
    "basic_needs": {
        "raising": "having your day-to-day essentials reliably met seems to be a struggle right now, and that appears to be weighing on you",
        "easing": "having your everyday essentials reliably met seems to be giving you a solid foundation",
    },
    "academic_performance": {
        "raising": "how your studies have been going appears to be weighing on you",
        "easing": "how your studies have been going seems to be working in your favour",
    },
    "study_load": {
        "raising": "the amount of academic work you are carrying appears to be a real pressure at the moment",
        "easing": "your current workload seems to be manageable",
    },
    "teacher_student_relationship": {
        "raising": "your relationships with teaching staff appear to be a source of strain rather than support",
        "easing": "feeling supported by teaching staff seems to be helping you",
    },
    "social_support": {
        "raising": "you may be missing consistent support from the people around you",
        "easing": "the people around you seem to be a genuine source of support",
    },
    "peer_pressure": {
        "raising": "pressure from the people around you appears to be adding to what you are already managing",
        "easing": "you do not seem to be under much pressure from those around you",
    },
    "extracurricular_activities": {
        "raising": "how much you are taking on outside your studies appears to be stretching you",
        "easing": "the balance you have found outside your studies seems to be working for you",
    },
}

# Opening sentence, keyed by predicted class label.
OPENING_BY_CLASS: dict[int, str] = {
    0: (
        "Your current wellbeing check-in suggests things feel reasonably steady "
        "for you at the moment."
    ),
    1: (
        "Your current wellbeing check-in suggests you are carrying a moderate "
        "amount at the moment."
    ),
    2: (
        "Your current wellbeing check-in suggests you are under a fair amount of "
        "pressure at the moment."
    ),
}

# Closing sentence, keyed by predicted class label. Non-clinical, forward-looking,
# and explicitly framed as changeable rather than as a fixed verdict.
CLOSING_BY_CLASS: dict[int, str] = {
    0: (
        "This is a snapshot of how things look right now rather than a fixed "
        "picture, and it can shift as your circumstances do."
    ),
    1: (
        "This is a snapshot of how things look right now rather than a fixed "
        "picture. Small, manageable changes in one of these areas often make a "
        "noticeable difference."
    ),
    2: (
        "This is a snapshot of how things look right now rather than a fixed "
        "picture. If this feels familiar or has been going on for a while, "
        "talking it through with your university wellbeing service is a "
        "reasonable next step."
    ),
}

# Connectors used when listing contributing factors, so the paragraph does not
# read as a bulleted list rendered into prose. At most two phrases are ever
# joined into one sentence — stacking three full clauses with "and" produced
# run-on sentences that undermined the clarity criterion.
RAISING_LEAD_IN = "In particular,"
RAISING_ADDITIONAL = "Alongside that,"

# Used when protective factors accompany pressures.
EASING_LEAD_IN = "On the other side,"
# Used when protective factors are all the model found — phrased to stay
# coherent after an opening that already named a moderate or high level, where
# "Encouragingly, ..." would read as contradicting the opening.
EASING_ONLY_LEAD_IN = "What does seem to be steadying things is that"
EASING_ADDITIONAL = "It also helps that"

# Terms that must never appear in user-facing output.
# Clinical vocabulary comes from ethical_framework.md's avoided list; the ML
# terms enforce the hard rule in explainable-ai/SKILL.md.
FORBIDDEN_CLINICAL_TERMS = (
    "diagnosis",
    "diagnose",
    "diagnosed",
    "cure",
    "treatment",
    "treat",
    "disorder",
    "illness",
    "disease",
    "symptom",
    "patient",
    "therapy",
    "medication",
    "prescribe",
    "clinical",
    "condition",
)

FORBIDDEN_ML_TERMS = (
    "shap",
    "feature",
    "importance",
    "model",
    "prediction",
    "predicted",
    "probability",
    "classifier",
    "algorithm",
    "weight",
    "coefficient",
    "score",
    "confidence",
    "training",
    "dataset",
    "variable",
)
