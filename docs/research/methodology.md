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

## Data Quality / Leakage Finding

This section documents a methodological event, in the order it actually
happened. The original comparison and its conclusions are deliberately left
intact above — a reader should be able to follow the discovery sequence
rather than see a tidied-up final answer.

**Sequence: original 5-model comparison → SHAP flags `blood_pressure` →
systematic audit of all 20 features → corrected comparison → re-selection.**

### 1. What SHAP surfaced

`04_SHAPAnalysis.ipynb` found `blood_pressure` carrying more than double the
mean |SHAP| of any other feature, despite `01_EDA.ipynb` having recorded it
as the *weakest* linearly-correlated feature (r = +0.394). The two facts are
only reconcilable if the relationship is non-linear, which it is: the mapping
is near-deterministic and non-monotonic (value 1 → moderate stress in 100% of
rows, 2 → low in 100%, 3 → high in 73.8%), fixing the label exactly for 54.5%
of the dataset. Pearson correlation — and therefore the entire EDA heatmap —
is structurally incapable of detecting this.

### 2. Systematic audit of the remaining 19 features

`blood_pressure` was not assumed to be the only affected column.
`02_Preprocessing.ipynb` § Systematic Target-Leakage Audit applies three
tests to every feature: a purity scan, a **single-feature lookup test** (fit
a "most common class per value" rule on the training split, score it on the
held-out test set), and a monotonicity check.

The lookup test is the decisive one, and the result is worse than the
original finding:

| Feature | Lookup-rule accuracy |
|---|---|
| sleep_quality | **0.9045** |
| future_career_concerns | **0.9000** |
| blood_pressure | 0.8864 |
| depression | 0.8818 |
| bullying | 0.8818 |
| anxiety_level | 0.8773 |
| headache | 0.8182 |
| self_esteem | 0.8091 |
| *(remaining 12)* | 0.591 – 0.750 |

Tuned 20-feature Random Forest, for reference: **0.8864**.

`sleep_quality` and `future_career_concerns` each **beat the entire tuned
20-feature model on their own**, from a single ordinal column. Six features
land within 0.01 of it. Every feature shares the same generative signature: a
small near-uniform bucket at value 0 (n = 30–88, behaving like a missing-data
sentinel), with every other value mapping to a single class at 85–100%
purity. A single self-reported 0–5 item cannot genuinely predict another
self-reported item at 90% accuracy across three balanced classes; real
psychological survey data is far noisier. The dataset appears to have been
**generated with features sampled conditional on the label**.

### 3. Removal does not fix it

| Scenario | n features | Accuracy | F1 macro |
|---|---|---|---|
| All 20 (original) | 20 | 0.8864 | 0.8861 |
| Drop `blood_pressure` only | 19 | 0.8773 | 0.8768 |
| Drop 6 leakiest (lookup > 0.85) | 14 | 0.8864 | 0.8865 |
| Drop 8 leakiest (lookup > 0.80) | 12 | 0.8727 | 0.8728 |
| Keep only 6 weakest features | 6 | 0.8500 | 0.8498 |

Chance level for three balanced classes is 0.333. Dropping the three worst
offenders costs **nothing at all**; keeping only the six *weakest* features
still yields 0.85. The label information is redundantly encoded across
essentially every column, so excluding any subset simply shifts the model
onto the next available proxy. **Feature removal is not a viable remedy for
this dataset.**

### 4. Corrected comparison and re-selection

The full comparison was nonetheless re-run with all six rivalling features
excluded (14 remaining), holding split, CV strategy, search grids and tuning
objective identical so the before/after is apples-to-apples. Model selection
was re-derived from scratch rather than carried over.

| Model | Accuracy | F1 macro | ROC-AUC | CV→test gap |
|---|---|---|---|---|
| Logistic Regression (baseline) | 0.8773 | 0.8773 | 0.9520 | — |
| **Random Forest (re-selected)** | **0.8818** | **0.8815** | **0.9838** | **−0.0075** |
| XGBoost | 0.8727 | 0.8726 | 0.9807 | +0.0125 |
| SVM | 0.8773 | 0.8776 | 0.9138 | +0.0078 |
| LightGBM | 0.8727 | 0.8725 | 0.9821 | +0.0127 |

Random Forest was re-selected on the same criteria as before — highest
ROC-AUC (0.9838), highest F1, the only candidate with a *negative* CV-to-test
gap (the healthy pattern; the other three all scored higher in CV than on the
held-out set), and TreeSHAP compatibility. It did not win on accuracy alone,
consistent with `CLAUDE.md`.

Excluding six features cost Random Forest **0.0046 accuracy** — which is the
finding, not a reassurance.

### 5. SHAP on the corrected model

The v2 global ranking is led by `social_support` (0.0558), `basic_needs`
(0.0510) and `academic_performance` (0.0495) — a **social/environmental and
academic** profile, replacing v1's artifact-driven physiological lead. All 13
features carrying a pre-stated directional prior matched expectation; zero
anomalies. The model's reasoning is directionally coherent with the wellbeing
literature, and now closer to what Chapter 2 would predict — but this
coherence describes reasoning over a compromised dataset and is not evidence
of real-world validity.

### 6. Relationship to the Tariq et al. (2025) retraction

Chapter 2 discusses the retraction of a comparable published study in this
exact problem space, on data-integrity grounds. That discussion was, until
now, an argument taken from the retraction notice — a reason to be careful in
principle.

It is no longer second-hand. The same category of defect has been
**independently identified and quantified in this project's own benchmark
dataset**, by this project's own pipeline, using evidence generated here
rather than reported elsewhere. This changes the standing of that Chapter 2
material: it moves from cited background to a directly corroborated
methodological hazard, demonstrated on data from the same family.

Two consequences for the write-up:

1. The retraction discussion should be cross-referenced to this section, and
   framed as **confirmed by independent replication of the failure mode**,
   not merely cited.
2. It sharpens the research-gap argument. The gap is not only that prior work
   lacked accessible explanations and adaptive recommendations — it is that
   **published work in this space has repeatedly failed to detect target
   leakage in its own training data**, and that an explainability-first
   pipeline catches what correlation-based EDA and headline accuracy do not.

### 7. Standing of all reported figures

No accuracy figure computed on this dataset — original or corrected — may be
presented as evidence of real-world stress-prediction capability. The
corrected run is reported as *evidence that removal does not work*, not as a
repaired result. The Phase 8 externally-collected validation set is therefore
no longer a strengthening step: it is the only route by which this project
can make any empirical claim about genuine predictive performance.

