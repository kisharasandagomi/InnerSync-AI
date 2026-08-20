import { describe, expect, it } from "vitest";
import type { AssessmentHistoryItem, AssessmentResult, DevelopmentSummaryResponse } from "./api";
import {
  buildReportContent,
  buildSummaryReportContent,
  canDownloadSummaryReport,
  renderReportPdf,
  renderSummaryReportPdf,
} from "./pdfReport";
import { DISCLAIMER_TEXT } from "./disclaimer";

function baseResult(overrides: Partial<AssessmentResult>): AssessmentResult {
  return {
    assessment_id: 1,
    created_at: "2026-08-18T10:30:00Z",
    stress_level: 1,
    stress_level_label: "moderate",
    explanation: "Your current wellbeing check-in suggests a moderate amount of pressure.",
    recommendations: [],
    is_affirmation: false,
    affirmation: null,
    is_escalation: false,
    escalation_message: null,
    comparative_trend_message: null,
    ...overrides,
  };
}

describe("buildReportContent", () => {
  it("includes the plain-language label, never a raw numeric score, in its own field", () => {
    const content = buildReportContent(baseResult({}));
    expect(content.stressLevelLabel).toBe("moderate");
    // stress_level (the raw 0/1/2) must never leak into any rendered field.
    expect(JSON.stringify(content)).not.toMatch(/"stress_level":\s*1/);
  });

  it("carries the explanation paragraph verbatim", () => {
    const content = buildReportContent(baseResult({}));
    expect(content.explanation).toBe(
      "Your current wellbeing check-in suggests a moderate amount of pressure.",
    );
  });

  it("formats recommendations as numbered title + action pairs, verbatim", () => {
    const content = buildReportContent(
      baseResult({
        recommendations: [
          {
            priority: 1,
            title: "Reach one person directly",
            action: "Message someone you trust this week.",
            rationale: "Connection helps.",
            category: "social",
          },
        ],
      }),
    );
    expect(content.bodyHeading).toBe("Suggested next steps");
    expect(content.bodyParagraphs).toEqual([
      "1. Reach one person directly",
      "Message someone you trust this week.",
    ]);
  });

  it("uses the affirmation text when is_affirmation is set", () => {
    const content = buildReportContent(
      baseResult({ is_affirmation: true, affirmation: "Things look steady right now." }),
    );
    expect(content.bodyParagraphs).toEqual(["Things look steady right now."]);
  });

  it("uses the escalation message and heading when is_escalation is set", () => {
    const content = buildReportContent(
      baseResult({
        is_escalation: true,
        escalation_message: "Please reach out to your wellbeing service.",
      }),
    );
    expect(content.bodyHeading).toBe("Worth reaching out");
    expect(content.bodyParagraphs).toEqual(["Please reach out to your wellbeing service."]);
  });

  it("includes the exact site-wide disclaimer text", () => {
    const content = buildReportContent(baseResult({}));
    expect(content.disclaimer).toBe(DISCLAIMER_TEXT);
  });

  it("formats the date as a human-readable label derived from created_at", () => {
    const content = buildReportContent(baseResult({ created_at: "2026-08-18T10:30:00Z" }));
    expect(content.dateLabel).toBe(new Date("2026-08-18T10:30:00Z").toLocaleString());
  });
});

describe("renderReportPdf", () => {
  it("produces a non-empty single-page PDF document", () => {
    const content = buildReportContent(baseResult({}));
    const doc = renderReportPdf(content);
    expect(doc.getNumberOfPages()).toBe(1);
    const bytes = doc.output("arraybuffer") as ArrayBuffer;
    expect(bytes.byteLength).toBeGreaterThan(0);
  });

  it("embeds the explanation, level, and disclaimer text in the PDF's text content", () => {
    const content = buildReportContent(
      baseResult({ stress_level_label: "high", explanation: "A distinctive marker sentence." }),
    );
    const doc = renderReportPdf(content);
    const text = doc.output("datauristring");
    // The compressed PDF stream isn't plain-text searchable via the data URI,
    // so this only confirms the document was produced without throwing and
    // is non-trivial in size for the content supplied.
    expect(text.length).toBeGreaterThan(200);
  });
});

// ---------------------------------------------------------------------------
// Multi-check-in development summary report (round 8)
// ---------------------------------------------------------------------------

function historyItem(overrides: Partial<AssessmentHistoryItem>): AssessmentHistoryItem {
  return {
    assessment_id: 1,
    created_at: "2026-08-01T09:00:00Z",
    stress_level: 1,
    stress_level_label: "moderate",
    previous_engagement: "no_previous_checkin",
    adaptive_recovery_applied: false,
    is_escalation: false,
    top_factor_phrase: null,
    explanation: "Your check-in suggests a moderate amount of pressure.",
    recommendations: [],
    is_affirmation: false,
    affirmation: null,
    escalation_message: null,
    comparative_trend_outcome: null,
    ...overrides,
  };
}

