import { describe, expect, it } from "vitest";
import { ENGAGEMENT_OPTIONS, FEATURE_FIELDS, FEATURE_NAMES, defaultAnswers } from "./featureSchema";

/**
 * Guards the model's input contract.
 *
 * These values are copied from ml_pipeline/artifacts/feature_schema.json
 * (model v2). If the model is retrained with a different feature set, this test
 * fails — which is the point. A silently mismatched payload would produce a
 * wrong prediction rather than an error.
 */
const SCHEMA_ORDER = [
  "self_esteem",
  "mental_health_history",
  "headache",
  "breathing_problem",
  "noise_level",
  "living_conditions",
  "safety",
  "basic_needs",
  "academic_performance",
  "study_load",
  "teacher_student_relationship",
  "social_support",
  "peer_pressure",
  "extracurricular_activities",
];

const SCHEMA_BOUNDS: Record<string, [number, number]> = {
  self_esteem: [0, 30],
  mental_health_history: [0, 1],
  headache: [0, 5],
  breathing_problem: [0, 5],
  noise_level: [0, 5],
  living_conditions: [0, 5],
  safety: [0, 5],
  basic_needs: [0, 5],
  academic_performance: [0, 5],
  study_load: [0, 5],
  teacher_student_relationship: [0, 5],
  social_support: [0, 3],
  peer_pressure: [0, 5],
  extracurricular_activities: [0, 5],
};

/** Excluded from v2 for target leakage — see ADR-003. Must never be collected. */
const LEAKY_FEATURES = [
  "sleep_quality",
  "future_career_concerns",
  "blood_pressure",
  "depression",
  "bullying",
  "anxiety_level",
];

describe("feature schema contract", () => {
  it("has exactly 14 fields", () => {
    expect(FEATURE_FIELDS).toHaveLength(14);
  });

  it("matches feature_schema.json names in positional order", () => {
    expect([...FEATURE_NAMES]).toEqual(SCHEMA_ORDER);
  });

  it("matches the schema's min/max for every field", () => {
    for (const field of FEATURE_FIELDS) {
      const [min, max] = SCHEMA_BOUNDS[field.name];
      expect([field.name, field.min, field.max]).toEqual([field.name, min, max]);
    }
  });

  it("collects no feature excluded for target leakage", () => {
    const collected = new Set(FEATURE_NAMES);
    for (const leaky of LEAKY_FEATURES) {
      expect(collected.has(leaky)).toBe(false);
    }
  });

  it("builds a payload with one entry per field, all in range", () => {
    const payload = defaultAnswers();
    expect(Object.keys(payload)).toHaveLength(14);
    expect(Object.keys(payload).sort()).toEqual([...SCHEMA_ORDER].sort());
    for (const field of FEATURE_FIELDS) {
      expect(payload[field.name]).toBeGreaterThanOrEqual(field.min);
      expect(payload[field.name]).toBeLessThanOrEqual(field.max);
    }
  });
});

describe("adaptive recovery engagement contract", () => {
  /**
   * Mirrors backend/app/schemas/assessment.py's PreviousEngagement literal
   * exactly. A value present here but not accepted by the backend (or vice
   * versa) would surface as a 422 the student can't do anything about.
   */
  const BACKEND_ENGAGEMENT_VALUES = ["yes", "partially", "no", "no_previous_checkin"];

  it("offers exactly the values the backend accepts", () => {
    const offered = ENGAGEMENT_OPTIONS.map((o) => o.value).sort();
    expect(offered).toEqual([...BACKEND_ENGAGEMENT_VALUES].sort());
  });

  it("defaults the form to 'first check-in', not an engaged/unengaged guess", () => {
    expect(ENGAGEMENT_OPTIONS[0].value).toBe("no_previous_checkin");
  });
});
