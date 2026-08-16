import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ScaleField } from "../components/Field";
import { ApiError, submitAssessment } from "../services/api";
import { useAuth } from "../services/auth";
import {
  FEATURE_FIELDS,
  defaultAnswers,
  type AssessmentPayload,
} from "../services/featureSchema";

/**
 * The questionnaire.
 *
 * Renders exactly the 14 fields in `FEATURE_FIELDS`, in schema order. Nothing is
 * added, omitted, or reordered here — the payload must match the model's input
 * contract, and a mismatch would produce a wrong prediction rather than an error.
 */
export function AssessmentPage() {
  const [answers, setAnswers] = useState<AssessmentPayload>(defaultAnswers);
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
      const result = await submitAssessment(answers, token);
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
      <p className="mt-2 max-w-prose text-sm leading-relaxed text-ink-soft">
        Fourteen quick questions. Answer for how the last week or two has felt —
        there are no right answers, and nothing here is a test.
      </p>

      <form onSubmit={handleSubmit} className="mt-6" noValidate>
        <div className="rounded-lg border border-line bg-card px-6">
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
