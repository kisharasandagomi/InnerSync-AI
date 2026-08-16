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

This component produces a recommendation for a **single point-in-time
assessment**. It holds no memory, no notion of a previous check-in, and no
engagement signal.

The Adaptive Recovery Framework (Module 8 Component 5 — changing strategy after
N ignored recommendations) is deliberately not implemented, because it requires
engagement history across multiple check-ins and therefore the backend
user-history tables that do not yet exist. The boundary is stated in the
`engine` module docstring and recorded in every log entry as
`adaptive_recovery_applied: false`, so a later evaluation cannot mistake
point-in-time output for adaptive behaviour.

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
