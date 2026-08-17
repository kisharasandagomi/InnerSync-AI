import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ScaleField } from "../components/Field";
import { ApiError, submitAssessment, type PreviousEngagement } from "../services/api";
import { useAuth } from "../services/auth";
import {
  ENGAGEMENT_OPTIONS,
  FEATURE_FIELDS,
  defaultAnswers,
  type AssessmentPayload,
} from "../services/featureSchema";

/**
 * The questionnaire.
 *
 * Renders exactly the 14 fields in `FEATURE_FIELDS`, in schema order, plus one
 * additional control for the Adaptive Recovery Framework: self-reported
 * engagement with the *previous* check-in's recommendations, folded into this
 * same submission rather than a separate flow. Nothing about the 14 feature
 * fields is added, omitted, or reordered — the payload must match the model's
 * input contract, and a mismatch would produce a wrong prediction rather than
 * an error.
 */
export function AssessmentPage() {
  const [answers, setAnswers] = useState<AssessmentPayload>(defaultAnswers);
  // Defaults to "first check-in" — the honest value unless a returning
  // student actively says otherwise, matching the backend's own default
  // reasoning (see EngagementLevel in app/models/assessment.py).
  const [previousEngagement, setPreviousEngagement] =
    useState<PreviousEngagement>("no_previous_checkin");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const { token } = useAuth();
  const navigate = useNavigate();

  function updateAnswer(name: string, value: number) {
    setAnswers((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    setError(null);
    setBusy(true);
    try {
      const result = await submitAssessment(answers, previousEngagement, token);
      // Hand the result straight to the results screen; it is never re-derived
      // or re-worded client-side.
      navigate("/results", { state: result });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not reach the server. Is the backend running?",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="text-xl font-semibold tracking-tight text-ink">
        How are things at the moment?
      </h1>
      <p className="mt-2 max-w-prose text-base leading-relaxed text-ink-soft">
        Fourteen quick questions. Answer for how the last week or two has felt —
        there are no right answers, and nothing here is a test.
      </p>

      <form onSubmit={handleSubmit} className="mt-6" noValidate>
        <div className="rounded-lg border border-line bg-card px-6 py-5">
          <label
            htmlFor="previous-engagement"
            className="block text-base font-medium text-ink"
          >
            Did you try the suggestions from your last check-in?
          </label>
          <p className="mt-1 text-sm text-ink-faint">
            There's no wrong answer here — this just helps keep suggestions
            useful over time.
          </p>
          <select
            id="previous-engagement"
            name="previous_engagement"
            value={previousEngagement}
            onChange={(e) =>
              setPreviousEngagement(e.target.value as PreviousEngagement)
            }
            className="mt-3 w-full rounded-md border border-line bg-card px-3 py-2 text-base text-ink focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {ENGAGEMENT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-4 rounded-lg border border-line bg-card px-6">
          {FEATURE_FIELDS.map((field) => (
            <ScaleField
              key={field.name}
              field={field}
              value={answers[field.name]}
              onChange={updateAnswer}
            />
          ))}
        </div>

        {error && (
          <p role="alert" className="mt-4 text-sm text-danger">
            {error}
          </p>
        )}

        <div className="mt-6 flex items-center gap-4">
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-accent px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
          >
            {busy ? "Working…" : "See my check-in"}
          </button>
          <p className="text-xs text-ink-faint">
            {FEATURE_FIELDS.length} questions
          </p>
        </div>
      </form>
    </div>
  );
}
