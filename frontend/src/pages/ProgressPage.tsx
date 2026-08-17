import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ApiError,
  getAssessmentHistory,
  type AssessmentHistoryItem,
} from "../services/api";
import { useAuth } from "../services/auth";

/**
 * Progress Monitoring Dashboard (Module 9/10) — a trend view over a
 * student's own check-in history.
 *
 * Per CLAUDE.md's explainability principle, this shows the same kind of
 * human-readable output as everywhere else in the system: low/moderate/high
 * levels and plain-language framing, never a raw stress-level number
 * presented as a precise measurement, and never a SHAP value, feature name,
 * or severity score. `top_factor_phrase` on each history item is already the
 * same pre-approved, safety-gate-validated phrase used in the explanation
 * paragraph — this page renders it verbatim, exactly as `ResultsPage` does,
 * rather than deriving new text from anything technical.
 *
 * Colour is not load-bearing here either (see `index.css`'s design-token
 * comment): the bars use a single accent hue at three intensities, and every
 * bar carries its own word label, so removing colour entirely would not lose
 * information.
 */
export function ProgressPage() {
  const { token } = useAuth();
  const [history, setHistory] = useState<AssessmentHistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    getAssessmentHistory(token)
      .then((items) => {
        if (!cancelled) setHistory(items);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError
            ? err.message
            : "Could not reach the server. Is the backend running?",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div>
      <p className="text-xs uppercase tracking-wider text-ink-faint">
        Your progress
      </p>
      <h1 className="mt-2 text-xl font-semibold tracking-tight text-ink">
        How things have been trending
      </h1>

      {error && (
        <p className="mt-6 rounded-lg border border-line bg-card p-4 text-sm text-ink-soft">
          {error}
        </p>
      )}

      {!error && history === null && (
        <p className="mt-6 text-sm text-ink-faint">Loading your check-ins…</p>
      )}

      {!error && history !== null && <ProgressBody history={history} />}
    </div>
  );
}

function ProgressBody({ history }: { history: AssessmentHistoryItem[] }) {
  if (history.length === 0) {
    return (
      <section className="mt-6 rounded-lg border border-line bg-card p-6">
        <p className="text-[15px] leading-7 text-ink">
          You haven't completed a check-in yet.
        </p>
        <Link
          to="/assessment"
          className="mt-4 inline-block rounded-md border border-line px-4 py-2 text-sm text-ink-soft transition-colors hover:bg-accent-soft hover:text-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          Start your first check-in
        </Link>
      </section>
    );
  }

  if (history.length === 1) {
    const only = history[0];
    return (
      <section className="mt-6 rounded-lg border border-line bg-card p-6">
        <p className="text-[15px] leading-7 text-ink">
          You've completed one check-in so far, on{" "}
          {formatDate(only.created_at)}, which came out{" "}
          <span className="font-medium text-accent-strong">
            {only.stress_level_label}
          </span>
          .
        </p>
        {only.top_factor_phrase && (
          <p className="mt-2 text-sm leading-6 text-ink-soft">
            At the time, {only.top_factor_phrase}.
          </p>
        )}
        <p className="mt-4 text-sm text-ink-faint">
          Come back after your next check-in and this page will start showing
          how things are trending over time.
        </p>
      </section>
    );
  }

  const summary = summarizeTrend(history);

  return (
    <>
      <section className="mt-6 rounded-lg border border-line bg-card p-6">
        <p className="text-[15px] leading-7 text-ink">{summary}</p>
      </section>

      <section
        className="mt-6 rounded-lg border border-line bg-card p-6"
        aria-label="Check-in trend"
      >
        <div className="flex items-end gap-3 overflow-x-auto pb-2">
          {history.map((item) => (
            <div
              key={item.assessment_id}
              className="flex shrink-0 flex-col items-center gap-2"
            >
              <span className="text-[11px] font-medium text-ink-soft">
                {levelWord(item.stress_level)}
              </span>
              <div
                className={`w-8 rounded-t-sm ${barClass(item.stress_level)}`}
                style={{ height: barHeight(item.stress_level) }}
                role="img"
                aria-label={`${formatDate(item.created_at)}: ${levelWord(item.stress_level)}`}
              />
              <span className="text-[11px] text-ink-faint">
                {formatShortDate(item.created_at)}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold tracking-tight text-ink">
          Check-in by check-in
        </h2>
        <ol className="mt-3 space-y-3">
          {[...history].reverse().map((item) => (
            <li
              key={item.assessment_id}
              className="rounded-lg border border-line bg-card p-5"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                <p className="text-[15px] font-medium text-ink">
                  {formatDate(item.created_at)} —{" "}
                  <span className="text-accent-strong">
                    {item.stress_level_label}
                  </span>
                </p>
                <div className="flex gap-2">
                  {item.is_escalation && (
                    <span className="rounded-full border border-accent bg-accent-soft/60 px-2 py-0.5 text-[11px] text-accent-strong">
                      Pointed toward wellbeing services
                    </span>
                  )}
                  {!item.is_escalation && item.adaptive_recovery_applied && (
                    <span className="rounded-full border border-line bg-accent-soft/40 px-2 py-0.5 text-[11px] text-ink-soft">
                      Suggestions adjusted from last time
                    </span>
                  )}
                </div>
              </div>
              {item.top_factor_phrase && (
                <p className="mt-2 text-sm leading-6 text-ink-soft">
                  {capitalise(item.top_factor_phrase)}.
                </p>
              )}
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}

function levelWord(level: 0 | 1 | 2): string {
  return level === 0 ? "Low" : level === 1 ? "Moderate" : "High";
}

// Single accent hue at three intensities — never red/amber/green. Every bar
// also carries its own word label above it, so colour is supporting
// information, not the only carrier of it.
function barClass(level: 0 | 1 | 2): string {
  if (level === 0) return "bg-accent-soft border border-accent/40";
  if (level === 1) return "bg-accent/60";
  return "bg-accent-strong";
}

function barHeight(level: 0 | 1 | 2): string {
  if (level === 0) return "1.5rem";
  if (level === 1) return "3.25rem";
  return "5rem";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatShortDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
  });
}

function capitalise(text: string): string {
  return text.length ? text[0].toUpperCase() + text.slice(1) : text;
}

/**
 * Plain-language trend framing from a chronological (oldest-first) history.
 * Compares recent levels only — never states or implies a raw number.
 */
export function summarizeTrend(history: AssessmentHistoryItem[]): string {
  const levels = history.map((item) => item.stress_level);
  const n = levels.length;
  const latest = levels[n - 1];
  const previous = levels[n - 2];

  if (latest < previous) {
    return "Things have been trending a little steadier over your last couple of check-ins.";
  }
  if (latest > previous) {
    return "The last couple of check-ins suggest things have felt a bit heavier recently.";
  }
  if (n >= 3 && levels[n - 3] !== latest) {
    return `Your last few check-ins have settled at a fairly steady ${levelWord(latest).toLowerCase()} level.`;
  }
  return "Your last two check-ins have looked similar.";
}