What survives intact, and should be argued positively: the pipeline, the
evaluation protocol, and the explainability layer all functioned correctly.
The SHAP analysis detected a data defect that VIF, correlation analysis,
cross-validation and held-out testing had all passed over. That is a
substantive methodological result in its own right.

## Human-Centered Explanation Generator (Component 2)

Converts the SHAP attribution for a single prediction into a short paragraph a
student can read and act on. Implemented as reusable code in
`ml_pipeline/src/explainability/` (templates and generation logic separated),
exercised in `06_ExplanationGenerator.ipynb`.

### Design

Two stages, matching the pipeline mandated by
`.claude/skills/explainable-ai/SKILL.md` (technical explanation → human-centred
translation):

1. `extract_top_factors()` ranks features by |SHAP| and selects the top 3–4,
   assigning each a direction and a plain-language phrase.
2. `assemble_explanation_paragraph()` composes those phrases into 3–5
   sentences: an opening naming the overall picture, the pressures that stood
   out, anything working protectively, and a closing framing the result as a
   changeable snapshot rather than a verdict.

**Direction is taken from the SHAP sign with respect to the high-stress class**,
not from the raw feature value. Using one consistent axis keeps "raising" and
"easing" meaningful whichever class was predicted, and guarantees the stated
direction is derived from the model's actual attribution rather than from an
assumption about what a high or low value ought to mean.

Templates cover all 14 v2 features in both directions (28 phrases). Every
phrase is hedged ("appears to", "seems to be") because the model produces a
probabilistic estimate and the language should not claim more certainty than
the model has.

### Safety gate

`validate_user_facing_text()` rejects any generated string containing clinical
vocabulary from `ethical_framework.md`'s avoided list (diagnosis, cure,
treatment, disorder, condition, symptom, …) or ML terminology (SHAP, feature,
importance, model, prediction, weight, …). It raises rather than warning,
satisfying `IMPLEMENTATION_RULES.md`'s requirement that a change exposing a
SHAP value or feature name to a user must stop rather than pass silently.

Matching uses word boundaries with an inflection suffix (`\bterm\w*\b`) rather
than substring containment. This was not a theoretical refinement: naive
substring matching rejected a legitimate phrase because "secure" contains
"cure", while the boundary form still catches "treatment" and "treated" from
the stem "treat".

### Why templates rather than an LLM call

Templates were chosen for this specific component, and the trade-off is worth
stating explicitly because it goes the opposite way elsewhere in the system
(the chatbot layer does use an LLM).

*In favour of templates*: output is **deterministic**, so the same SHAP input
always yields the same text and the faithfulness check is exactly reproducible
— a requirement for the Phase 8 evaluation. It is **auditable**: 28 phrases can
be read in full and signed off against the approved/avoided vocabulary list,
which is not possible for an open-ended generator. It is **guaranteed** never
to emit clinical language or SHAP internals, because the vocabulary is fixed in
advance rather than constrained by prompt instructions that a model may not
follow. It has **zero inference cost and no latency**, and introduces no
third-party data-sharing question for text derived from sensitive wellbeing
data — relevant to the privacy commitments in `ethical_framework.md`.

*Against templates*: the output is **less natural** and more repetitive across
students than an LLM would produce, and it **does not adapt** to phrasing,
tone, or context beyond the branch structure written into it. With 14 features
and a fixed sentence skeleton, two students with similar profiles receive
near-identical text.

*Judgement*: for the component whose single job is to not leak clinical or
technical language into a vulnerable user's hands, a guarantee is worth more
than fluency. An LLM would be more pleasant to read but would convert a
hard constraint into a probabilistic one, and every such generation would need
its own safety check anyway — at which point the check, not the model, is doing
the load-bearing work. A hybrid (LLM rephrasing of template output, gated by
the same validator) is a reasonable future extension and is noted as such
rather than attempted here.

### Faithfulness logging

Every generated explanation carries a record — feature, raw value, signed SHAP
contribution, chosen direction, resulting phrase, and the share of total
|SHAP| the explanation accounts for — written to
`ml_pipeline/experiments/faithfulness_log_*.jsonl`. The record is never
surfaced to a student. It exists so the plain-language text can later be
audited against the attribution it claims to describe, which is the
"faithfulness" criterion in the XAI skill and a prerequisite for evaluating
explanation quality with real users in Phase 8.

On the four local cases, all 16 selected factors had stated direction matching
SHAP sign (0 mismatches), and explanations accounted for 42–79% of total
|SHAP| magnitude.

### Choice of SHAP axis (investigated, not assumed)

`shap_values` is `(n_samples, n_features, n_classes)`, so generating an
explanation requires choosing which class column to read. The first
implementation always used the **high-stress column**, which produced an
incoherent result for mid-scale predictions: a student predicted moderate
received an explanation consisting only of protective factors, contradicting
the opening sentence that named a moderate level. This was initially recorded
as an inherent property of explaining three classes on one axis. That was
wrong, and the investigation below corrected it.

Three candidate axes were compared on the four local cases, counting how many
of the top four factors were labelled "raising":

| Axis | low pred | moderate pred | high pred |
|---|---|---|---|
| (a) high-stress column only | 0/4 | **0/4** | 4/4 |
| (b) the predicted class's own column | **4/4** | 4/4 | 4/4 |
| (c) severity, `SHAP(high) − SHAP(low)` | 0/4 | **2/4** | 4/4 |

- **(a)** describes only distance from the top of the scale, so for a moderate
  prediction nearly every contribution is negative and the explanation
  degenerates to an all-protective list.
- **(b)** — the intuitive fix — is worse, and fails in a way worth recording.
  A positive SHAP value for the predicted class means "pushed toward this
  outcome", *not* "increased stress". For a low-stress prediction every strong
  contributor is therefore positive, so this axis would report met basic needs
  and strong academic performance as **raising** the student's stress. The
  semantics invert at the calm end of the scale.
- **(c)** measures movement toward the severe end relative to the calm end,
  respecting the ordering of the target. It resolves to all-easing at the low
  end and all-raising at the high end, while giving mid-scale predictions a
  genuine mix.

**(c) was adopted**, implemented as `severity_contributions()`. After the
change, the moderate case surfaces two pressures (strained relationships with
teaching staff, unmet day-to-day essentials) alongside two protective factors
(manageable activities outside study, low peer pressure) — a coherent account
of why the model placed that student in the middle rather than at either end.

