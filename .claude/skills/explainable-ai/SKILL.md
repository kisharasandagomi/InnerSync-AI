# Explainable AI Skill

Trigger: any work inside `ml_pipeline/` SHAP analysis, or `backend/app/explainability/`.

Act as an explainable AI researcher. Always consider: SHAP values, global vs.
local explanation, and — critically — the gap between a technically correct
explanation and a human-understandable one.

Hard rule: **never expose raw SHAP values, SHAP plots, or ML feature-importance
terminology to the end user.** These stay in logs/debug output for research
and evaluation purposes only.

The pipeline is always: technical explanation → human-centred translation.
Example:
- Technical: `Feature importance: Sleep quality = -0.42`
- User-facing: "Your recent sleep pattern appears to be one of the main
  factors affecting your current stress level."

When building or reviewing the Human-Centered Explanation Generator, check:
- Clarity: could a student with no ML background understand this in one read?
- Trust: does the language feel supportive rather than clinical or alarming?
- Faithfulness: does the plain-language explanation actually match the
  underlying SHAP attribution direction and rough magnitude (log both to
  verify, don't just eyeball it)?
- Usefulness: does the explanation point toward something the student could
  plausibly act on (ties into the recommendation engine)?

When evaluating explanations with real users later, these four properties
(clarity, trust, faithfulness, usefulness) are the metrics to test, not just
"did they like it."

Style rule (round 4): no em-dashes (—) in any generated or static user-facing text (explanation/recommendation/comparative-trend/greeting templates, chatbot system prompt and fallback replies, static frontend copy). Use a comma, period, colon, or restructured sentence instead, whichever reads most naturally for that instance. Applies to new text going forward, not to code comments or docstrings.
