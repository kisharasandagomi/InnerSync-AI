# Methodology

Working source of truth for the methodology chapter. Maps the project onto
CRISP-DM. See `PROJECT_ROADMAP.md` Phase 1 — not yet finalized.

## Status

Not yet populated beyond the section below.

## Multicollinearity check (VIF) — `02_Preprocessing.ipynb`

**Context**: EDA (`01_EDA.ipynb`) found unusually high pairwise correlation
across the dataset's 20 input features — mean |r| = 0.58 across all 210
feature pairs, with 17/210 pairs exceeding |r| = 0.7 (strongest:
`self_esteem` ↔ `stress_level` at −0.756). Per `IMPLEMENTATION_RULES.md`,
this required a follow-up multicollinearity check before any modelling.

**Method**: Variance Inflation Factor computed for all 20 input features
(target excluded). No `statsmodels` in the `mainks` environment, so VIF was
implemented directly against `scikit-learn` (already installed): for each
feature, an OLS regression of that feature on all 19 others, VIF = 1 /
(1 − R²). Mathematically identical to `statsmodels`'s implementation when
the regression includes an intercept, which `LinearRegression` does by
default.

**Finding**: all 20 features have VIF comfortably under the IMPLEMENTATION_RULES.md
threshold of 10. Highest is `social_support` at 5.75; lowest is
`breathing_problem` at 1.78. **Zero features exceed the threshold.**

**Why this doesn't contradict the EDA correlation flag**: VIF and pairwise
correlation measure different things. VIF asks whether a feature is
predictable from a *linear combination of all other features together*;
pairwise correlation only looks at one relationship at a time. This
dataset's correlation structure is two broad clusters (stress-increasing
features positively intercorrelated; stress-protective features positively
intercorrelated with each other and negatively with the first cluster) —
redundancy is spread thinly across many features rather than concentrated in
one feature being near-redundant with one or two specific others. That
pattern produces high pairwise correlations without producing severe VIF,
because no single feature can be reconstructed as a clean linear combination
of the rest.

**Decision on feature dropping**: none made yet — deliberately deferred to a
separate discussion, since the VIF result alone does not obviously call for
dropping anything (no feature exceeds the threshold).

**Open question for the limitations/results chapter — not resolved by VIF**:
the EDA's correlation-block structure (and the resulting near-balanced,
near-perfectly-separable class structure) is still worth addressing
independently of multicollinearity. VIF confirms the feature set is
statistically safe to feed into a model as-is; it says nothing about whether
the dataset's construct validity is realistic. A benchmark this cleanly
structured (mean |r| = 0.58, two-cluster correlation pattern) makes it easy
to reach high accuracy without that reflecting genuine real-world predictive
difficulty — consistent with the DMP's existing provenance caveat
("self-reported, crowd-sourced, no verifiable physical corroboration") but
going further than that caveat currently states. This should be addressed
explicitly in the results/limitations chapter, not left implicit.

## Handling the risk of inflated apparent performance

This section states, in advance, how this project will handle the risk
raised above — that this dataset's unusually clean correlation structure
could produce apparent model performance that overstates real-world
predictive difficulty.

**1. Explicit comparison against the literature review's accuracy range.**
When final model results are reported (Phase 2 comparative evaluation and
Phase 8 write-up), accuracy will be stated alongside the range already
established in Chapter 2's literature review: 63–99% across the 17 reviewed
studies, where the single study reporting ~99% accuracy was itself flagged
in that review as a likely overfitting/leakage case (single-institution
data, no external validation). If this project's model also lands at the
high end of that range, that will be stated directly in the results text and
explicitly connected back to this EDA/VIF finding — not left for a reader
to notice unprompted or buried in an appendix.

**2. Field-wide evidence, not just this project's own result.** The
Frontiers (2026) source already cited in Chapter 2 found this same pattern
field-wide: studies validated on a single dataset systematically report
inflated apparent performance compared to studies validated across multiple
independent datasets. That finding applies directly here — it is the reason
a single high accuracy number from `student_stress_factors.csv` alone cannot
be treated as evidence of real-world predictive validity, independent of
whatever this project's own model happens to score.

**3. The actual mitigation is external validation, not a preprocessing fix.**
VIF and correlation analysis are diagnostic, not corrective, for this
specific risk — dropping or transforming correlated features would not make
the underlying dataset less cleanly-separable, and doing so purely to lower
an accuracy number would be manufacturing a worse model for cosmetic
reasons, not a defensible methodological choice. The actual mitigation was
already part of the design before this finding: the locally-collected
questionnaire + conversational check-in data (Phase 8, external/held-out
validation set, see `data_management_plan.md`) exists specifically to test
whether performance holds up on data this project did not train on and that
was not subject to whatever produced this dataset's unusually clean
structure. That validation step is the answer to this risk; this section
documents the reasoning, it does not introduce a new plan.

