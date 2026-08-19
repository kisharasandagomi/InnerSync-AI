import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ResourcesPage } from "./ResourcesPage";
import { HomeContent } from "../components/HomeContent";

/**
 * Round 6 item 2: the post-login Resources page must render the exact same
 * HomeContent component the public sign-in page uses, not a second copy of
 * its text. Comparing the two components' rendered markup directly (not
 * just checking a few strings appear) is the strongest guard against a
 * future fork -- if anyone ever pastes a duplicate/edited copy of the
 * articles into ResourcesPage instead of importing HomeContent, this fails.
 */
describe("ResourcesPage reuses HomeContent", () => {
  it("renders markup identical to a standalone HomeContent, byte for byte", () => {
    const { container: resourcesContainer } = render(<ResourcesPage />);
    const { container: homeContentContainer } = render(<HomeContent />);

    const resourcesHomeContentMarkup =
      resourcesContainer.querySelector('[class*="max-w-3xl"]')?.outerHTML;
    expect(resourcesHomeContentMarkup).toBe(homeContentContainer.firstElementChild?.outerHTML);
  });

  it("includes the crisis directory and sensitive article, reachable while signed in", () => {
    render(<ResourcesPage />);
    expect(
      screen.getByText("Sri Lanka mental health support directory"),
    ).toBeInTheDocument();
    expect(screen.getByText("You are not alone, and help works")).toBeInTheDocument();
  });

  it("has its own page heading distinct from the public sign-in page's copy", () => {
    render(<ResourcesPage />);
    expect(screen.getByRole("heading", { name: "Articles and support" })).toBeInTheDocument();
  });
});
