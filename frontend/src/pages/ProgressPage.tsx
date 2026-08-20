import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ApiError,
  getAssessmentHistory,
  getDevelopmentSummary,
  type AssessmentHistoryItem,
  type DevelopmentSummaryResponse,
} from "../services/api";
import { canDownloadSummaryReport, downloadSummaryReport } from "../services/pdfReport";
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
 *
 * Each entry in "Check-in by check-in" is expandable (round 2 UX feedback):
 * `top_factor_phrase` alone was too thin a summary. Expanding reveals that
 * check-in's full `explanation` paragraph — the exact
 * `ExplanationRecord.paragraph` text the student already read on the
 * results screen at the time, reused verbatim via `GET /assessments/history`.
 * Nothing here regenerates or rewords it.
 */
export function ProgressPage() {
  const { token } = useAuth();
  const [history, setHistory] = useState<AssessmentHistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Round 7: fetched independently of `history` (its own endpoint,
  // GET /assessments/summary) rather than derived from `history` here on
  // the frontend, so the aggregation stays server-side, template-based, and
  // safety-gate-validated -- see app.services.development_summary.
  const [devSummary, setDevSummary] = useState<DevelopmentSummaryResponse | null>(null);

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
    getDevelopmentSummary(token)
      .then((result) => {
        if (!cancelled) setDevSummary(result);
      })
      .catch(() => {
        // Non-critical: the rest of the page (trend graph, check-in list)
        // still works without the aggregated summary, so a failure here
        // does not set the page-level error state.
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div>
      <p className="text-xs uppercase tracking-wider text-ink-faint">
        My Trends
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

      {!error && history !== null && (
        <ProgressBody history={history} devSummary={devSummary} />
      )}
    </div>
  );
}

function ProgressBody({
  history,
  devSummary,
}: {
  history: AssessmentHistoryItem[];
  devSummary: DevelopmentSummaryResponse | null;
}) {
  if (history.length === 0) {
    return (
      <section className="mt-6 rounded-lg border border-line bg-card p-6">
        <p className="text-base leading-7 text-ink">
          You haven't completed a check-in yet.
        </p>
        <Link
          to="/assessment"
          className="mt-4 inline-block rounded-md border border-line px-4 py-2 text-sm text-ink-soft transition-colors hover:bg-accent-soft hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
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
        <p className="text-base leading-7 text-ink">
          You've completed one check-in so far, on{" "}
          {formatDate(only.created_at)}, which came out{" "}
          <span className="font-medium text-ink">
            {only.stress_level_label}
          </span>
          .
        </p>
        {only.top_factor_phrase && (
          <p className="mt-2 text-sm leading-6 text-ink-soft">
            At the time, {only.top_factor_phrase}.
          </p>
        )}
        {only.explanation && (
          <p className="mt-3 whitespace-pre-line text-sm leading-6 text-ink-soft">
            {only.explanation}
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
        <p className="text-base leading-7 text-ink">{summary}</p>
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
              <span className="text-xs font-medium text-ink-soft">
                {levelWord(item.stress_level)}
              </span>
              <div
                className={`w-8 rounded-t-sm ${barClass(item.stress_level)}`}
                style={{ height: barHeight(item.stress_level) }}
                role="img"
                aria-label={`${formatDate(item.created_at)}: ${levelWord(item.stress_level)}`}
              />
              <span className="text-xs text-ink-faint">
                {formatShortDate(item.created_at)}
              </span>
            </div>
          ))}
        </div>
      </section>

      {devSummary && devSummary.checkins_considered >= 2 && (
        <DevelopmentSummarySection summary={devSummary} history={history} />
      )}

      <section className="mt-8">
        <h2 className="text-sm font-semibold tracking-tight text-ink">
          Check-in by check-in
        </h2>
        <ol className="mt-3 space-y-3">
          {[...history].reverse().map((item) => (
            <HistoryEntry key={item.assessment_id} item={item} />
          ))}
        </ol>
      </section>
    </>
  );
}

/**
 * Round 7: aggregated, plain-language pattern summary across the student's
 * most recent check-ins, from `GET /assessments/summary`. Every string here
 * is rendered verbatim -- `summary_sentence` and `closing_message` are both
 * already template-based and safety-gate-validated server-side (see
 * `app.services.development_summary`), the same discipline as
 * `top_factor_phrase` and `explanation` elsewhere on this page.
 *
 * Round 8: a "Download PDF" button for this same content, gated on the
 * caller's full check-in count (not `summary.checkins_considered`, which
 * caps at the 5-check-in summary window and would stay stuck at showing the
 * gate note forever for a student with 6+ check-ins but only 2 within the
 * window). Below the 3-check-in minimum this renders an explanatory note
 * instead of a disabled button, since a disabled control here would invite
 * clicking it to find out why nothing happens.
 */
function DevelopmentSummarySection({
  summary,
  history,
}: {
  summary: DevelopmentSummaryResponse;
  history: AssessmentHistoryItem[];
}) {
  const canDownload = canDownloadSummaryReport(history);
  return (
    <section className="mt-6 rounded-lg border border-line bg-card p-6">
      <h2 className="text-sm font-semibold tracking-tight text-ink">
        Since your last few check-ins
      </h2>
      <p className="mt-2 text-base leading-7 text-ink">{summary.summary_sentence}</p>
      <p className="mt-3 text-sm leading-6 text-ink-soft">{summary.closing_message}</p>

      {canDownload ? (
        <button
          type="button"
          onClick={() => downloadSummaryReport(history, summary)}
          className="mt-4 rounded-md border border-line px-4 py-2 text-sm text-ink-soft transition-colors hover:bg-accent-soft hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          Download summary PDF
        </button>
      ) : (
        <p className="mt-4 text-sm text-ink-faint">
          A downloadable summary PDF becomes available after your 3rd check-in.
        </p>
      )}
    </section>
  );
}

/**
 * One reverse-chronological entry, collapsed to the one-line
 * `top_factor_phrase` by default, expandable to that check-in's full
 * `explanation` paragraph — reused verbatim, never regenerated (see the
 * module docstring above).
 */
function HistoryEntry({ item }: { item: AssessmentHistoryItem }) {
  const [expanded, setExpanded] = useState(false);
  const detailId = `history-detail-${item.assessment_id}`;

  return (
    <li className="rounded-lg border border-line bg-card p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <p className="text-base font-medium text-ink">
          {formatDate(item.created_at)}:{" "}
          <span className="text-ink">{item.stress_level_label}</span>
        </p>
        <div className="flex gap-2">
          {item.is_escalation && (
            <span className="rounded-full border border-accent bg-accent-soft/60 px-2 py-0.5 text-xs text-ink">
              Pointed toward wellbeing services
            </span>
          )}
          {!item.is_escalation && item.adaptive_recovery_applied && (
            <span className="rounded-full border border-line bg-accent-soft/40 px-2 py-0.5 text-xs text-ink-soft">
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

      {item.explanation && (
        <>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            aria-controls={detailId}
            className="mt-2 text-sm font-medium text-ink underline-offset-4 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {expanded ? "Show less" : "Show the full explanation"}
          </button>
          {expanded && (
            <div
              id={detailId}
              className="mt-2 rounded-md bg-accent-soft/30 p-3"
            >
              <p className="whitespace-pre-line text-sm leading-6 text-ink-soft">
                {item.explanation}
              </p>
              {/* Round 6: that check-in's plan, verbatim -- exactly one of
                  a ranked action list, an affirmation, or an escalation
                  signpost, same mutual exclusivity ResultsPage renders for
                  the current check-in. Nothing here regenerates or
                  reformats the text. */}
              {item.recommendations.length > 0 && (
                <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm leading-6 text-ink-soft">
                  {item.recommendations.map((rec) => (
                    <li key={rec.priority}>
                      <span className="font-medium text-ink">{rec.title}:</span>{" "}
                      {rec.action}
                    </li>
                  ))}
                </ul>
              )}
              {item.recommendations.length === 0 && item.is_affirmation && item.affirmation && (
                <p className="mt-3 text-sm leading-6 text-ink-soft">{item.affirmation}</p>
              )}
              {item.recommendations.length === 0 &&
                !item.is_affirmation &&
                item.is_escalation &&
                item.escalation_message && (
                  <p className="mt-3 text-sm leading-6 text-ink-soft">
                    {item.escalation_message}
                  </p>
                )}
            </div>
          )}
        </>
      )}
    </li>
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
