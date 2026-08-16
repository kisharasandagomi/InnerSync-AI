/**
 * The model's input contract, mirroring ml_pipeline/artifacts/feature_schema.json
 * for model v2 exactly — same 14 fields, same order, same bounds.
 *
 * Order matters: the backend maps this payload onto a positional feature vector,
 * so a reordered or missing field would silently produce a wrong prediction
 * rather than an error. `FEATURE_FIELDS` is the single source of truth for the
 * form, and `assessment.test.tsx` asserts it still matches the schema.
 *
 * The six features excluded from v2 for target leakage (sleep_quality,
 * future_career_concerns, blood_pressure, depression, bullying, anxiety_level)
 * must NOT be collected here — see docs/decisions/ADR.md ADR-003.
 */

export interface FeatureField {
  /** Must match the backend field name exactly. */
  readonly name: string;
  /** Question shown to the student. */
  readonly label: string;
  /** Short clarifier; keeps the question concrete without clinical framing. */
  readonly help: string;
  readonly min: number;
  readonly max: number;
  /** Labels for the extremes of the scale, so the direction is unambiguous. */
  readonly lowLabel: string;
  readonly highLabel: string;
}

export const FEATURE_FIELDS: readonly FeatureField[] = [
  {
    name: "self_esteem",
    label: "How you have been feeling about yourself",
    help: "0 means very low, 30 means very positive.",
    min: 0,
    max: 30,
    lowLabel: "Very low",
    highLabel: "Very positive",
  },
  {
    name: "mental_health_history",
    label: "Have you experienced ongoing wellbeing difficulties before?",
    help: "This is only used to weight the estimate. It is not a record of anything.",
    min: 0,
    max: 1,
    lowLabel: "No",
    highLabel: "Yes",
  },
  {
    name: "headache",
    label: "How often have you had headaches recently?",
    help: "0 means never, 5 means very frequently.",
    min: 0,
    max: 5,
    lowLabel: "Never",
    highLabel: "Very often",
  },
  {
    name: "breathing_problem",
    label: "Have you had difficulty breathing comfortably?",
    help: "0 means never, 5 means very frequently.",
    min: 0,
    max: 5,
    lowLabel: "Never",
    highLabel: "Very often",
  },
  {
    name: "noise_level",
    label: "How noisy is where you live and study?",
    help: "0 means quiet, 5 means very noisy.",
    min: 0,
    max: 5,
    lowLabel: "Quiet",
    highLabel: "Very noisy",
  },
  {
    name: "living_conditions",
    label: "How would you rate your living situation?",
    help: "0 means poor, 5 means very good.",
    min: 0,
    max: 5,
    lowLabel: "Poor",
    highLabel: "Very good",
  },
  {
    name: "safety",
    label: "How safe do you feel where you spend your time?",
    help: "0 means not at all safe, 5 means very safe.",
    min: 0,
    max: 5,
    lowLabel: "Not safe",
    highLabel: "Very safe",
  },
  {
    name: "basic_needs",
    label: "Are your day-to-day essentials reliably met?",
    help: "Food, warmth, somewhere to sleep. 0 means rarely, 5 means always.",
    min: 0,
    max: 5,
    lowLabel: "Rarely",
    highLabel: "Always",
  },
  {
    name: "academic_performance",
    label: "How do you feel your studies are going?",
    help: "0 means very poorly, 5 means very well.",
    min: 0,
    max: 5,
    lowLabel: "Very poorly",
    highLabel: "Very well",
  },
  {
    name: "study_load",
    label: "How heavy is your current workload?",
    help: "0 means very light, 5 means very heavy.",
    min: 0,
    max: 5,
    lowLabel: "Very light",
    highLabel: "Very heavy",
  },
  {
    name: "teacher_student_relationship",
    label: "How are your relationships with teaching staff?",
    help: "0 means very strained, 5 means very supportive.",
    min: 0,
    max: 5,
    lowLabel: "Strained",
    highLabel: "Supportive",
  },
  {
    name: "social_support",
    label: "How supported do you feel by the people around you?",
    help: "0 means not at all, 3 means well supported.",
    min: 0,
    max: 3,
    lowLabel: "Not at all",
    highLabel: "Well supported",
  },
  {
    name: "peer_pressure",
    label: "How much pressure do you feel from those around you?",
    help: "0 means none, 5 means a great deal.",
    min: 0,
    max: 5,
    lowLabel: "None",
    highLabel: "A great deal",
  },
  {
    name: "extracurricular_activities",
    label: "How much are you taking on outside your studies?",
    help: "0 means nothing, 5 means a great deal.",
    min: 0,
    max: 5,
    lowLabel: "Nothing",
    highLabel: "A great deal",
  },
] as const;

/** Field names in positional order, as the backend expects them. */
export const FEATURE_NAMES: readonly string[] = FEATURE_FIELDS.map((f) => f.name);

export type AssessmentPayload = Record<string, number>;

/** Midpoint defaults, so no answer is pre-nudged toward a stressed reading. */
export function defaultAnswers(): AssessmentPayload {
  return Object.fromEntries(
    FEATURE_FIELDS.map((f) => [f.name, Math.round((f.min + f.max) / 2)]),
  );
}

/**
 * Options for the Adaptive Recovery Framework's engagement question, asked as
 * part of every submission. Values match the backend's `PreviousEngagement`
 * literal exactly. Defaults to "no_previous_checkin" — see `AssessmentPage`.
 */
export const ENGAGEMENT_OPTIONS: readonly { value: string; label: string }[] = [
  { value: "no_previous_checkin", label: "This is my first check-in" },
  { value: "yes", label: "Yes, I tried them" },
  { value: "partially", label: "I tried some of them" },
  { value: "no", label: "No, I didn't get to them" },
] as const;