## Model Selection — `03_ModelTraining.ipynb`

**Selected model: Random Forest** (`max_depth=10`, `min_samples_leaf=1`,
`min_samples_split=2`, `n_estimators=100`).

Five models were trained and evaluated on an identical stratified 80/20
split (880 train / 220 held-out test), with hyperparameters tuned by
grid/randomized search under stratified 5-fold cross-validation on the
training split only. The full comparison table is in
`03_ModelTraining.ipynb`; every run — not only the selected one — is logged
under `ml_pipeline/experiments/`, per `IMPLEMENTATION_RULES.md`.

Per `CLAUDE.md`, selection was explicitly **not** made on accuracy alone.
Indeed, accuracy alone would not have resolved this comparison: Random
Forest and SVM tie exactly on accuracy (0.8864), and all five models fall
within a narrow 0.873–0.886 band. The decision rests on the following
reasoning:

**1. Best held-out ROC-AUC (0.9844).** Random Forest achieved the highest
one-vs-rest macro ROC-AUC of any tuned model. ROC-AUC is threshold-independent,
so it measures how well the model *ranks* risk rather than how it performs at
one arbitrary decision boundary — the more relevant property for an
early-warning system whose operating threshold may later be tuned toward
higher sensitivity.

**2. SVM ruled out on ROC-AUC despite tying on F1.** Random Forest and SVM
are effectively tied on F1 (0.8861 vs 0.8860) and identical on accuracy and
balanced accuracy. They are separated decisively by ROC-AUC: 0.9844 vs
0.9245. The SVM's headline scores therefore rest on a much weaker underlying
ranking of class probabilities, and its calibrated probability estimates are
correspondingly less trustworthy — which matters directly here, since
downstream explanation and recommendation logic consumes predicted
probabilities, not just the argmax label.

**3. No meaningful CV-to-test gap, unlike LightGBM.** LightGBM produced the
*highest* cross-validated `f1_macro` of any model (0.8945) yet one of the
lowest held-out test F1 scores (0.8726) — a CV-to-test drop of roughly 0.022
in the direction that signals overfitting to the CV fold structure. Random
Forest showed the opposite, healthier pattern (CV 0.8808 → test 0.8861: test
performance slightly *exceeds* CV, consistent with the final model being
refit on the full training split rather than on 4/5 of it). **LightGBM was
therefore not selected despite having the single strongest cross-validation
number** — this is precisely the case that justifies why CV score alone was
not used as the selection criterion, and it is recorded as such in
`model_card.md` under Limitations.

**4. TreeSHAP compatibility — directly relevant to the research
contribution.** Random Forest is a tree ensemble, so SHAP values can be
computed exactly and in polynomial time via TreeSHAP. An SVM would have
required KernelSHAP, which is both approximate and substantially slower.
Since the dissertation's core contribution is a Human-Centered Explainable
AI Framework — and since Phase 4 includes a *faithfulness check* comparing
generated plain-language explanations against the SHAP values that produced
them — exact rather than approximated Shapley values materially strengthen
that evaluation. Choosing a model whose explanations are approximations
would weaken the central claim.

**5. Precedent in the reviewed literature.** Multiple studies in Chapter 2's
review found Random Forest to be a top performer on comparable
student-stress datasets, so this selection is consistent with, rather than
divergent from, the established findings in this problem space.

**Trade-off acknowledged.** Logistic Regression achieved a marginally higher
ROC-AUC (0.9851 vs 0.9844) than the selected model. It was not selected
because that difference (0.0007) is negligible and almost certainly within
noise for a 220-row test set, while Random Forest is better on every other
reported metric (accuracy 0.8864 vs 0.8818, F1 0.8861 vs 0.8820). The
untuned linear baseline performing this close to every tuned model is
itself a finding, and is treated as further evidence for the
construct-validity concern documented in the section above — it suggests the
decision boundary in this dataset is close to linearly separable, which is
not what one would expect of genuinely noisy self-reported wellbeing data.

**Not yet established.** This selection rests on internal validation only
(CV + a held-out split of the same dataset). It is provisional until the
Phase 8 external validation set is collected; if performance does not hold
there, the selection must be revisited rather than defended.

## SHAP Global Explainability — `04_SHAPAnalysis.ipynb`

SHAP values were computed with `TreeExplainer` (exact, not approximated) on
the same 220-row held-out test set, loading the saved artifact rather than
retraining. The notebook asserts the loaded model reproduces the accuracy and
F1 recorded in `artifact_manifest.json` before explaining anything, so the
explanations provably describe the model documented in the model card.

### Global importance ranking (mean |SHAP|, averaged across the 3 classes)

