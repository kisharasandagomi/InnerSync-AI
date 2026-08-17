/**
 * Pure state machine driving the chat-delivered check-in.
 *
 * Deliberately has no rendering, no network calls, and no dependency on
 * React — kept exactly as testable as `featureSchema.ts` itself, since this
 * module is what guarantees the chat-driven flow produces the same 14-value
 * payload, in the same order and within the same bounds, as the slider form
 * always has. `checkinFlow.test.ts` asserts that directly.
 *
 * The LLM has no role anywhere in this file. Per this session's task: each
 * answer is captured as a precise value from a bounded control (chips or a
 * slider, rendered by `CheckinQuestion.tsx`), never interpreted from
 * free text — the same "no LLM in the prediction path" discipline that
 * governs the rest of this system (see `app/chatbot/service.py`'s module
 * docstring on the backend) applies here on the frontend too: this state
 * machine only ever accepts a value that was already validated against a
 * field's bounds before being passed in.
 */

import {
  ENGAGEMENT_OPTIONS,
  FEATURE_FIELDS,
  type AssessmentPayload,
  type FeatureField,
} from "./featureSchema";
import type { PreviousEngagement } from "./api";

export interface EngagementQuestion {
  kind: "engagement";
  options: typeof ENGAGEMENT_OPTIONS;
}

export interface FeatureQuestion {
  kind: "feature";
  field: FeatureField;
  /** 1-based position among the 14 feature questions, for "Question X of 14". */
  index: number;
  total: number;
}

export type CheckinQuestion = EngagementQuestion | FeatureQuestion;

export interface CheckinState {
  /** 0 = the engagement question; 1..14 = FEATURE_FIELDS[0..13]; 15 = complete. */
  readonly step: number;
  readonly previousEngagement: PreviousEngagement | null;
  readonly answers: Readonly<Partial<AssessmentPayload>>;
}

const TOTAL_STEPS = FEATURE_FIELDS.length + 1; // engagement question + 14 features

/** A fresh check-in, starting at the engagement question — same order as the slider form. */
export function startCheckin(): CheckinState {
  return { step: 0, previousEngagement: null, answers: {} };
}

/** Whether every question has been answered and the state is ready to submit. */
export function isComplete(state: CheckinState): boolean {
  return state.step >= TOTAL_STEPS;
}

/**
 * The question the student should be asked right now, or `null` if the
 * check-in is already complete.
 */
export function currentQuestion(state: CheckinState): CheckinQuestion | null {
  if (isComplete(state)) return null;
  if (state.step === 0) {
    return { kind: "engagement", options: ENGAGEMENT_OPTIONS };
  }
  const featureIndex = state.step - 1;
  return {
    kind: "feature",
    field: FEATURE_FIELDS[featureIndex],
    index: featureIndex + 1,
    total: FEATURE_FIELDS.length,
  };
}

/**
 * Record the answer to the engagement question and advance.
 *
 * @throws Error if the check-in is not currently on the engagement question.
 */
export function answerEngagement(
  state: CheckinState,
  value: PreviousEngagement,
): CheckinState {
  if (state.step !== 0) {
    throw new Error("Not currently on the engagement question");
  }
  return { ...state, step: 1, previousEngagement: value };
}

/**
 * Record the answer to the current feature question and advance.
 *
 * Validates the value against the current field's own bounds before
 * accepting it — the same bounds `feature_schema.json` defines and the
 * slider form already enforces via each `<input type="range">`'s min/max.
 * A control that only ever offers in-bounds choices (see
 * `CheckinQuestion.tsx`) should never trigger this, but the check stays
 * here rather than being trusted to the caller, for the same "verify the
 * contract, don't just assume it" discipline used everywhere else in this
 * project.
 *
 * @throws Error if the check-in is not currently on a feature question, or
 *   `value` falls outside that field's `[min, max]`.
 */
export function answerFeature(state: CheckinState, value: number): CheckinState {
  const question = currentQuestion(state);
  if (question === null || question.kind !== "feature") {
    throw new Error("Not currently on a feature question");
  }
  const { field } = question;
  if (!Number.isInteger(value) || value < field.min || value > field.max) {
    throw new Error(
      `${field.name}: ${value} is outside the valid range [${field.min}, ${field.max}]`,
    );
  }
  return {
    ...state,
    step: state.step + 1,
    answers: { ...state.answers, [field.name]: value },
  };
}

export interface CheckinSubmission {
  answers: AssessmentPayload;
  previousEngagement: PreviousEngagement;
}

/**
 * The payload ready for `submitAssessment` — the exact same shape the
 * slider form has always produced: all 14 `FEATURE_FIELDS` names as keys,
 * schema order, each value within its field's bounds, plus
 * `previousEngagement`.
 *
 * @throws Error if the check-in is not yet complete.
 */
export function toSubmission(state: CheckinState): CheckinSubmission {
  if (!isComplete(state) || state.previousEngagement === null) {
    throw new Error("Check-in is not complete yet");
  }
  const answers = {} as AssessmentPayload;
  for (const field of FEATURE_FIELDS) {
    const value = state.answers[field.name];
    if (value === undefined) {
      throw new Error(`Missing answer for ${field.name}`);
    }
    answers[field.name] = value;
  }
  return { answers, previousEngagement: state.previousEngagement };
}