**Generalisable point for the dissertation**: this is not specific to this
dataset or model. Any SHAP explanation over an **ordinal** multi-class target
faces the same choice, and the two obvious options are both wrong — one
degenerates at the middle of the scale, the other inverts at the ends.
Collapsing to a signed severity axis across the extreme classes is the general
remedy, and is worth stating as a methodological contribution of the
explainability component rather than an implementation detail.

## Personalized Recommendation Engine (Component 4)

Maps the contributing factors already computed for the explanation onto
concrete, prioritized actions. Implemented in `ml_pipeline/src/recommendation/`
(catalogue separated from selection logic), exercised in
`07_RecommendationEngine.ipynb`.

### Shared input with the explanation generator

The engine consumes the **same `ExplanationFactor` list** the explanation
paragraph was built from — the severity-axis contributions described above, not
a fresh computation. This is a deliberate coupling: if the two components
derived their own factor rankings independently, a student could read that
teaching-staff relationships are straining them and then be advised about
something else entirely. On the four local cases, all 8 generated
recommendations traced back to a factor named in that student's own
explanation (0 untraceable).

### Prioritization logic

1. **Raising factors only.** A protective factor needs acknowledging, not
   fixing; recommending an action against something already working would be
   incoherent.
2. **Severity floor (0.0200).** Derived, and honestly bounded — see below.
3. **Rank by severity magnitude**, strongest first.
4. **Cap at three.** Three actions is already a lot to receive at once; more
   reads as a to-do list and reliably gets ignored — which would additionally
   corrupt the engagement signal the Adaptive Recovery Framework will later
   depend on. This directly implements `CLAUDE.md`'s prohibition on generic
   recommendation dumps.

Observed behaviour across the four cases: low → 0 raising factors → affirmation;
moderate → 2 actions; high → 3 actions (capped from 4 qualifying); misclassified
→ 3 actions.

### Deriving the severity floor — and what it does not do

The floor was initially a bare constant. It is now derived from the observed
distribution of |severity| across the entire held-out test set (220 students ×
14 features = 3,080 attributions), computed in `07_RecommendationEngine.ipynb`:

| percentile | \|severity\| |
|---|---|
| p10 | 0.0086 |
| **p25** | **0.0200** |
| p50 | 0.0498 |
| p75 | 0.0846 |
| p90 | 0.1331 |

The floor is set at the **25th percentile (0.0200)**. The quartile is the choice
being made; the round number is a coincidence of this dataset rather than the
reason for the value.

**The threshold does not currently bind, and this is stated rather than
glossed.** Across the same test set, 430 raising factors reach the top-4
selection and **none** falls below 0.0200 — the smallest |severity| among all
top-4 factors is 0.0346. In other words, the top-4 ranking already excludes
everything the floor would have excluded.

Two consequences follow, both worth being precise about:

1. The floor functions as a **guard rail for out-of-distribution input**, not as
   an active filter. It exists so that a student whose attributions are
   uniformly small — a profile unlike anything in this dataset, or a future
   model with flatter attributions — receives an affirmation rather than an
   action constructed from noise. On this data it is inert.
2. The affirmation observed for the low-stress case is caused by that student
   having **no raising factors at all**, not by the floor. An earlier draft of
   this section implied the floor was doing that work; it was not.

The threshold was deliberately *not* raised until it visibly excluded
something. Tuning a parameter until it appears to earn its place is exactly the
kind of unjustified choice this section exists to avoid, and the honest position
is that the top-4 cap is doing the selection work while the floor covers a case
this dataset does not contain.

### When nothing warrants an action

An engine that always produces recommendations will invent problems. Where no
factor is both raising and above the severity floor, the engine returns a
class-appropriate **affirmation** instead of an action list.

The three affirmations differ by predicted class, and the high-stress variant is
the important one: if a student is under substantial pressure but no single
factor stands out sharply enough to act on, the honest response is to point
toward a person rather than an automated tip. That case routes to university
wellbeing services, consistent with the escalation principle in
`ethical_framework.md`.

### Why rule-based rather than another ML or SHAP step

The alternative would be learning a recommendation policy — but there is no
outcome data to learn from. No student has yet received a recommendation, acted
on it, or reported whether it helped, so any learned policy would be fitted to
nothing, and its errors would be neither predictable nor explainable.

Rule-based selection is also **auditable in the same way as the explanation
templates**: the entire mapping is 14 entries that can be read in full and
reviewed against the approved vocabulary, and every action a student receives
can be traced deterministically to a signed SHAP contribution above a stated
threshold. That traceability is the property the whole framework is built on;
introducing a learned component here would break the audit chain precisely
where a wellbeing intervention reaches a real person.

All recommendation text passes the same `validate_user_facing_text()` gate as
the explanation paragraphs, so clinical vocabulary and ML terminology are
blocked by the same mechanism rather than a parallel one.

### Coverage gap against CLAUDE.md's canonical examples

Two of the four example mappings in `CLAUDE.md` cannot be implemented against
the v2 model, and this is a dataset limitation rather than a design choice:

| Canonical example | Status |
|---|---|
| academic pressure → study planner | Implemented (`study_load`, `academic_performance`) |
| relationship issues → journaling / social support | Implemented (`social_support`, `teacher_student_relationship`, `peer_pressure`) |
| poor sleep → sleep hygiene plan | **Not available.** `sleep_quality` was excluded from v2 as a leaking feature (ADR-003), so the model cannot attribute stress to it and the engine cannot honestly recommend on it. |
| physical inactivity → walking / exercise plan | **Not available.** The dataset contains no exercise or physical-activity field. `extracurricular_activities` measures commitment load, not activity, and is not a substitute. |

Both gaps close if the Phase 8 locally-collected questionnaire includes sleep
and physical-activity items, which is a concrete argument for their inclusion in
that instrument.

### Scope boundary — not the Adaptive Recovery Framework

> **Superseded.** This subsection originally stated the Adaptive Recovery
> Framework was not implemented because the required engagement history and
> backend user-history tables did not yet exist. Both now exist. The
> correction follows the same convention as other superseded claims in this
> project (see `ADR.md` ADR-003 on the v1 → v2 model): retained and marked
> rather than silently rewritten, so the discovery sequence stays legible.
> Current status is documented in full in § Adaptive Recovery Framework
> (Component 5) below.

