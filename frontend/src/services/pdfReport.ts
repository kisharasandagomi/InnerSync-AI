/**
 * One-page PDF export of an already-generated check-in result.
 *
 * Every piece of body text here (explanation, escalation message,
 * affirmation, recommendation title/action) is placed VERBATIM from
 * `AssessmentResult` -- the same server-generated, safety-gated text
 * `ResultsPage` renders. This module does no wording, truncation, or
 * re-casing of its own beyond word-wrapping for the page width, matching
 * the same discipline `ResultsPage.tsx`'s module docstring describes. The
 * raw numeric stress score is never included, only `stress_level_label`.
 */
import { jsPDF } from "jspdf";
import type { AssessmentHistoryItem, AssessmentResult, DevelopmentSummaryResponse } from "./api";
import { DISCLAIMER_TEXT } from "./disclaimer";

export interface ReportContent {
  dateLabel: string;
  stressLevelLabel: string;
  explanation: string;
  /** Heading for the section below (varies: escalation / affirmation / next steps). */
  bodyHeading: string;
  /** Body paragraphs for that section, in order. For recommendations, one
   *  "N. Title" line followed by its action text, per item. */
  bodyParagraphs: string[];
  disclaimer: string;
}

/**
 * Pure assembly of report content from an assessment result. Kept separate
 * from PDF rendering so the actual field content (what text ends up in the
 * report) can be unit-tested without instantiating jsPDF.
 */
export function buildReportContent(result: AssessmentResult): ReportContent {
  const dateLabel = new Date(result.created_at).toLocaleString();

  let bodyHeading: string;
  let bodyParagraphs: string[];

  if (result.is_escalation && result.escalation_message) {
    bodyHeading = "Worth reaching out";
    bodyParagraphs = [result.escalation_message];
  } else if (result.is_affirmation && result.affirmation) {
    bodyHeading = "Suggested next steps";
    bodyParagraphs = [result.affirmation];
  } else {
    bodyHeading = "Suggested next steps";
    bodyParagraphs = result.recommendations.flatMap((rec) => [
      `${rec.priority}. ${rec.title}`,
      rec.action,
    ]);
  }

  return {
    dateLabel,
    stressLevelLabel: result.stress_level_label,
    explanation: result.explanation,
    bodyHeading,
    bodyParagraphs,
    disclaimer: DISCLAIMER_TEXT,
  };
}

/** Renders `content` into a one-page jsPDF document. */
export function renderReportPdf(content: ReportContent): jsPDF {
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const marginX = 48;
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const contentWidth = pageWidth - marginX * 2;
  let y = 56;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text("InnerSync AI - Wellbeing Check-in Report", marginX, y);
  y += 26;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.text(`Date: ${content.dateLabel}`, marginX, y);
  y += 22;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.text(`Stress level: ${content.stressLevelLabel}`, marginX, y);
  y += 22;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.text("What this means", marginX, y);
  y += 16;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  const explanationLines: string[] = doc.splitTextToSize(content.explanation, contentWidth);
  doc.text(explanationLines, marginX, y);
  y += explanationLines.length * 13 + 14;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.text(content.bodyHeading, marginX, y);
  y += 16;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  for (const paragraph of content.bodyParagraphs) {
    const lines: string[] = doc.splitTextToSize(paragraph, contentWidth);
    doc.text(lines, marginX, y);
    y += lines.length * 13 + 8;
  }

  doc.setFont("helvetica", "italic");
  doc.setFontSize(8);
  const disclaimerLines: string[] = doc.splitTextToSize(content.disclaimer, contentWidth);
  const disclaimerY = pageHeight - 30 - (disclaimerLines.length - 1) * 10;
  doc.text(disclaimerLines, marginX, disclaimerY);

  return doc;
}

/** Builds and triggers a browser download of the report PDF. UI entry point. */
export function downloadAssessmentReport(result: AssessmentResult): void {
  const content = buildReportContent(result);
  const doc = renderReportPdf(content);
  const dateStamp = new Date(result.created_at).toISOString().slice(0, 10);
  doc.save(`innersync-checkin-report-${dateStamp}.pdf`);
}

// ---------------------------------------------------------------------------
// Multi-check-in development summary report (round 8)
//
// Deliberately "the development summary, as a downloadable PDF" -- reuses
// this same module's page-building primitives (marginX/contentWidth/y
// cursor, splitTextToSize wrapping) and, for content, the exact same two
// data sources already on the Progress page: `AssessmentHistoryItem[]` (the
// trend bars, mirroring ProgressPage.tsx's own bar chart) and
// `DevelopmentSummaryResponse` (the synthesis sentence and closing message,
// from `GET /assessments/summary` -- see `app.services.development_summary`).
// No new aggregation, wording, or charting logic is introduced here.
// ---------------------------------------------------------------------------

const MIN_CHECKINS_FOR_SUMMARY_REPORT = 3;

export interface TrendBarPoint {
  dateLabel: string;
  levelLabel: string;
  /** 0 low, 1 moderate, 2 high -- same encoding as `AssessmentHistoryItem.stress_level`. */
  level: 0 | 1 | 2;
}

export interface SummaryReportContent {
  dateLabel: string;
  checkinsConsidered: number;
  trend: TrendBarPoint[];
  summarySentence: string;
  closingMessage: string;
  disclaimer: string;
}

