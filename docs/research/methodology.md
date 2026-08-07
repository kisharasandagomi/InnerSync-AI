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