This component produces a recommendation for a **single point-in-time
assessment**. It holds no memory, no notion of a previous check-in, and no
engagement signal — nothing about that is different after the Adaptive
Recovery Framework was added; the framework wraps this component's output
rather than changing it.

Every recommendation log entry still stamps `adaptive_recovery_applied` —
`false` for every plan this component produces on its own, since it has no
way to detect the patterns the framework looks for. That flag is set to its
real value one layer up, in `backend/app/services/adaptive_recovery.py`.

## Adaptive Recovery Framework (Component 5)

Module 8 Component 5 — changing recommendation strategy after recommendations
have gone repeatedly unheeded across consecutive check-ins, and escalating
toward university wellbeing services when elevated stress persists regardless
of engagement. Implemented in `backend/app/services/adaptive_recovery.py`,
wired into `assessment_service.py` immediately after the point-in-time plan
(§ Personalized Recommendation Engine, above) is built, and exercised by
`backend/tests/test_adaptive_recovery.py`.

**Why this lives in `backend/`, not `ml_pipeline/src/recommendation/`,
despite ADR-001's boundary on training-only code:** the decision logic fits
nothing, so ADR-001's letter does not forbid either location, but its spirit
does — this component's input is live, per-user database history, a concept
the research world's static-dataset notebooks have no notion of, and putting
it in `ml_pipeline/` would mean importing SQLAlchemy sessions into the
research package. Recorded formally as `ADR.md` ADR-004; this section covers
the four decisions specific to *how* it was built, not *where*.

### Catalogue restructuring: one template per feature → `[primary, alternate]`

`ml_pipeline/src/recommendation/catalogue.py`'s `RECOMMENDATION_CATALOGUE`
changed shape from `dict[str, RecommendationTemplate]` (one template per
feature) to `dict[str, list[RecommendationTemplate]]` (`[primary, alternate]`
per feature). This is a **breaking change to research-world code**, made
solely so the Adaptive Recovery Framework has a genuinely different
suggestion to switch to when a factor's primary recommendation has already
been shown across consecutive check-ins without engagement — without
duplicating catalogue content in `backend/`, which would let the two copies
drift.

The change is breaking in the literal sense (every caller indexing the old
`dict[str, RecommendationTemplate]` shape would break), but not in its
observable output: `engine.py`'s point-in-time path was updated to read
`RECOMMENDATION_CATALOGUE[feature][0]` — the primary template — and nothing
else about its selection logic changed. This was verified, not assumed:
`backend/tests/test_assessments.py`'s existing fixtures (predating the
Adaptive Recovery Framework) assert the exact recommendation titles,
actions, and rationales returned for a fixed input, and those assertions
pass unchanged against the restructured catalogue — the point-in-time
output is byte-identical before and after. Each alternate was also written
to use a genuinely different mechanism from its primary (e.g. asking someone
else's perspective instead of self-reflection), not a reworded copy of the
same suggestion, so a student who reaches the switched recommendation is
offered something meaningfully different, not the same advice restated.

### Engagement granularity: the previous check-in's top driver, not per-factor tracking

`previous_engagement` is collected once per submission — a single
self-reported value (`yes` / `partially` / `no` / `no_previous_checkin`) —
not one value per recommended factor. The factor-switch rule
(`decide_adaptive_strategy` in `adaptive_recovery.py`) therefore interprets
"engagement with it" as **engagement with the immediately preceding
check-in's recommendation plan as a whole**, applied specifically to whether
that plan's top-ranked (priority-1) factor repeats as the current check-in's
top-ranked factor.

This is a **stated scope decision**, not an implementation detail to be
reverse-engineered from the code later. The alternative — tracking
engagement separately per recommended factor — was not adopted because the
data does not support it: the system asks one engagement question per
check-in, not one per recommendation shown, so there is no per-factor signal
to track. Reading a single engagement value as applying to the plan's
leading recommendation is the most defensible mapping available given that
constraint, since the priority-1 recommendation is the one the student is
most likely to have acted on (or not) if they engaged with the plan at all.
A future instrument that collected per-recommendation engagement
(e.g. "did you try suggestion 1? suggestion 2?") would make a genuinely
per-factor rule possible, and would be a natural extension — but is not
something the current data collection supports, so building the rule as if
it were would be inventing a signal the system does not have.

### `HISTORY_LOOKBACK_LIMIT = 10` — a bounded-performance choice, not an empirical one

`fetch_recent_history` caps how many prior check-ins it loads per decision at
10. Unlike the recommendation engine's severity floor (§ Deriving the
severity floor, above), this number was **not** derived from a distribution,
a percentile, or any dataset analysis, and does not need to have been. Both
rules this component checks require at most a streak of 3 (escalation) or 2
(factor switch) consecutive prior check-ins; 10 is simply comfortable
headroom over that requirement, chosen so the query stays a small, constant-
cost `LIMIT` clause on an indexed column (`assessments.user_id`,
`assessments.created_at`) rather than scanning a user's entire history as
their check-in count grows over months of use. Calling this out explicitly
matters because this project otherwise holds itself to justifying constants
empirically (the severity floor being the clearest example) — this one is a
plain engineering bound, and dressing it up as anything more rigorous than
that would misrepresent it.

### `previous_engagement` stored as `String(20)`, not a native enum

`Assessment.previous_engagement` is a plain `String(20)` column, validated
against `EngagementLevel` at the Pydantic schema layer rather than enforced
as a native PostgreSQL `ENUM` type at the database layer. Reasoned in a code
comment on the column itself
(`backend/app/models/assessment.py`): a native Postgres enum makes adding a
future value (e.g. a finer-grained engagement scale) an `ALTER TYPE`
migration against a live column, which is more disruptive than a
`String`-backed column with an added `Literal`/`Enum` member on the
application side. Recorded here so the reasoning is not comment-only, per
`IMPLEMENTATION_RULES.md`'s documentation expectations.

## Conversational Interaction Layer (Module 3)