/** Same three-word mapping `ProgressPage.tsx`'s `levelWord` uses, kept in
 *  sync by convention rather than a shared import (a services module and a
 *  page module deliberately don't depend on each other here). */
function levelLabel(level: 0 | 1 | 2): string {
  return level === 0 ? "Low" : level === 1 ? "Moderate" : "High";
}

/**
 * Whether a student has enough history for the multi-check-in summary
 * report to be offered at all. The single gate `ProgressPage.tsx` checks
 * before showing the download button.
 */
export function canDownloadSummaryReport(history: AssessmentHistoryItem[]): boolean {
  return history.length >= MIN_CHECKINS_FOR_SUMMARY_REPORT;
}

/**
 * Pure assembly of the summary report's content from data already fetched
 * by the Progress page -- kept separate from PDF rendering for the same
 * unit-testability reason `buildReportContent` above is.
 */
export function buildSummaryReportContent(
  history: AssessmentHistoryItem[],
  summary: DevelopmentSummaryResponse,
): SummaryReportContent {
  return {
    dateLabel: new Date().toLocaleString(),
    checkinsConsidered: summary.checkins_considered,
    trend: history.map((item) => ({
      dateLabel: new Date(item.created_at).toLocaleDateString(),
      levelLabel: levelLabel(item.stress_level),
      level: item.stress_level,
    })),
    summarySentence: summary.summary_sentence,
    closingMessage: summary.closing_message,
    disclaimer: DISCLAIMER_TEXT,
  };
}

/** Renders `content` into a one-page jsPDF document, including a simple bar
 *  trend chart mirroring the one on the Progress page (three fixed bar
 *  heights by level, single accent colour at three intensities -- never
 *  red/amber/green, the same "colour is not load-bearing" rule
 *  `ProgressPage.tsx`'s module docstring documents for the on-screen
 *  version). */
export function renderSummaryReportPdf(content: SummaryReportContent): jsPDF {
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const marginX = 48;
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const contentWidth = pageWidth - marginX * 2;
  let y = 56;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text("InnerSync AI - Development Summary Report", marginX, y);
  y += 26;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.text(`Generated: ${content.dateLabel}`, marginX, y);
  y += 16;
  doc.text(`Based on your last ${content.checkinsConsidered} check-ins`, marginX, y);
  y += 30;

  // --- Trend bars -----------------------------------------------------
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.text("How things have been trending", marginX, y);
  y += 20;

  const barWidth = 22;
  const barGap = 14;
  const chartBaseY = y + 70;
  const barColorByLevel: Record<0 | 1 | 2, [number, number, number]> = {
    0: [201, 154, 46], // accent-soft equivalent, lightest
    1: [180, 130, 30], // accent, mid
    2: [122, 88, 18], // accent-strong, darkest -- still gold-family, not red
  };
  const barHeightByLevel: Record<0 | 1 | 2, number> = { 0: 18, 1: 40, 2: 62 };

  content.trend.forEach((point, i) => {
    const x = marginX + i * (barWidth + barGap);
    const barHeight = barHeightByLevel[point.level];
    const [r, g, b] = barColorByLevel[point.level];
    doc.setFillColor(r, g, b);
    doc.rect(x, chartBaseY - barHeight, barWidth, barHeight, "F");

    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    doc.text(point.levelLabel, x + barWidth / 2, chartBaseY - barHeight - 4, {
      align: "center",
    });
    doc.text(point.dateLabel, x + barWidth / 2, chartBaseY + 12, { align: "center" });
  });
  y = chartBaseY + 30;

  // --- Synthesis and closing message -----------------------------------
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.text("What your check-ins suggest", marginX, y);
  y += 16;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  const summaryLines: string[] = doc.splitTextToSize(content.summarySentence, contentWidth);
  doc.text(summaryLines, marginX, y);
  y += summaryLines.length * 13 + 16;

  doc.setFont("helvetica", "italic");
  doc.setFontSize(10);
  const closingLines: string[] = doc.splitTextToSize(content.closingMessage, contentWidth);
  doc.text(closingLines, marginX, y);

  doc.setFont("helvetica", "italic");
  doc.setFontSize(8);
  const disclaimerLines: string[] = doc.splitTextToSize(content.disclaimer, contentWidth);
  const disclaimerY = pageHeight - 30 - (disclaimerLines.length - 1) * 10;
  doc.text(disclaimerLines, marginX, disclaimerY);

  return doc;
}

/**
 * Builds and triggers a browser download of the development summary
 * report. UI entry point, gated by `canDownloadSummaryReport` -- callers
 * (`ProgressPage.tsx`) should not render the button at all below the
 * 3-check-in minimum, but this function itself does not re-check it, the
 * same "the caller decides visibility, the builder just builds" split
 * `downloadAssessmentReport` already follows.
 */
export function downloadSummaryReport(
  history: AssessmentHistoryItem[],
  summary: DevelopmentSummaryResponse,
): void {
  const content = buildSummaryReportContent(history, summary);
  const doc = renderSummaryReportPdf(content);
  const dateStamp = new Date().toISOString().slice(0, 10);
  doc.save(`innersync-development-summary-${dateStamp}.pdf`);
}
