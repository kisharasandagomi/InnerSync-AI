# Local Data Triangulation

**Status**: descriptive analysis of the locally-collected student
questionnaire (n=31), reproducible from code. Not a validation of the
deployed model's accuracy — this document triangulates *which stress
domains students themselves report* against the domain categories already
used throughout this project's recommendation catalogue, as supporting
context for the Phase 8 discussion.

## Methodology

All figures below are generated directly from
[`ml_pipeline/datasets/local_validation/student_responses.csv`](../../ml_pipeline/datasets/local_validation/student_responses.csv)
by
[`ml_pipeline/src/evaluation/local_data_triangulation.py`](../../ml_pipeline/src/evaluation/local_data_triangulation.py).
Run it directly (`python ml_pipeline/src/evaluation/local_data_triangulation.py`
from the repo root, inside the `mainks` environment) to reproduce every
number here; each run also writes a timestamped JSON record to
`ml_pipeline/experiments/`, the same logging pattern used for every other
finding in this project. Regression tests against the checked-in CSV live
in `ml_pipeline/tests/test_local_data_triangulation.py`.

This analysis was originally performed outside the repository in a
separate tool; it was ported into reproducible, logged code so the figures
here are re-derivable rather than asserted.

### Domain coding scheme

Two independently-worded questions in the local survey — a free-text
"biggest factor affecting your stress level" and a fixed-choice "major
personal challenges" question — were each coded into the five domains used
throughout this dissertation for the deployed model's features: academic,
social, environmental, psychological, and physiological (the last merged
with "not represented" for reporting, since physiological causes were rare
in this free-text sample and blank/vague responses are not meaningfully
distinguishable from them at this sample size).

The coding scheme itself is an explicit dictionary in
`local_data_triangulation.py` (`FACTOR_DOMAIN_MAP`,
`CHALLENGE_DOMAIN_MAP`), applied identically to every row by code. The
*judgement* of which domain a given raw response belongs to was made by
reading each response — that judgement call is not something code can
verify — but the scheme it produced is written down in one place, in full,
rather than existing only as an unrecorded manual step. A reader who
disagrees with a specific mapping can see exactly which line to contest.

## Descriptive statistics (n=31)

- **Age group**: 21–23 dominates the sample (26/31), with small numbers in
  18–20, 24–26, and above 26.
- **Gender**: 21 male, 10 female.
- **Year of study**: mostly Year 3 (15) and Year 4 (12).
- **Study hours/day**: "More than 5 hours" (14) and "1–3 hours" (10) are
  the two largest groups.
- **Sleep quality (1–5)**: mean **2.87** — skewed toward the lower half of
  the scale, consistent with `sleep_quality` having been identified
  elsewhere in this project as a strong (in fact leaking) correlate of
  reported stress, per `docs/decisions/ADR.md`'s ADR-003.
- **Exercise frequency**: "1–2 times per week" is the modal response (19/31).

Full distributions (every category, not just the modal one) are in the
logged JSON and reproducible by running the script directly.

## Thematic comparison table

| Domain | Biggest factor (free text) | Major challenges (categorical) |
|---|---|---|
| Academic | 18 (58.1%) | 18 (58.1%) |
| Environmental | 3 (9.7%) | 4 (12.9%) |
| Social | 1 (3.2%) | 4 (12.9%) |
| Psychological | 2 (6.5%) | 0 (0.0%) |
| Physiological / Not represented | 7 (22.6%) | 5 (16.1%) |

**Row-wise agreement**: the two questions independently coded to the same
domain for **20 of 31 respondents (64.5%)**.

### Interpretation

The two questions converge strongly on Academic being the dominant
self-reported stress domain (58.1% on both), which is consistent with the
deployed model's own top-ranked SHAP features including `academic_performance`
and `study_load`. Agreement is weaker outside the academic domain — most
visibly, Social is reported at 3.2% via free text but 12.9% via the fixed
category, and Psychological causes appear only in the free-text question
(6.5%) and not at all in the fixed-choice one. This is a plausible and
common triangulation finding rather than a contradiction: free text and a
constrained category list are different instruments and are not expected
to agree perfectly, and the fixed "major personal challenges" list did not
offer a psychological-framed option for a respondent to select. The 64.5%
row-wise agreement rate is itself the headline triangulation statistic —
moderate convergence between two independently-worded measures of the same
underlying construct, at this sample size.

## Limitations

n=31 from a single institution's convenience sample. The domain-coding
judgement is a single researcher's reading of each response, not
inter-rater-checked. These figures describe what this specific sample
reported, not a validated claim about the deployed model's real-world
accuracy — see `docs/governance/model_card.md`'s Limitations section for
that distinction.
