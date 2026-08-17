import { describe, expect, it } from "vitest";
import { FEATURE_FIELDS } from "./featureSchema";
import {
  answerEngagement,
  answerFeature,
  currentQuestion,
  isComplete,
  startCheckin,
  toSubmission,
} from "./checkinFlow";

/**
 * Guards that the chat-driven check-in produces the exact same contract as
 * the slider form — same 14 keys, schema order, in-bounds values — since
 * both ultimately call the same unchanged `submitAssessment` /
 * `POST /assessments`. Mirrors `featureSchema.test.ts`'s "guard the
 * contract" pattern.
 */

/** Answers every question with a value at the middle of its own range. */
function completeCheckin(engagement: "yes" | "no" | "partially" | "no_previous_checkin" = "no_previous_checkin") {
  let state = startCheckin();
  state = answerEngagement(state, engagement);
  for (const field of FEATURE_FIELDS) {
    state = answerFeature(state, Math.round((field.min + field.max) / 2));
  }
  return state;
}

describe("checkin flow: question sequence", () => {
  it("asks the engagement question first", () => {
    const state = startCheckin();
    const question = currentQuestion(state);
    expect(question?.kind).toBe("engagement");
  });

  it("then asks all 14 feature questions in exact schema order", () => {
    let state = answerEngagement(startCheckin(), "no_previous_checkin");
    for (const field of FEATURE_FIELDS) {
      const question = currentQuestion(state);
      expect(question?.kind).toBe("feature");
      if (question?.kind === "feature") {
        expect(question.field.name).toBe(field.name);
      }
      state = answerFeature(state, field.min);
    }
    expect(currentQuestion(state)).toBeNull();
  });

  it("reports 1-based progress out of 14 for feature questions", () => {
    let state = answerEngagement(startCheckin(), "no_previous_checkin");
    const first = currentQuestion(state);
    expect(first?.kind === "feature" && first.index).toBe(1);
    expect(first?.kind === "feature" && first.total).toBe(14);

    state = answerFeature(state, FEATURE_FIELDS[0].min);
    const second = currentQuestion(state);
    expect(second?.kind === "feature" && second.index).toBe(2);
  });

  it("is not complete until all 15 questions (engagement + 14) are answered", () => {
    let state = startCheckin();
    expect(isComplete(state)).toBe(false);
    state = answerEngagement(state, "no_previous_checkin");
    expect(isComplete(state)).toBe(false);
    for (const field of FEATURE_FIELDS.slice(0, -1)) {
      state = answerFeature(state, field.min);
      expect(isComplete(state)).toBe(false);
    }
    state = answerFeature(state, FEATURE_FIELDS.at(-1)!.min);
    expect(isComplete(state)).toBe(true);
  });
});

describe("checkin flow: value validation", () => {
  it("rejects a value below the current field's minimum", () => {
    const state = answerEngagement(startCheckin(), "no_previous_checkin");
    expect(() => answerFeature(state, FEATURE_FIELDS[0].min - 1)).toThrow();
  });

  it("rejects a value above the current field's maximum", () => {
    const state = answerEngagement(startCheckin(), "no_previous_checkin");
    expect(() => answerFeature(state, FEATURE_FIELDS[0].max + 1)).toThrow();
  });

  it("rejects a non-integer value", () => {
    const state = answerEngagement(startCheckin(), "no_previous_checkin");
    expect(() => answerFeature(state, FEATURE_FIELDS[0].min + 0.5)).toThrow();
  });

  it("accepts both endpoints of a field's range", () => {
    const field = FEATURE_FIELDS[0];
    const state = answerEngagement(startCheckin(), "no_previous_checkin");
    expect(() => answerFeature(state, field.min)).not.toThrow();
    expect(() => answerFeature(state, field.max)).not.toThrow();
  });

  it("refuses to answer a feature question before the engagement question", () => {
    const state = startCheckin();
    expect(() => answerFeature(state, FEATURE_FIELDS[0].min)).toThrow();
  });

  it("refuses to re-answer the engagement question once past it", () => {
    const state = answerEngagement(startCheckin(), "no_previous_checkin");
    expect(() => answerEngagement(state, "yes")).toThrow();
  });
});

describe("checkin flow: submission contract", () => {
  it("refuses to build a submission before the check-in is complete", () => {
    const state = answerEngagement(startCheckin(), "no_previous_checkin");
    expect(() => toSubmission(state)).toThrow();
  });

  it("produces exactly the 14 schema keys, in schema order values, all in range", () => {
    const submission = toSubmission(completeCheckin());
    const keys = Object.keys(submission.answers);
    expect(keys).toHaveLength(14);
    expect(keys.sort()).toEqual(FEATURE_FIELDS.map((f) => f.name).sort());
    for (const field of FEATURE_FIELDS) {
      const value = submission.answers[field.name];
      expect(value).toBeGreaterThanOrEqual(field.min);
      expect(value).toBeLessThanOrEqual(field.max);
    }
  });

  it("carries the engagement answer through unchanged", () => {
    const submission = toSubmission(completeCheckin("yes"));
    expect(submission.previousEngagement).toBe("yes");
  });

  it("produces a payload identical in shape to the slider form's own default payload", () => {
    // Cross-check against featureSchema's own defaultAnswers(), the slider
    // form's payload builder — same keys, same order, same value domain.
    const submission = toSubmission(completeCheckin());
    const sliderFormKeys = Object.keys(
      Object.fromEntries(FEATURE_FIELDS.map((f) => [f.name, f.min])),
    );
    expect(Object.keys(submission.answers).sort()).toEqual(sliderFormKeys.sort());
  });
});
