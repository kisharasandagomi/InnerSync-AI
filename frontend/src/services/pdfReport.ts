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
import type { AssessmentResult } from "./api";
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
