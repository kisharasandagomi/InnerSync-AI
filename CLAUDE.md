# InnerSync AI — Claude Development Constitution

## Project Identity

You are assisting in developing **InnerSync AI**: An Explainable AI Framework for
Early Stress Prediction and Personalized Wellbeing Intervention for University
Students.

This is an individual final-year **BSc (Hons) Data Science** dissertation project.
Target: First Class Honours (95+ marks).

Every decision is judged against four criteria, in this order of priority:

1. Research contribution and academic justification
2. Evaluation rigour (does this survive scrutiny, not just "does it run")
3. Software engineering quality
4. Feature completeness (lowest priority — never add a feature just because it's possible)

## Project Framing (Data Science, not Software Engineering)

The **centre of gravity is the predictive model and the evidence around it**, not
the application. The chatbot, questionnaire, and dashboard are the data-collection
and delivery layer for the research — they are not the deliverable in themselves.

If a task description makes the chatbot/UI sound like the main achievement,
reframe it: "this feature exists to collect data for / deliver the output of the
ML and XAI pipeline."

## The Two Worlds — Never Mix Them

This project has a **Research World** and a **Production World**. They are
physically separate in the repo and must stay that way.

```
RESEARCH WORLD (ml_pipeline/)              PRODUCTION WORLD (backend/app/)
Dataset → EDA → Preprocessing →            Student → Frontend → API →
Feature Engineering → Model Experiments    Load trained artifact → Predict →
→ Evaluation → SHAP Analysis               Explain → Recommend
   ↓ outputs serialized artifacts ────────────────→ (loaded, never retrained)
```

Hard rule: **`backend/app/` never trains a model.** It only loads artifacts
produced by `ml_pipeline/` (`.pkl` models, fitted preprocessors, `feature_schema.json`,
`shap_config.json`). If a backend task seems to require training logic, stop and
flag it — that logic belongs in `ml_pipeline/src/`, exported as an artifact.

## Machine Learning Principles

Pipeline must include, in order: data understanding → cleaning → feature
engineering → baseline model → comparative model training → hyperparameter
tuning → cross-validated evaluation → SHAP explainability.

Candidate models: Logistic Regression, Random Forest, XGBoost, SVM, LightGBM,
Neural Network (optional, secondary).

Evaluation metrics required for every model comparison: Accuracy, Precision,
Recall, F1-score, ROC-AUC, Balanced Accuracy, Confusion Matrix, k-fold
Cross-Validation. **Never select a model on accuracy alone** — justify the
choice against at least F1 and ROC-AUC too, and note the trade-off explicitly.

Always check for and report: class imbalance handling, data leakage risk,
multicollinearity (VIF), and whether validation was internal-only or included
an external/held-out set. (See Chapter 2 of the dissertation — this project
exists partly because prior work in this space failed on exactly these points.)

## Explainable AI Principles

SHAP is used internally. End users must **never see**: SHAP plots, SHAP values,
feature-importance scores, or technical ML/AI terminology.

Instead, always generate a human-readable translation.

Technical: `Feature importance: Sleep quality = -0.42`
User-facing: *"Your recent sleep pattern appears to be one of the main factors
affecting your current stress level."*

Every explanation-generation task should ask: would a stressed 19-year-old
understand this without any ML background?

## Research Contribution

The contribution is a **Human-Centered Explainable AI Framework** combining
comparative ML, SHAP interpretation, human-centred explanation generation,
adaptive personalised recommendations, and continuous wellbeing monitoring —
not a new algorithm, and not "an AI chatbot."

## Ethical Requirements (see docs/governance/ for full detail)

The system must **never**: diagnose mental illness, replace psychologists,
provide medical treatment, or prescribe medication.

The system **should**: support wellbeing, encourage healthy habits, recommend
professional help when high-risk patterns persist, and protect user privacy.

Before implementing anything that touches user data, check
`docs/governance/ethical_framework.md` and `data_management_plan.md`. Consent,
anonymisation, and documented data provenance are non-negotiable requirements,
not nice-to-haves — a real, comparable published study in this exact research
area was retracted for skipping them.

## Software Engineering Standards

Clean Architecture, SOLID, modular design, separation of concerns, reusable
services. Python: PEP8, type hints, docstrings, explicit error handling.
Avoid: hardcoded values, duplicate code, monolithic files.

Every major module needs: a clear one-line purpose statement, docstrings,
unit tests where practical, and a README/docs update if its interface changes.

## Development Workflow

Before writing code:
1. Understand the existing architecture (read relevant files first)
2. State the proposed solution in one or two sentences
3. State the research/academic value of doing it this way
4. Note at least one alternative considered and why it was rejected
5. Then implement

Do not skip steps 2–4 for anything touching `ml_pipeline/` or `explainability/`
— those are the dissertation's core contribution and deserve a paper trail.

## How Skills and the Agent Work Together

Skills run automatically, triggered by context — they are the "always-on"
behaviour: `research-quality`, `machine-learning`, `explainable-ai`,
`software-engineering`, `academic-review`, `ethical-ai`.

One agent runs on explicit request only, before milestones:
`dissertation-review-agent` — invoked as "review this like a supervisor" or
"use dissertation-review-agent on my methodology chapter." It exists to shift
from "how do I implement this" to "would this survive a UK dissertation panel."

No other agents (ml/backend/frontend/architecture) — unnecessary role-management
overhead for a solo project where Claude Code + skills already provide continuous
good behaviour.
