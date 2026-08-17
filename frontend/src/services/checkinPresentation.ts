/**
 * Which widget style presents each feature question in the chat check-in.
 *
 * **Rendering-layer only.** Nothing here is imported by `checkinFlow.ts`,
 * and nothing here changes what a valid answer is — every style still ends
 * by calling the same `onAnswerFeature(value: number)` with an integer
 * inside the field's own `[min, max]`, which `checkinFlow.answerFeature()`
 * validates exactly as before. This module exists only so
 * `CheckinQuestion.tsx` doesn't have to hardcode one visual treatment for
 * every question — round after round of identical sliders was the actual
 * feedback this addresses.
 *
 * Style assignment reasoning (not arbitrary — grouped by what the question
 * is actually asking):
 * - **slider**: magnitude/quantity questions, where dragging a continuous
 *   scale matches how the student would naturally think about the answer
 *   ("how much", "how heavy") — and the one wide-range field
 *   (`self_esteem`, 0-30) as before, since 31 chips would be absurd.
 * - **icon-scale**: subjective/emotional-register questions — how something
 *   *feels* (safe, supported, strained vs. relaxed) rather than how much of
 *   it there is. A face/mood icon communicates that register faster than a
 *   number does.
 * - **chips**: concrete, countable, or binary questions, where a small set
 *   of discrete labelled taps is already the clearest interaction — no
 *   improvement from a slider or icon here.
 *
 * No points, streaks, or scoring are introduced anywhere in this module —
 * this is about interaction variety, not gamification, per this session's
 * explicit instruction.
 */

export type CheckinWidgetStyle = "slider" | "icon-scale" | "chips";

/**
 * Icon sequences, one emoji per integer value from a field's `min` to
 * `max` inclusive, chosen to match that field's own direction (its
 * `lowLabel`/`highLabel`) rather than assuming low is always good — e.g.
 * `headache` improves toward its low end (never), while `safety` improves
 * toward its high end (very safe), so the two sequences run opposite ways.
 */
const ICON_SETS: Readonly<Record<string, readonly string[]>> = {
  // 0 never -> 5 very often: calm settles into visible discomfort.
  headache: ["😌", "🙂", "😐", "😕", "😣", "😖"],
  breathing_problem: ["😌", "🙂", "😐", "😕", "😣", "😖"],
  // 0 not at all safe -> 5 very safe: unease eases into comfort.
  safety: ["😟", "😕", "😐", "🙂", "😊", "😄"],
  // 0 very strained -> 5 very supportive: same register as `safety`.
  teacher_student_relationship: ["😟", "😕", "😐", "🙂", "😊", "😄"],
  // 0 not at all -> 3 well supported: same register, shorter range.
  social_support: ["😟", "😕", "🙂", "😊"],
};

const WIDGET_STYLE_BY_FIELD: Readonly<Record<string, CheckinWidgetStyle>> = {
  self_esteem: "slider",
  mental_health_history: "chips", // binary — rendered as its own two-way toggle regardless
  headache: "icon-scale",
  breathing_problem: "icon-scale",
  noise_level: "slider",
  living_conditions: "chips",
  safety: "icon-scale",
  basic_needs: "chips",
  academic_performance: "slider",
  study_load: "slider",
  teacher_student_relationship: "icon-scale",
  social_support: "icon-scale",
  peer_pressure: "chips",
  extracurricular_activities: "chips",
};

/** The widget style for a feature field, defaulting to "chips" if ever unassigned. */
export function widgetStyleFor(fieldName: string): CheckinWidgetStyle {
  return WIDGET_STYLE_BY_FIELD[fieldName] ?? "chips";
}

/** The icon sequence for an "icon-scale" field, or `null` if it has none. */
export function iconSetFor(fieldName: string): readonly string[] | null {
  return ICON_SETS[fieldName] ?? null;
}
