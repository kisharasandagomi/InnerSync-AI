import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MoodAvatar, type MoodLevel } from "./MoodAvatar";

function renderMarkup(level: MoodLevel | null): string {
  const { container } = render(<MoodAvatar level={level} />);
  return container.innerHTML;
}

/**
 * Round 6 bug 4 regression guard. The actual mapping code in MoodAvatar.tsx
 * was already correct on inspection (distinct eyebrow/mouth paths per
 * level); the real bug was in Layout.tsx, which fetched the "most recent
 * check-in" once per sign-in and never refetched, so a check-in submitted
 * mid-session never updated the avatar (see Layout.tsx's fixed effect).
 * These tests guard the mapping function itself directly, at the markup
 * level, not just via aria-label text -- a bug that left two levels
 * visually identical while still labelling them differently would not be
 * caught by an aria-label-only check.
 */
describe("MoodAvatar level -> expression mapping", () => {
  it("renders three pairwise-different markups for low, moderate, and high", () => {
    const low = renderMarkup(0);
    const moderate = renderMarkup(1);
    const high = renderMarkup(2);

    expect(low).not.toBe(moderate);
    expect(moderate).not.toBe(high);
    expect(low).not.toBe(high);
  });

  it("gives each level its own distinct mouth shape", () => {
    // The calm smile, the moderate curve, and the high "o" are three
    // different SVG shapes with different endpoint coordinates -- if a
    // future edit ever collapsed two of these to the same path, this test
    // catches it directly rather than relying on the label text alone.
    expect(renderMarkup(0)).toContain("M16.5 27 Q20 30 23.5 27");
    expect(renderMarkup(1)).toContain("M17 27.5 Q20 28.5 23 27.5");
    expect(renderMarkup(2)).toContain("<ellipse");

    expect(renderMarkup(0)).not.toContain("<ellipse");
    expect(renderMarkup(1)).not.toContain("<ellipse");
    expect(renderMarkup(2)).not.toContain("M17 27.5 Q20 28.5 23 27.5");
  });

  it("only adds eyebrows for the high (caring) expression, not moderate", () => {
    expect(renderMarkup(0)).not.toContain("M13 18.5");
    expect(renderMarkup(1)).not.toContain("M13 18.5");
    expect(renderMarkup(2)).toContain("M13 18.5");
  });

  it("gives each level a distinct, non-alarming aria-label", () => {
    const low = render(<MoodAvatar level={0} />).container.querySelector("svg");
    const moderate = render(<MoodAvatar level={1} />).container.querySelector("svg");
    const high = render(<MoodAvatar level={2} />).container.querySelector("svg");

    const labels = [
      low?.getAttribute("aria-label"),
      moderate?.getAttribute("aria-label"),
      high?.getAttribute("aria-label"),
    ];
    expect(new Set(labels).size).toBe(3);
  });

  it("falls back to the calm face (not an alarming placeholder) when there is no check-in yet", () => {
    // No check-ins yet still uses the level-0 (calm) mouth shape -- only the
    // label text differs ("Say hello" vs "Feeling calm") -- rather than any
    // separate, potentially alarming "no data" graphic.
    expect(renderMarkup(null)).toContain("M16.5 27 Q20 30 23.5 27");
  });
});
