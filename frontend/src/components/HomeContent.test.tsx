import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HomeContent } from "./HomeContent";

/**
 * Guards round 5's specific requirement: the two crisis-line numbers
 * repeated inside "You are not alone, and help works" must exactly match
 * the full Sri Lanka mental health support directory further down the same
 * page, with zero transcription drift. HomeContent.tsx sources both from
 * the same DIRECTORY array by construction; this test is the check that
 * guarantee actually holds in the rendered output.
 */
describe("HomeContent crisis-line numbers", () => {
  it("renders the NIMH number identically in the article and the full directory", () => {
    render(<HomeContent />);
    const matches = screen.getAllByText("1926 (24/7, free, call or SMS)");
    expect(matches).toHaveLength(2);
  });

  it("renders the NIMH WhatsApp number identically in the article and the full directory", () => {
    render(<HomeContent />);
    const matches = screen.getAllByText("WhatsApp 075 555 1926");
    expect(matches).toHaveLength(2);
  });

  it("renders the Sumithrayo number identically in the article and the full directory", () => {
    render(<HomeContent />);
    const matches = screen.getAllByText("+94 11 269 2909");
    expect(matches).toHaveLength(2);
  });

  it("renders the sensitive article's heading and the full directory heading", () => {
    render(<HomeContent />);
    expect(screen.getByText("You are not alone, and help works")).toBeInTheDocument();
    expect(
      screen.getByText("Sri Lanka mental health support directory"),
    ).toBeInTheDocument();
  });

  it("contains no em-dash anywhere in the rendered content", () => {
    const { container } = render(<HomeContent />);
    expect(container.textContent).not.toMatch(/—/);
  });
});
