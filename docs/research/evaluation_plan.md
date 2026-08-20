# Evaluation Plan

Working source of truth for Chapter 8 (Evaluation).

## Status

Comparative ML evaluation and SHAP faithfulness checks are documented in
`docs/research/methodology.md`. The Phase 8 human evaluation survey (SUS,
explanation clarity/trust, chatbot, recommendation usefulness) has now been
run with a small participant group and is reported below, reproducibly from
code rather than asserted. Still not populated: a full write-up connecting
these figures back to the research gap and discussing their limitations at
length — this section currently reports numbers, not the finished Chapter 8
narrative. See `PROJECT_ROADMAP.md` Phase 8.

## Phase 8 survey evaluation

**Methodology.** Two linked survey exports —
[`docs/research/phase8_evaluation/survey_part1.csv`](phase8_evaluation/survey_part1.csv)
(n=7; System Usability Scale core items, explanation and chatbot ratings,
overall experience) and
[`docs/research/phase8_evaluation/survey_part2_followup.csv`](phase8_evaluation/survey_part2_followup.csv)
(n=7; the one SUS item moved to a short follow-up form, plus
recommendation-usefulness ratings) — are analysed by
[`ml_pipeline/src/evaluation/phase8_survey_analysis.py`](../../ml_pipeline/src/evaluation/phase8_survey_analysis.py).
Run it directly to reproduce every figure below; each run also writes a
timestamped JSON record to `ml_pipeline/experiments/`, the same logging
pattern used for every other finding in this project. Regression tests
against the checked-in CSVs live in
`ml_pipeline/tests/test_phase8_survey_analysis.py`. This analysis was
originally performed outside the repository in a separate tool; it was
ported into reproducible, logged code so these figures are re-derivable
rather than asserted.

**System Usability Scale — 9-item modification.** The standard SUS is 10
alternating positive/negative items scored 0-100 via a ×2.5 multiplier on a
0-40 raw total. This survey's main form presents 9 of the 10 standard
items; the 10th ("I think that I would need the support of a technical
person to be able to use this system") was moved to the short follow-up
form instead, to keep the main form shorter, and is **not** merged back
into the SUS total — the two forms were separate response sessions, and
folding a follow-up answer into a same-sitting SUS score would overstate
what was measured in one sitting. The scale is adjusted accordingly (9
items × 4 max = 36 raw points, multiplier 100/36 rather than 2.5) to
preserve the 0-100 range; the excluded item is reported separately, not
silently dropped.

| Measure | Result |
|---|---|
| SUS mean (9-item, n=7) | **80.6** |
| SUS median | 80.6 |
| SUS range | 72.2 – 86.1 |
| Excluded item ("need technical support") | mean 1.0/5 — all 7 respondents strongly disagreed |
| Explanation usefulness (5 items, pooled mean) | 4.14 / 5 |
| Chatbot usefulness (2 items, pooled mean) | 3.77 / 5 |
| Recommendation usefulness (4 items, pooled mean, n from part 2) | 3.93 / 5 |
| Overall experience rating | 5.0 / 5 (all 7 respondents) |

**Reading these figures.** n=7 is a small pilot-scale sample, appropriate
for an early usability read but not for a statistically powered claim.
The perfect 5.0/5 overall rating in particular should be read as a ceiling
effect worth flagging rather than evidence the system is flawless —
consistent with `docs/governance/model_card.md`'s general practice of not
over-claiming from a small internal sample.
