import { Link, Navigate, useLocation } from "react-router-dom";
import type { AssessmentResult } from "../services/api";

/**
 * Displays the backend's response.
 *
 * The explanation paragraph and every recommendation/affirmation/escalation
 * string are rendered VERBATIM. That text was generated server-side and
 * passed the vocabulary safety gate there (no clinical language, no ML
 * terminology). Re-wording, truncating, or re-casing it client-side would
 * bypass that check, so this component only ever places the strings into the
 * DOM.
 */
export function ResultsPage() {
  const location = useLocation();
  const result = location.state as AssessmentResult | null;

  // Direct navigation without a result — send the user back to the form.
  if (!result) {
    return <Navigate to="/assessment" replace />;
  }

  return (
    <div>
      <p className="text-xs uppercase tracking-wider text-ink-faint">
        Your check-in
      </p>

      {/* The level is stated in the backend's own words. No colour coding: a
          red badge would read as an alarm, and severity is not a diagnosis. */}
      <h1 className="mt-2 text-xl font-semibold tracking-tight text-ink">
        Things look{" "}
        <span className="text-accent-strong">{result.stress_level_label}</span>{" "}
        right now
      </h1>

      <section className="mt-6 rounded-lg border border-line bg-card p-6">
        <p className="whitespace-pre-line text-[15px] leading-7 text-ink">
          {result.explanation}
        </p>
      </section>

      {result.is_escalation ? (
        // Foregrounded but not alarming: a clearly distinct card (accent
        // left border, no red/warning colour — ethical_framework.md asks for
        // "a clear, non-alarming prompt"), placed where suggestions normally
        // go rather than appended below them, since this replaces the
        // automated suggestions rather than supplementing them.
        <section
          className="mt-8 rounded-lg border border-accent bg-accent-soft/60 p-6"
          role="note"
          aria-label="Wellbeing service signpost"
        >
          <h2 className="text-sm font-semibold tracking-tight text-accent-strong">
            Worth reaching out
          </h2>
          <p className="mt-3 whitespace-pre-line text-[15px] leading-7 text-ink">
            {result.escalation_message}
          </p>
        </section>
      ) : (
        <section className="mt-8">
          <h2 className="text-sm font-semibold tracking-tight text-ink">
            Suggested next steps
          </h2>

          {result.is_affirmation ? (
            <p className="mt-3 rounded-lg border border-line bg-accent-soft/40 p-5 text-[15px] leading-7 text-ink">
              {result.affirmation}
            </p>
          ) : (
            <ol className="mt-3 space-y-4">
              {result.recommendations.map((rec) => (
                <li
                  key={rec.priority}
                  className="rounded-lg border border-line bg-card p-5"
                >
                  <div className="flex items-baseline gap-3">
                    <span
                      aria-hidden="true"
                      className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent-strong"
                    >
                      {rec.priority}
                    </span>
                    <h3 className="text-[15px] font-medium text-ink">
                      {rec.title}
                    </h3>
                  </div>
                  <p className="mt-2 pl-9 text-[15px] leading-7 text-ink">
                    {rec.action}
                  </p>
                  <p className="mt-2 pl-9 text-sm leading-6 text-ink-soft">
                    {rec.rationale}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </section>
      )}

      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Link
          to="/assessment"
          className="rounded-md border border-line px-4 py-2 text-sm text-ink-soft transition-colors hover:bg-accent-soft hover:text-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          Start another check-in
        </Link>
        <Link
          to="/progress"
          className="text-sm text-ink-soft underline-offset-4 hover:text-accent-strong hover:underline"
        >
          See your trends
        </Link>
        <p className="text-xs text-ink-faint">
          Saved {new Date(result.created_at).toLocaleString()}
        </p>
      </div>
    </div>
  );
}
