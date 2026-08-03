# Master Project Context

Single-page orientation for anyone (including future-Claude) picking this
project up cold. For governing rules see [CLAUDE.md](CLAUDE.md) and
[IMPLEMENTATION_RULES.md](IMPLEMENTATION_RULES.md); for current phase see
[PROJECT_ROADMAP.md](PROJECT_ROADMAP.md).

## What this is

InnerSync AI is a BSc (Hons) Data Science dissertation project: an
explainable ML framework that predicts early stress in university students
from a structured questionnaire (and later, NLP-derived conversational
features), explains the prediction in plain language via SHAP, and suggests
personalised, non-clinical wellbeing recommendations.

## What this is not

Not a new ML algorithm. Not a clinical/diagnostic tool. Not primarily a
chatbot or web app — those exist only to collect data for, and deliver the
output of, the ML/XAI research.

## The two worlds

- **Research World** (`ml_pipeline/`): dataset → EDA → preprocessing →
  feature engineering → comparative model training → evaluation → SHAP.
  Outputs versioned artifacts.
- **Production World** (`backend/app/`): loads artifacts, never trains.
  Predicts → explains (human-readable only) → recommends.

## Primary dataset

Kaggle "Student Stress Factors: A Comprehensive Analysis" (rxnach), 1,100
responses, 21 features. Used as a training/benchmarking resource, not the
sole evidence base — see `docs/governance/data_management_plan.md` for the
provenance limitation and the plan for local validation data.

## Current phase

See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) — as of this writing, Phase 0
(foundation/scaffold) is in progress.