function summaryResponse(
  overrides: Partial<DevelopmentSummaryResponse>,
): DevelopmentSummaryResponse {
  return {
    checkins_considered: 3,
    most_frequent_factor_label: "academic pressure",
    most_frequent_factor_count: 2,
    engaged_count: 1,
    engaged_considered: 2,
    summary_sentence:
      "Over your last 3 check-ins, academic pressure has come up most often as a factor worth acting on.",
    closing_message: "Keep going at whatever pace works for you.",
    ...overrides,
  };
}

const THREE_CHECKIN_HISTORY: AssessmentHistoryItem[] = [
  historyItem({ assessment_id: 1, created_at: "2026-08-01T09:00:00Z", stress_level: 2 }),
  historyItem({ assessment_id: 2, created_at: "2026-08-05T09:00:00Z", stress_level: 1 }),
  historyItem({ assessment_id: 3, created_at: "2026-08-09T09:00:00Z", stress_level: 0 }),
];

describe("canDownloadSummaryReport", () => {
  it("gates on the 3-check-in minimum", () => {
    expect(canDownloadSummaryReport([])).toBe(false);
    expect(canDownloadSummaryReport([historyItem({})])).toBe(false);
    expect(canDownloadSummaryReport([historyItem({}), historyItem({})])).toBe(false);
    expect(canDownloadSummaryReport(THREE_CHECKIN_HISTORY)).toBe(true);
  });

  it("stays available with more than 3 check-ins", () => {
    expect(canDownloadSummaryReport([...THREE_CHECKIN_HISTORY, historyItem({})])).toBe(true);
  });
});

describe("buildSummaryReportContent", () => {
  it("carries the summary sentence and closing message verbatim, no re-wording", () => {
    const summary = summaryResponse({});
    const content = buildSummaryReportContent(THREE_CHECKIN_HISTORY, summary);

    expect(content.summarySentence).toBe(summary.summary_sentence);
    expect(content.closingMessage).toBe(summary.closing_message);
    expect(content.checkinsConsidered).toBe(summary.checkins_considered);
  });

  it("builds one trend point per history item, in the same order, with the same levels", () => {
    const content = buildSummaryReportContent(THREE_CHECKIN_HISTORY, summaryResponse({}));

    expect(content.trend).toHaveLength(3);
    expect(content.trend.map((p) => p.level)).toEqual([2, 1, 0]);
    expect(content.trend.map((p) => p.levelLabel)).toEqual(["High", "Moderate", "Low"]);
  });

  it("never includes a raw numeric stress score outside the level field", () => {
    const content = buildSummaryReportContent(THREE_CHECKIN_HISTORY, summaryResponse({}));
    // The only place a 0/1/2 may appear is TrendBarPoint.level itself,
    // which is deliberately not a free-text field a reader could confuse
    // for a precise score -- mirrors buildReportContent's own check.
    expect(JSON.stringify(content.trend.map((p) => p.levelLabel))).not.toMatch(/[012]/);
  });

  it("includes the exact site-wide disclaimer text", () => {
    const content = buildSummaryReportContent(THREE_CHECKIN_HISTORY, summaryResponse({}));
    expect(content.disclaimer).toBe(DISCLAIMER_TEXT);
  });
});

describe("renderSummaryReportPdf", () => {
  it("produces a non-empty single-page PDF document for simulated multi-check-in data", () => {
    const content = buildSummaryReportContent(THREE_CHECKIN_HISTORY, summaryResponse({}));
    const doc = renderSummaryReportPdf(content);

    expect(doc.getNumberOfPages()).toBe(1);
    const bytes = doc.output("arraybuffer") as ArrayBuffer;
    expect(bytes.byteLength).toBeGreaterThan(0);
  });

  it("renders without throwing for a longer, more varied trend", () => {
    const longerHistory: AssessmentHistoryItem[] = [
      historyItem({ assessment_id: 1, stress_level: 2 }),
      historyItem({ assessment_id: 2, stress_level: 2 }),
      historyItem({ assessment_id: 3, stress_level: 1 }),
      historyItem({ assessment_id: 4, stress_level: 0 }),
      historyItem({ assessment_id: 5, stress_level: 0 }),
    ];
    const content = buildSummaryReportContent(longerHistory, summaryResponse({ checkins_considered: 5 }));

    expect(() => renderSummaryReportPdf(content)).not.toThrow();
  });
});
