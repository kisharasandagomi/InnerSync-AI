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
  Analysis" dataset (1,100 rows, 21 features — 20 inputs + target, 5 domains).
  Exact file version used is pinned by SHA-256
  `14a45e92708b0c063ad4ab04563aa8fd4e3fc27157fd282e1c0658dc5161faed`, recorded
  in every experiment log and in `ml_pipeline/artifacts/artifact_manifest.json`.
- External validation: locally collected questionnaire/conversational data
  (see `data_management_plan.md`). `[TBD: n, collection window — not yet
  collected; planned for Phase 8]`

## Model Type and Selection

**Random Forest** (`scikit-learn` `RandomForestClassifier`), hyperparameters
`max_depth=10`, `min_samples_leaf=1`, `min_samples_split=2`,
`n_estimators=100`, `random_state=42`.

Selected over Logistic Regression, XGBoost, SVM, and LightGBM. Selection was
explicitly not made on accuracy alone — Random Forest and SVM tie exactly on
accuracy (0.8864), so accuracy could not have resolved the comparison. The
decision rests on: best held-out ROC-AUC (0.9844); a decisive ROC-AUC margin
over the otherwise-tied SVM (0.9844 vs 0.9245); no adverse CV-to-test gap
(unlike LightGBM, see Limitations); TreeSHAP compatibility, giving exact
rather than approximated Shapley values for the project's core explainability
contribution; and precedent in the reviewed literature. Full reasoning,
including the trade-off against Logistic Regression's marginally higher
ROC-AUC, is documented in `docs/research/methodology.md` § Model Selection.
All five runs are logged in `ml_pipeline/experiments/`.

## Evaluation Results

All five models on the identical 220-row held-out test set. The selected
model is shown in bold; the others are retained here for transparency, since
reporting only the winner would obscure how narrow the margins are.

| Model | Accuracy | Balanced Acc. | Precision (macro) | Recall (macro) | F1 (macro) | ROC-AUC (macro, OvR) |
|---|---|---|---|---|---|---|
| Logistic Regression (baseline, untuned) | 0.8818 | 0.8821 | 0.8818 | 0.8821 | 0.8820 | 0.9851 |
| **Random Forest (selected)** | **0.8864** | **0.8868** | **0.8882** | **0.8868** | **0.8861** | **0.9844** |
| XGBoost | 0.8727 | 0.8729 | 0.8730 | 0.8729 | 0.8729 | 0.9682 |
| SVM | 0.8864 | 0.8868 | 0.8868 | 0.8868 | 0.8860 | 0.9245 |
| LightGBM | 0.8727 | 0.8731 | 0.8731 | 0.8731 | 0.8726 | 0.9819 |

Precision/recall/F1 are macro-averaged (the three classes are near-balanced,
and macro weights each equally rather than letting any one dominate).
Balanced accuracy is by definition macro-averaged recall, hence identical to
the recall column — both are reported because both are required.

Selected model's confusion matrix (rows = true, columns = predicted):

| | pred 0 | pred 1 | pred 2 |
|---|---|---|---|
| **true 0** | 61 | 6 | 7 |
| **true 1** | 2 | 67 | 3 |
| **true 2** | 3 | 4 | 67 |

Validation method: stratified 80/20 train/test split (880 train / 220
held-out test, `random_state=42`), with hyperparameters tuned by
grid/randomized search under **stratified 5-fold cross-validation on the
training split only**. The held-out test set was never used for tuning or
model selection during training. Selected model's cross-validated
`f1_macro` was 0.8808. **Internal validation only** — no external validation
set has been used yet; that is planned for Phase 8 and is required before
these figures can be treated as evidence of real-world performance.

## Explainability

Method: SHAP. The selected model is a tree ensemble, so **TreeSHAP applies** —
Shapley values are computed exactly rather than approximated (this was one of
the selection criteria; see `methodology.md` § Model Selection). Global and
local explanations generated; translated to human-readable form via the
Human-Centered Explanation Generator (never shown to users in raw form — see
`.claude/skills/explainable-ai/SKILL.md`).

`[TBD: SHAP implementation and faithfulness check are Phase 4 — not yet
performed. Fill in global/local explanation findings once complete.]`

## Limitations

- Trained substantially on a single public, self-reported, crowd-sourced
  dataset with limited independent verification of its fields — treat
  benchmark performance as an upper bound, not a guarantee of real-world
  accuracy. EDA found an unusually clean correlation structure in this
  dataset (mean |r| = 0.58 across the 210 feature pairs; 17 pairs above
  |r| = 0.7), which plausibly inflates apparent performance; see
  `docs/research/methodology.md` § Handling the risk of inflated apparent
  performance.
- **Cross-validation score alone was not sufficient to select a model, and
  should not be read as one.** LightGBM produced the highest cross-validated
  `f1_macro` of any candidate (0.8945) but one of the lowest held-out test F1
  scores (0.8726) — a drop of ~0.022 indicating overfitting to the CV fold
  structure. The selected Random Forest showed no such gap (CV 0.8808 → test
  0.8861). Any future re-tuning must continue to check CV and held-out
  performance together, not CV in isolation.
- Three-class stress labelling is a simplification of a continuous,
  multi-dimensional experience.
- Internal validation only so far. All reported figures come from one
  dataset, split internally. No external/held-out-source validation has been
  performed (Phase 8).
- `[TBD: add any demographic subgroup performance disparities found during
  evaluation]`
- Not validated against any clinical instrument or professional assessment —
  this is explicitly out of scope (see `ethical_framework.md`).

## Bias Considerations

**Subgroup bias analysis is not possible on the current training dataset.**
The Kaggle dataset contains no demographic fields whatsoever — its 20 input
features are entirely psychological, physiological, social, environmental,
and academic (see `feature_schema.json` for the full list). There is no
gender, age, degree, year-of-study, or socioeconomic field to disaggregate
by, so no disparity analysis can be run against it, and the absence of
measured disparity here must not be read as evidence of its absence.

This is a limitation of the benchmark dataset, not a decision to skip the
analysis. `[TBD: run disaggregated performance analysis on the Phase 8
locally-collected validation set, where demographic fields are collected
under the consent process in ethical_framework.md and sample size allows.]`

## Failure Cases / Known Risks

- A student whose stress is driven by a factor not represented in the feature
  set (e.g. a factor absent from the questionnaire) may receive a
  misleadingly reassuring prediction.
- Free-text sentiment analysis may misread sarcasm, culturally specific
  expression, or non-English phrasing if present in conversational input.
- `[TBD: add any additional failure modes observed during testing]`