A Gemini-backed chatbot, `backend/app/chatbot/` (`gemini_client.py`,
`service.py`, `prompts.py`, `sentiment.py`), fronted by
`GET`/`POST /chat/messages` and `frontend/src/pages/ChatPage.tsx`. Persists
to a single new table, `chat_messages` (role, content, timestamp,
`fallback_reason`) — no `Conversation`/session table; continuity is just
chronological order per user, and a session boundary for the turn cap below
is inferred from a gap between timestamps rather than tracked as a
persisted field (see `app/models/chat_message.py`'s module docstring).

### The boundary this component must not cross

**Restated here in the same terms as `CLAUDE.md`, because it is the easiest
rule in this component to violate by accident:** the chatbot does not
perform stress prediction. `app/chatbot/service.py` never imports
`app.ml.predictor`, never calls `StressPredictor.predict()`, and never
touches `Assessment` or `POST /assessments`'s 14-feature contract. This is
not a hypothetical risk avoided by discipline alone — it is the same
conclusion this project already reached empirically in § NLP Feature
Ablation Study, above: Experiments C and D (a model combining structured
questionnaire features with free text from the same subject) cannot run on
any data available to this project, because no such paired dataset exists.
Wiring live chatbot text into the trained Random Forest here would not be
implementing that future work — it would be fabricating the same kind of
cross-subject relationship Experiments C/D's section explicitly documented
as a worse methodological error than the target-leakage problem in ADR-003,
just done to a live user's own data instead of two different research
subjects. The chatbot's sole relationship to the prediction pipeline is that
both exist in the same product; there is no data path between them.

### Safety: reusing the gate, not rebuilding it

Every Gemini reply is checked by the **same** `validate_user_facing_text()`
gate that guards the explanation and recommendation text (§ Human-Centered
Explanation Generator, above), imported directly from
`ml_pipeline.src.explainability.generator` rather than re-implemented. This
was a deliberate reuse decision: a second implementation of the
avoided-vocabulary list would inevitably drift from the first, and an LLM's
free-form output is exactly the case this gate was built to catch — unlike
the template-based explanation generator, Gemini's output cannot be
guaranteed safe by construction, so it needs the same runtime check applied
to unpredictable text.

A reply that fails the gate is **not retried**. `_get_validated_reply()` in
`service.py` decides once and substitutes a fixed canned reply
(`SAFETY_FALLBACK_REPLY` in `app/chatbot/prompts.py`), persisted like a
genuine turn so the conversation stays coherent, tagged
`fallback_reason="safety_gate_rejected"` for audit. The rejected raw draft
is never persisted anywhere, never logged, and never reaches the student in
any form — verified directly in
`backend/tests/test_chatbot.py::test_safety_gate_catches_and_replaces_an_unsafe_reply`,
which engineers a deliberately diagnostic-sounding Gemini draft and asserts
neither the response body nor the persisted row contains it.

The system prompt (`SYSTEM_PROMPT` in `prompts.py`) independently instructs
Gemini toward the same rules — warm and supportive tone; never diagnose or
name a condition; never use clinical vocabulary; never estimate or state a
stress level, since that is the prediction pipeline's job, not the
chatbot's; clarify early that this is an AI check-in, not a counsellor; and
escalate calmly toward university wellbeing services on anything that sounds
urgent. The prompt and the gate are deliberately two independent layers,
not one relying on the other: the prompt reduces how often the gate needs to
intervene, but the gate is what actually guarantees the boundary, since a
prompt is a request to the model, not an enforceable constraint on it. The
"AI check-in, not a counsellor" disclaimer additionally does not rely on the
model remembering to say it at all — `ChatPage.tsx` always renders a fixed,
non-LLM, non-persisted introductory bubble stating this before any real
conversation turn, so the disclaimer is guaranteed regardless of what Gemini
does.

### Cost and rate-limit safety

Two independent mechanisms, for two different risks:

1. **`MAX_TURNS_PER_SESSION` (30).** Caps how long one inferred session can
   run before the student is told, in-conversation, that they have reached
   the limit and pointed toward university wellbeing services — checked
   before any Gemini call is made, so an exhausted session costs nothing
   further. This guards against one runaway conversation consuming a
   disproportionate share of the free tier's per-minute budget, not a claim
   about how long a supportive conversation should be.
2. **Graceful handling of Gemini's own HTTP 429.** A rate-limit response
   from Gemini itself is caught and replaced with a fixed, calm
   in-conversation reply (`RATE_LIMIT_FALLBACK_REPLY`), never a raw error
   surfaced to the student.

A third, unrelated failure mode is handled differently on purpose: an
invalid or revoked `GEMINI_API_KEY` (Gemini's HTTP 401/403) is treated as a
**configuration** problem, not a runtime one — it propagates as
`ChatConfigError` and surfaces as an HTTP 503 with an explicit detail
message, exactly like a wholly missing key. Per `CLAUDE.md`, papering over a
missing or invalid key with a hardcoded fallback reply would hide a real
deployment problem behind what looks like normal chatbot behaviour; this
component refuses to do that.

### Sentiment logging (supplementary, non-model-facing)

`app/chatbot/sentiment.py` scores each student message with the same VADER
and TextBlob lexicons already built for Experiment B (§ NLP Feature Ablation
Study), reusing `ml_pipeline/src/nlp/lexicon_scores.py` directly. This is
descriptive evidence-gathering only, in the same spirit as the faithfulness
logging elsewhere in this system: the scores are never returned to the
student, never fed into any model, and never influence the chatbot's reply.
Best-effort — a scoring failure is caught and logged, never allowed to break
a chat turn.

The raw message text is deliberately never logged, only the four derived
numbers (`vader_compound`, `textblob_polarity`, `textblob_subjectivity`,
plus `vader_neg`/`neu`/`pos` internally). `ethical_framework.md`'s Risk
Mitigation table names "no plaintext sensitive fields in logs" as the
standing mitigation for a data breach, and a student's own wellbeing-chat
text is precisely the sensitive field that protects.

## Chat-Driven Check-In Delivery

A UX change, based on direct user feedback: the chat interface
(`frontend/src/pages/ChatPage.tsx`) is now the primary way a student
completes a check-in, asking the same 14 `feature_schema.json` questions one
at a time as sequential chat messages, instead of requiring the slider form
up front. This is a **delivery-layer change only** — `POST /assessments`,
its 14-feature contract, the ML pipeline, SHAP, the explanation generator,
the recommendation engine, and the safety gate are all unchanged.

### The LLM has no role in capturing answers

Each question is answered through a bounded quick-select control rendered
inside the chat bubble — never free text interpreted by Gemini into a
value. This is the same "no LLM in the prediction path" discipline
documented for the chatbot itself (§ Conversational Interaction Layer,
above) and the same reasoning behind the NLP ablation study's conclusion (§
NLP Feature Ablation Study, Experiments C/D): this project has spent real
effort establishing that a value feeding the trained model must be precise
and verifiable, not inferred from language. Letting an LLM interpret "yeah
pretty rough tbh" into a `study_load` value would reintroduce exactly that
risk for a 14-feature contract that has otherwise never taken free text as
input.

**Round 2 (direct user testing feedback): three widget styles, not one.**
`frontend/src/services/checkinPresentation.ts` assigns each of the 14
fields a widget style — slider, chip row, or an icon/emoji scale — purely a
rendering choice, kept entirely separate from `checkinFlow.ts`. Every style
still ends by calling the same `onAnswerFeature(value: number)`, validated
identically against that field's own `[min, max]` regardless of which
widget produced it; `checkinPresentation.test.ts` asserts this holds for
every field's min, midpoint, and max value under its assigned style. The
assignment is grouped by what each question is actually asking (documented
in full in that module): magnitude/quantity questions get a slider,
subjective/emotional-register questions ("how safe do you feel", "how
supportive are your teaching staff") get a face/mood icon scale — with the
icon sequence's direction matched to that field's own `lowLabel`/
`highLabel` rather than assumed, since some fields improve toward their low
end (`headache`) and others toward their high end (`safety`) — and
concrete/countable/binary questions keep the chip row. No points, streaks,
or scores are introduced anywhere in this — the goal was interaction
variety, not gamifying a wellbeing check-in.

The state machine driving the flow — `frontend/src/services/checkinFlow.ts`
— is deliberately pure and has no dependency on React, Gemini, or the chat
transport, mirroring how `featureSchema.ts` is the single source of truth
the slider form already used. Both paths call the same
`FEATURE_FIELDS`/`submitAssessment`; `checkinFlow.test.ts` asserts the
chat-driven payload is identical in shape (14 keys, schema order, each
value validated against that field's own bounds) to what the slider form
has always produced, the same "guard the contract" pattern already used for
`featureSchema.test.ts` and the assessment-history endpoint tests.

### Free-form chat stays a separate, explicitly chosen mode

`ChatPage.tsx` presents "Start a check-in" and "Just talk" as two distinct
entry points (a menu screen when no mode is pre-selected via navigation
state), never blended into one conversation while a check-in is in
progress. Free-form chat continues to never feed into the model, per the
boundary in § Conversational Interaction Layer above — this UX change does
not touch that boundary in either direction.

**Round 2: automatic hand-off to free-form chat after results.** Direct
user testing found the check-in felt like it dead-ended once results
appeared. `ChatPage.tsx` now unifies both modes onto one local message
list, so `mode` controls only which *input* is active (the bounded
quick-select control mid-check-in; free text once it's done), not which
messages are visible — completing a check-in transitions `mode` to `"talk"`
automatically, in the same thread, with no restart and no navigation. The
transition is one-directional and inert with respect to the boundary above:
it changes what UI element accepts the next keystroke, not what any message
is used for. A message sent after this point is still a normal
`POST /chat/messages` call, still never touches `Assessment` or the model.

### Discussing a student's own past result in free-form chat

**Round 2, another piece of direct user feedback**: a student asking "why
did it say I was stressed?" in free-form chat previously got a reply
admitting the bot had no access to their results at all — accurate under
the original design, but an obviously worse experience than the system
being capable of supporting. `app/chatbot/service.py`'s
`_fetch_recent_explanation` now reads exactly one field — the caller's own
most recent `ExplanationRecord.paragraph` — and `prompts.py`'s
`build_system_instruction` folds it into the Gemini system instruction as
context, only when present.

This is a **read-only, one-directional** addition, not a weakening of the
Module 3 boundary: the explanation text already passed
`validate_user_facing_text()` once, when it was generated for the results
screen, and flows only *into* a prompt, never back into anything that
predicts, trains, or writes to the assessment tables. No SHAP value,
feature name, or numeric score is read, because none is available to
read — the query selects `ExplanationRecord.paragraph` alone. The **same**
safety gate still checks the model's actual reply before it reaches the
student, exactly as for every other chat turn; nothing about this addition
touches that check. The system prompt is also updated to say plainly that
it must state only what the provided summary says and never volunteer a
"score"/"level"/"prediction" framing while discussing it — see
`SYSTEM_PROMPT` in `prompts.py`. Tests scope this per-user
(`test_chat_context_is_scoped_to_the_authenticated_caller`) and confirm no
technical vocabulary reaches the prompt
(`test_chat_context_never_carries_shap_or_feature_vocabulary`).

### Result delivery

On completion, the response from `POST /assessments` — explanation
paragraph, then recommendations (or an affirmation, or an escalation) — is
rendered as sequential chat bubbles using the returned text verbatim, the
same "never re-word text that already passed the safety gate" rule
`ResultsPage.tsx` has always followed for the slider-form path.

### The slider form is kept, not replaced

`AssessmentPage.tsx` (`/assessment`) is unchanged and fully functional —
confirmed with the project owner rather than removed or unilaterally
demoted. It is surfaced as a small, low-emphasis link ("Prefer the classic
form?") from the new landing page (`LandingPage.tsx`, the default authed
route at `/`) rather than as the promoted path, since chat is now the
primary way to start a check-in.

## Personalized Greeting

Round 3. `display_name` (optional, collected once at registration —
`backend/app/models/user.py`, on `users` rather than `user_profiles` since
it's a display/identity attribute like email, not a demographic fairness
field) personalises the chat check-in's opening line. Resolution — the
student's own name if set, else the local part of their email, never blank
or broken — is implemented twice, deliberately: `resolve_greeting_name` in
`backend/app/schemas/auth.py` and `resolveGreetingName` in
`frontend/src/services/greeting.ts`, both covered by tests, so the
"never blank" guarantee is verified on both sides of the boundary rather
than trusted to whichever one actually renders the text. The greeting
itself — `"Hi {name}, ready for your check-in?"` — is a fixed template
(`checkinGreeting` in `greeting.ts`), not an LLM generation, consistent with
every other piece of deterministic, safety-relevant text in this system.

## Comparative Trend Message

Round 3. After a check-in with at least one prior result, a short message
compares this result's severity to the immediately previous check-in —
`backend/app/services/comparative_trend.py`. Three outcomes
("improved"/"same"/"worse"), each a fixed template run through the existing
`validate_user_facing_text()` gate, same as every other generated string in
this system. Hedged language throughout: "a bit lighter", not "improved by
X%"; "be gentle with yourself", not a diagnosis or a verdict.

**Reuses the Adaptive Recovery Framework's own history data, not a second
query.** `assessment_service.create_assessment` calls
`adaptive_recovery.fetch_recent_history` once and passes the same list to
both `plan_with_adaptive_recovery` (refactored this round to accept that
history as a parameter, rather than fetching it internally) and
`determine_comparative_trend`.

**Escalation coordination.** Escalation (3+ consecutive check-ins at the
highest severity class) can only fire when the immediately previous
check-in was *also* at that class, so the raw ordinal comparison is always
"same" whenever escalation fires — a structural fact, not a coincidence
relied upon implicitly. `determine_comparative_trend` takes `is_escalation`
as an explicit input regardless: when true, it always returns
`COMPARATIVE_ESCALATION_COORDINATED_MESSAGE` — a short, factual, secondary
note — rather than the standard "same" message, so nothing here ever reads
as competing with or duplicating the escalation signpost's own supportive
framing. The true ordinal outcome is still computed and persisted
(`Recommendation.comparative_trend_outcome`) for audit even when the
*message* shown differs from what that raw outcome would otherwise imply.
Both frontend rendering paths (`ChatPage.tsx`'s `resultMessages`,
`ResultsPage.tsx`) place this message last, after any escalation
signpost/affirmation/recommendations — visually secondary, matching its
backend-coordinated content.

## Hobby-Personalized Recommendations

Round 3. An optional `hobby` field (`user_profiles.hobby`, collected once at
registration alongside `display_name`) lets exactly one existing
recommendation template — `mental_health_history`'s primary, "Return to
something that helped before" — reference it:
`ml_pipeline/src/recommendation/catalogue.py`'s `RecommendationTemplate`
gained an optional `hobby_action_template` field (a string with one
`{hobby}` placeholder), populated only for that one template. Chosen
because its existing generic phrasing is already about returning to a
helpful routine, which a hobby is a direct, concrete example of — not
retrofitted onto a thematically unrelated template.

**Stays inside the existing rule-based, SHAP-traceable architecture.** The
chatbot has no role in generating or selecting this text; `hobby` is a
profile field the student explicitly set, read once by
`assessment_service._fetch_hobby` and passed into
`build_recommendation_plan`, which still only ever selects from
`RECOMMENDATION_CATALOGUE` entries tied to an actual contributing factor —
exactly as before. Extending this to any other template is possible but
was deliberately not done broadly this round; one clearly-fitting template
is worth more than several loosely-fitting ones.

**Safety.** A student's own `hobby` text is free-form (bounded to 80
characters at the schema layer, but not itself vocabulary-gated at write
time) — so `engine._resolve_action_text` runs the interpolated text through
`validate_user_facing_text()` before using it, and falls back silently to
the template's own static, catalogue-reviewed `action` text if that check
ever fails, rather than raising. A personalisation nicety must never be
able to break a check-in result.

## Progress Monitoring Dashboard (Module 9/10)

A read-only trend view over a student's own check-in history, backed by
`GET /assessments/history` (`backend/app/api/assessments.py`) and rendered by
`frontend/src/pages/ProgressPage.tsx`. Reuses data already persisted by every
prior component — `Assessment.predicted_class`, `Assessment.previous_engagement`,
`Recommendation.adaptive_recovery_applied`/`is_escalation`, and the rank-1
entry of `ExplanationRecord.faithfulness_factors` — so this component adds no
new write path and no new database table.

**Round 2 (direct user testing feedback): expandable per-entry detail.**
`top_factor_phrase` alone read as too thin a summary per check-in. Each
history item now also carries `explanation` — that check-in's full
`ExplanationRecord.paragraph`, the exact text the student already read on
the results screen at the time, added to `AssessmentHistoryItem` as one
more already-safety-gated field read off the same already-joined row (no
new query). `ProgressPage.tsx`'s `HistoryEntry` shows `top_factor_phrase` by
default and reveals `explanation` behind an explicit "Show the full
explanation" toggle — reused verbatim, never regenerated or reworded.

### Why trend framing, not raw numbers

The same explainability principle that governs every other student-facing
surface in this system (§ Human-Centered Explanation Generator, above; see
also `.claude/skills/explainable-ai/SKILL.md`) applies here without
exception: a student never sees a SHAP value, a feature name, or a raw
severity score, and that discipline does not relax just because the content
is now a history of several check-ins instead of one. A dashboard is
arguably a *higher*-risk surface for this than a single result screen — it
is easy to design a trend chart that reads as a precise clinical instrument
(a line graph with a numeric y-axis, a "your score" figure) purely by
following ordinary dashboard conventions, without anyone intending to
introduce ML terminology or a diagnostic framing.

The design response: `stress_level` (0/1/2) is used only to choose a bar's
height and a fixed word label ("Low"/"Moderate"/"High"), never displayed as
a number, and `top_factor_phrase` is the same pre-approved,
`validate_user_facing_text()`-checked phrase already used inside the
explanation paragraph (§ Human-Centered Explanation Generator), rendered
verbatim rather than re-derived. The one new piece of text this component
introduces — the plain-language trend summary ("things have been trending a
little steadier...") — is generated from a simple comparison over the last
two or three `stress_level` values only, in `ProgressPage.tsx`'s
`summarizeTrend()`, and never states or implies a number.

Colour is deliberately not load-bearing, consistent with `index.css`'s
existing design-token rationale ("colour is never load-bearing for the
stress level, the wording carries it"): the trend bars use one accent hue at
three intensities rather than a red/amber/green severity scale, and every
bar also carries its own word label, so the visual would still be legible
with colour removed entirely.

### `top_factor_phrase`: still the top severity-axis factor, still safety-gated

`GET /assessments/history` returns each check-in's single strongest
contributing factor — the rank-1 entry of that check-in's
`ExplanationFactor` list (§ Human-Centered Explanation Generator's severity
axis) — but only as its already-curated `FEATURE_PHRASES` phrase, never as
the underlying feature name or signed contribution. This mirrors how
`AssessmentResponse` already excludes `feature` from `RecommendationItem`
(`backend/app/schemas/assessment.py`): the response schema for a
student-facing endpoint is held to the same vocabulary discipline as the
explanation text itself, not merely to the discipline applied to the raw
persisted record.

### Read-only by design

The endpoint runs no prediction, explanation, or recommendation logic — it
is a query over rows `POST /assessments` already wrote. This keeps the
dashboard's addition to the system's surface area small and auditable: it
cannot introduce a new source of disagreement between what a student was
told at check-in time and what the dashboard later shows them, because it
is reading the same persisted record back rather than recomputing anything.

## NLP Feature Ablation Study (Experiments A–D) — `05_NLP_Ablation.ipynb`

**Research comparison only.** This section documents an ablation study
produced to inform the dissertation's discussion of whether NLP-derived
features are worth adding to the system. It does not retrain, replace, or
modify the deployed v2 model, `backend/app/`, or the `POST /assessments`
contract, and nothing in `ml_pipeline/src/nlp/` is imported by the backend.
Every run is logged under `ml_pipeline/experiments/` using the same
`log_experiment()` pattern established for the main model comparison.

### The four intended conditions

| # | Condition | Status |
|---|---|---|
| A | Questionnaire only | Reference — the existing, fully-evaluated v2 Random Forest (`03_ModelTraining.ipynb`, `04_SHAPAnalysis.ipynb`). Not retrained here. |
| B | NLP only | Run in this study — TF-IDF + Logistic Regression on Dreaddit. |
| C | Questionnaire + NLP, combined | Not executable on data available today. |
| D | *(reserved: combined + tuning/feature-selection variant)* | Not executable, same reason as C. |

### Why Experiments C and D cannot run on data available today

This is a methodological finding, not a skipped step, and it was not obvious
until checked directly against both datasets' actual contents.

A combined model needs one respondent who supplied **both** a structured
questionnaire response and free text. The Kaggle dataset behind Experiment A
(`student_stress_factors.csv`) has no text field at all. Dreaddit
(Experiment B) has text but none of the 14 questionnaire features. The two
are different people, recruited from different platforms (a student
wellbeing survey vs. Reddit posts across stress-related subreddits), with no
shared identifier connecting any row in one to any row in the other.

**Deliberately not attempted**: pairing a random Kaggle respondent's answers
with a random Dreaddit post's text to manufacture a "combined" row. That
would fabricate a relationship between two unrelated people — a worse
methodological error than the target-leakage problem already documented in
ADR-003 (§ Data Quality / Leakage Finding above), not a workaround for it.
Leakage was an undetected flaw in real data about real respondents;
fabricating cross-subject pairs would be inventing data about a person who
does not exist.

**What would make C and D possible**: the project's own Phase 8
locally-collected instrument (`docs/governance/data_management_plan.md`) is
the only data source that structurally supports this, because it collects
both a Likert-style questionnaire *and* an open-ended free-text prompt
("what's the biggest factor currently affecting your stress?") from the
**same** respondent. C and D are recorded here as a planned future analysis,
contingent on collecting a sufficient number of Phase 8 responses — not as
an abandoned line of work. If they later show NLP features meaningfully
improve on Experiment A once genuinely combined data exists, integrating
that into the deployed pipeline is a separate decision to be made explicitly
with the project owner, not an automatic next step from this study.

### Experiment A — questionnaire only (reference)

Read directly from `ml_pipeline/artifacts/artifact_manifest.json`, not
retrained: Random Forest (v2), 14 features, held-out test accuracy 0.8818,
F1 macro 0.8815, ROC-AUC (macro, OvR) 0.9838. Full detail already documented
above under § Model Selection.

### Experiment B — NLP only

TF-IDF + Logistic Regression, trained and tuned via `GridSearchCV`
(`tfidf__max_features` ∈ {3000, 5000, 10000}, `tfidf__ngram_range` ∈
{(1,1), (1,2)}, `logreg__C` ∈ {0.1, 1, 10}, stratified 5-fold CV,
`f1_macro` objective — same tuning protocol as every deployed-model
candidate, for methodological consistency between the two pipelines, not
because this feeds the deployed model). Trained and evaluated on Dreaddit's
own official train/test split (2,838 / 715 posts), predicting Dreaddit's own
binary stress label. No re-splitting, no relabelling.

Best configuration: `max_features=10000`, `ngram_range=(1,1)`, `C=1.0`
(CV F1 macro 0.7397). Held-out test metrics:

| Metric | Value |
|---|---|
| Accuracy | 0.7007 |
| Balanced accuracy | 0.6989 |
| Precision (macro) | 0.7017 |
| Recall (macro) | 0.6989 |
| F1 (macro) | 0.6989 |
| ROC-AUC | 0.7974 |

These figures are consistent with the range reported in the published
Dreaddit benchmark literature for comparable bag-of-words baselines, which is
a useful sanity check on the pipeline given this is the first time this
project has trained on this dataset.

**Descriptive sentiment scoring** (VADER, TextBlob) — reported to
characterise the text, not used as model features anywhere. Mean scores by
label:

| Label | VADER compound | TextBlob polarity | TextBlob subjectivity |
|---|---|---|---|
| 0 (not stressed) | +0.271 | +0.103 | 0.472 |
| 1 (stressed) | −0.306 | −0.016 | 0.505 |

Both lexicons separate the two classes in the expected direction — stressed
posts score more negatively on both — without any supervised training. This
is a mild positive sanity check on Dreaddit's label quality; it is not a
third ablation condition and was not fed into Experiment B's model.

### Experiment A vs. Experiment B — explicitly not a comparison table

The two are reported side by side for reference only:

| | Experiment A (reference) | Experiment B |
|---|---|---|
| Dataset | Kaggle `student_stress_factors.csv` | Dreaddit (Reddit posts) |
| Population | University student survey respondents | Reddit users, stress-related subreddits |
| Test rows | 220 | 715 |
| Target | 3-class (low/moderate/high) | Binary (not stressed/stressed) |
| Input | 14 Likert-style questionnaire features | Raw post text (TF-IDF) |
| Accuracy | 0.8818 | 0.7007 |
| F1 (macro) | 0.8815 | 0.6989 |

**These numbers must not be read as "questionnaire features beat NLP
features"**, or the reverse. They differ on every axis that would make such
a reading valid: different datasets, different populations, and a different
number of target classes (chance level 0.333 for A vs. 0.5 for B) — a
3-class and a binary F1 score are not the same quantity. The purpose of this
table is to make each result legible next to the other, not to rank them.

### Standing of this study

Consistent with the rest of this document's treatment of the questionnaire
dataset: Experiment A's figures remain provisional pending Phase 8 external
validation (see § Handling the risk of inflated apparent performance).
Experiment B's figures are a first, honest read on Dreaddit and are not
claimed to generalise to this project's own student population, since
Dreaddit's Reddit-user population was never intended to represent it.
