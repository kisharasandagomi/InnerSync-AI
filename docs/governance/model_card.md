# Model Card — InnerSync AI Stress Prediction Model

*This card is a living document. Fields marked `[TBD]` are filled in once the
corresponding phase of the roadmap is complete — do not leave them blank in
the final dissertation appendix.*

## Model Purpose

Classifies a university student's current stress level (three-class: low /
moderate / high, per the benchmark dataset's labelling) from structured
questionnaire and NLP-derived conversational features, to support an
explainable, non-diagnostic wellbeing intervention system.

## Intended Users

The system itself (via the backend `app/ml` loader), not a clinician or
administrator directly. Output is always mediated through the Human-Centered
Explanation Generator before reaching a student.

## Training Data

- Primary training/benchmark: Kaggle "Student Stress Factors: A Comprehensive
  Analysis" dataset (1,100 rows, 21 features, 5 domains). `[TBD: confirm final
  dataset version/date used]`
- External validation: locally collected questionnaire/conversational data
  (see `data_management_plan.md`). `[TBD: n, collection window]`

## Model Type and Selection

`[TBD: final selected model, e.g. "XGBoost, selected over Random Forest and
SVM based on F1-score and recall on the high-stress class, see
ml_pipeline/experiments/ for full comparison"]`

## Evaluation Results

`[TBD — fill in once Phase 2 is complete]`

| Metric | Value |
|---|---|
| Accuracy | |
| Precision | |
| Recall | |
| F1-score | |
| ROC-AUC | |
| Balanced Accuracy | |

Validation method: `[TBD: k-fold CV + external validation set, state k and
split ratios]`

## Explainability

Method: SHAP (TreeSHAP if the final model is tree-based). Global and local
explanations generated; translated to human-readable form via the Human-
Centered Explanation Generator (never shown to users in raw form — see
`.claude/skills/explainable-ai/SKILL.md`).

## Limitations

- Trained substantially on a single public, self-reported, crowd-sourced
  dataset with limited independent verification of its fields — treat
  benchmark performance as an upper bound, not a guarantee of real-world
  accuracy.
- Three-class stress labelling is a simplification of a continuous,
  multi-dimensional experience.
- `[TBD: add any demographic subgroup performance disparities found during
  evaluation]`
- Not validated against any clinical instrument or professional assessment —
  this is explicitly out of scope (see `ethical_framework.md`).

## Bias Considerations

`[TBD: report performance broken down by available demographic fields —
gender, degree, year — where sample size allows, and note any disparity]`

## Failure Cases / Known Risks

- A student whose stress is driven by a factor not represented in the feature
  set (e.g. a factor absent from the questionnaire) may receive a
  misleadingly reassuring prediction.
- Free-text sentiment analysis may misread sarcasm, culturally specific
  expression, or non-English phrasing if present in conversational input.
- `[TBD: add any additional failure modes observed during testing]`
