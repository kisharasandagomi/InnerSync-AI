# InnerSync AI

An Explainable AI Framework for Early Stress Prediction and Personalized
Wellbeing Intervention for University Students.

BSc (Hons) Data Science final-year dissertation project. The research
contribution is a Human-Centered Explainable AI Framework combining
comparative ML, SHAP interpretation, human-centred explanation generation,
adaptive personalised recommendations, and continuous wellbeing monitoring.

## Project Structure

- `ml_pipeline/` — Research World: dataset, EDA, preprocessing, feature
  engineering, model experiments, evaluation, SHAP analysis. Produces
  versioned artifacts consumed by the backend.
- `backend/` — Production World: FastAPI service that loads trained artifacts
  and serves predictions, explanations, and recommendations. Never trains a
  model.
- `frontend/` — Data-collection and delivery layer (chat interface,
  questionnaire, dashboard). Not the research deliverable itself.
- `docs/` — Dissertation-supporting documentation: research chapters,
  architecture, governance, and architectural decision records.
- `deployment/` — Container orchestration for local/dev environments.

See [CLAUDE.md](CLAUDE.md), [IMPLEMENTATION_RULES.md](IMPLEMENTATION_RULES.md),
and [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for the governing rules and
current project phase.

## Environment

Conda environment `mainks` (Python 3.13.13). See
[environment.yml](environment.yml) for the full dependency list.

```bash
conda env create -f environment.yml
conda activate mainks
```
