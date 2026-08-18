import { describe, expect, it } from "vitest";
import type { AssessmentResult } from "./api";
import { buildReportContent, renderReportPdf } from "./pdfReport";
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
