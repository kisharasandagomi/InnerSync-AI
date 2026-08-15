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

> **SUPERSEDED — v1 → v2.** A systematic target-leakage audit
> (`02_Preprocessing.ipynb`) found six features that each individually
> reproduce or beat the full model's accuracy via a trivial one-value lookup
> rule. The model was retrained with those six excluded. **The current model
> is v2 (14 features).** The v1 description immediately below is retained for
> the record; current v2 figures follow in Evaluation Results.

**Current model (v2)**: Random Forest (`RandomForestClassifier`),
`max_depth=None`, `min_samples_leaf=1`, `min_samples_split=5`,
`n_estimators=200`, `random_state=42`, trained on **14 features** with
`sleep_quality`, `future_career_concerns`, `blood_pressure`, `depression`,
`bullying`, and `anxiety_level` excluded for target leakage. Random Forest
was **re-selected from scratch** on the corrected feature set (highest
ROC-AUC 0.9838, highest F1 0.8815, and the only candidate without an adverse
CV-to-test gap), not carried over by assumption.

**Superseded model (v1)**: Random Forest, hyperparameters
`max_depth=10`, `min_samples_leaf=1`, `min_samples_split=2`,
`n_estimators=100`, `random_state=42`, trained on all 20 features.

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

### Current — v2 (14 features, leaky features excluded)

Identical 220-row held-out test set, identical CV/tuning protocol.

| Model | Accuracy | Balanced Acc. | Precision (macro) | Recall (macro) | F1 (macro) | ROC-AUC (macro, OvR) |
|---|---|---|---|---|---|---|
| Logistic Regression (baseline) | 0.8773 | 0.8775 | 0.8772 | 0.8775 | 0.8773 | 0.9520 |
| **Random Forest (selected)** | **0.8818** | **0.8821** | **0.8824** | **0.8821** | **0.8815** | **0.9838** |
| XGBoost | 0.8727 | 0.8731 | 0.8730 | 0.8731 | 0.8726 | 0.9807 |
| SVM | 0.8773 | 0.8775 | 0.8786 | 0.8775 | 0.8776 | 0.9138 |
| LightGBM | 0.8727 | 0.8730 | 0.8736 | 0.8730 | 0.8725 | 0.9821 |

Selected model's cross-validated `f1_macro`: 0.8740 (test 0.8815 — test
exceeds CV, the healthy pattern).

**Excluding the six leaking features cost only 0.0046 accuracy.** That is
itself the central finding, not a reassurance — see Limitations.

### Superseded — v1 (20 features, leakage present)

Retained for the record. These are the figures originally reported before the
leakage audit.

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

v1 selected model's confusion matrix (rows = true, columns = predicted):

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

- **CRITICAL — pervasive target leakage in the training dataset.** A
  systematic audit (`02_Preprocessing.ipynb`) found that label information is
  redundantly encoded across essentially every feature. A trivial one-value
  lookup rule on `sleep_quality` alone scores 0.9045 accuracy, and on
  `future_career_concerns` alone 0.9000 — **both beat the entire tuned
  20-feature model (0.8864)**. Six features individually rival it. Every
  feature shows the same signature: a small near-uniform bucket at value 0,
  with all other values mapping to a single class at 85–100% purity,
  consistent with features generated conditional on the label.
  **Removal is not a remedy**: dropping the three worst offenders costs zero
  accuracy, and the six *weakest* features alone still yield 0.85 against a
  0.333 chance baseline. **No accuracy figure in this card — v1 or v2 —
  should be presented as evidence of real-world stress-prediction
  capability.** See `methodology.md` § Data Quality / Leakage Finding and
  `ADR.md` ADR-003.
- This is the same category of defect that led to the retraction of a
  comparable published study discussed in Chapter 2 (Tariq et al., 2025) —
  here independently identified in this project's own benchmark data rather
  than taken from the retraction notice.
- Trained substantially on a single public, self-reported, crowd-sourced
  dataset with limited independent verification of its fields — treat
  benchmark performance as an upper bound, not a guarantee of real-world
  accuracy. EDA found an unusually clean correlation structure in this
  dataset (mean |r| = 0.58 across the 210 feature pairs; 17 pairs above
  |r| = 0.7), which plausibly inflates apparent performance; see
  `docs/research/methodology.md` § Handling the risk of inflated apparent
  performance.
- Correlation-based EDA and VIF both **passed** this dataset. Neither
  detected the leakage, because the strongest leaking mappings are
  non-monotonic and therefore invisible to Pearson correlation. SHAP analysis
  was what surfaced it.
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
