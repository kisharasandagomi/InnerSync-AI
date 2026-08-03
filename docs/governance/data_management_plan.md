# Data Management Plan — InnerSync AI

## Data Sources

1. **Public benchmark dataset**: "Student Stress Factors: A Comprehensive
   Analysis" (Kaggle, rxnach), 1,100 responses, 21 features across
   psychological, physiological, social, environmental, and academic domains.
   Used for model training, testing, and comparison. Provenance limitation:
   self-reported, crowd-sourced, no verifiable physical corroboration of
   physiological fields — used only as a benchmarking/training resource, not
   as the sole evidence base for conclusions about real users.
2. **Locally collected data** (Google Form + in-app questionnaire and
   conversational check-ins): used for external validation and local/research
   discussion, not as primary training data. Collected under the consent
   process defined in `ethical_framework.md`.

## Collection Method

- Structured questionnaire (sleep, academic workload, exam pressure,
  exercise, diet, social interaction, financial pressure, screen time, mood,
  self-rated stress).
- Free-text conversational check-ins, processed via NLP (sentiment, emotion,
  keyword extraction) into structured features.

## Anonymisation

- Each user is assigned a pseudonymous internal ID at registration.
- Direct identifiers (name, email) are stored in the `User` table only;
  behavioural/emotional data is stored against the pseudonymous ID in
  separate tables, minimising the surface where identity and sensitive data
  are directly joined.
- Any data exported for dissertation analysis/appendices is aggregated or
  fully de-identified before inclusion.

## Storage

- PostgreSQL database, access restricted to the application via credentials
  held in environment variables (never committed to git).
- Raw/processed ML datasets kept in `ml_pipeline/datasets/`, excluded from
  version control via `.gitignore`.
- Trained model artifacts (`ml_pipeline/artifacts/`) contain no raw user data,
  only fitted parameters — safe to version if needed for reproducibility,
  though large binaries are still gitignored by default.

## Retention

- Data is retained for the duration of the dissertation project and any
  follow-up evaluation period, then deleted unless the user has separately
  consented to longer retention for research purposes.
- Users may request deletion of their account and associated data at any
  time.

## Access Control

- Only the project author (and supervisor, where required for assessment)
  has access to the raw database during development.
- API access is authenticated via JWT; no endpoint returns another user's
  data.
- No production credentials or real user data are used in local development
  or testing environments — synthetic/sample data only.
