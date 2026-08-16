"""Phase 3 NLP work — currently the Experiment B ablation only.

**Scope**: everything in this package is research code for the ablation study
comparing questionnaire-only (Experiment A), NLP-only (Experiment B), and
combined (Experiments C/D, not currently executable — see
`docs/research/methodology.md` § NLP Feature Ablation Study) approaches to
stress prediction. Nothing here is imported by `backend/`, and nothing here
retrains, replaces, or otherwise touches the deployed v2 model in
`ml_pipeline/artifacts/`.
"""