| Rank | Feature | mean \|SHAP\| | Domain |
|---|---|---|---|
| 1 | blood_pressure | 0.0804 | Physiological |
| 2 | sleep_quality | 0.0385 | Physiological |
| 3 | teacher_student_relationship | 0.0355 | Academic |
| 4 | academic_performance | 0.0343 | Academic |
| 5 | basic_needs | 0.0305 | Environmental |
| 6 | depression | 0.0271 | Psychological |
| 7 | social_support | 0.0270 | Social |
| 8 | self_esteem | 0.0263 | Psychological |
| 9 | anxiety_level | 0.0249 | Psychological |
| 10 | bullying | 0.0225 | Social |
| 11 | safety | 0.0213 | Environmental |
| 12 | extracurricular_activities | 0.0174 | Social |
| 13 | headache | 0.0162 | Physiological |
| 14 | peer_pressure | 0.0161 | Social |
| 15 | future_career_concerns | 0.0147 | Academic |
| 16 | study_load | 0.0096 | Academic |
| 17 | living_conditions | 0.0091 | Environmental |
| 18 | noise_level | 0.0074 | Environmental |
| 19 | mental_health_history | 0.0041 | Psychological |
| 20 | breathing_problem | 0.0034 | Physiological |

### Direction sanity check

For each feature, its value was correlated against its SHAP contribution
toward class 2 (high stress). Expected directions were **stated in advance**
from domain reasoning, then compared — a genuine pre-registered check rather
than post-hoc rationalisation.

**All 19 features with a directional prior matched expectation; zero
anomalies.** Higher anxiety, depression, bullying, peer pressure, study load,
headache, noise, and mental-health history all push toward higher predicted
stress; higher self-esteem, sleep quality, social support, academic
performance, basic needs, safety, living conditions, and teacher–student
relationship all push away from it. `extracurricular_activities` was marked
*ambiguous* in advance (overcommitment vs. healthy engagement are both
plausible) and so was not scored; the model treats it as stress-increasing
(r = +0.71), which is defensible but should not be claimed as a confirmed
prior.

The model's reasoning is therefore **directionally coherent with the
wellbeing literature**. That is a genuine positive result — but it concerns
direction only, and is separate from the magnitude problem below.

### Which domain dominates — and the artifact that undermines the question

Taken at face value, the ranking is led by the **physiological** domain
(`blood_pressure` rank 1, `sleep_quality` rank 2), followed closely by
**academic** (ranks 3–4), with psychological and social factors mid-table.
That would be a mild surprise against Chapter 2, where the reviewed
literature emphasises academic pressure and psychological factors as the
primary drivers of student stress, with physiological variables typically
treated as *consequences* of stress rather than leading predictors of it.

**That reading should not be reported, because rank 1 is a data artifact.**
Investigation in `04_SHAPAnalysis.ipynb` established:

- `blood_pressure` maps near-deterministically and **non-monotonically** to
  the target: value 1 → moderate stress in 100% of rows, value 2 → low stress
  in 100% of rows, value 3 → high stress in 73.8%. For **54.5% of the
  dataset, this single feature fixes the label exactly.**
- The mapping's non-monotonic value order is why `01_EDA.ipynb` missed it —
  Pearson correlation gave `blood_pressure` the *weakest* association of any
  feature (r = +0.394). A linear coefficient is structurally incapable of
  seeing this relationship, so the correlation heatmap gave a false
  reassurance.
- A **three-line lookup table on `blood_pressure` alone** matches the tuned
  20-feature Random Forest on accuracy (0.8864 vs 0.8864) and beats it on
  macro F1 (0.8890 vs 0.8861).

The most plausible explanation is that `blood_pressure` was **generated from
the label** during dataset construction — target leakage present in the
published data, not introduced by this project's pipeline.

### Consequences for the results and limitations chapters

1. **The five-model comparison measured less than it appeared to.** The tight
   0.873–0.886 band across all five models is the signature of every model
   finding the same shortcut, not evidence of a well-posed problem.
2. **The ~88% figures approximate an artifact ceiling** and must not be
   compared like-for-like against Chapter 2's 63–99% range.
3. **This sharpens, rather than replaces, the construct-validity concern**
   already documented above. That section anticipated inflated performance
   from a single suspiciously clean dataset; this is the concrete mechanism,
   identified and quantified.
4. **The framework itself is validated by this finding, not damaged by it.**
   The SHAP layer — the dissertation's core contribution — is what exposed a
   leak that standard correlation-based EDA had missed entirely. That is a
   defensible argument *for* explainability-first methodology, and should be
   presented as such rather than buried as an embarrassment.
5. **Recommended next modelling step** (deliberate decision, not yet taken):
   re-run the full comparison with `blood_pressure` excluded, to measure what
   the other 19 features genuinely contribute. Expect substantially lower
   headline numbers — that is the point, and the lower number is the more
   honest one to report.
