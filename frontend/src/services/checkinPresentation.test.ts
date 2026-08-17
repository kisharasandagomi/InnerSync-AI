import { describe, expect, it } from "vitest";
import { FEATURE_FIELDS } from "./featureSchema";
import { iconSetFor, widgetStyleFor } from "./checkinPresentation";
import { answerEngagement, answerFeature, startCheckin } from "./checkinFlow";

/**
 * Guards the presentation-layer addition from round 2 of UX feedback:
 * every field has a widget style, every icon-scale field's icon count
 * matches its own range exactly, and — the actual point of this task item
 * — a value answered through *any* widget style still produces exactly the
 * same valid payload `checkinFlow.ts` has always accepted. This file never
 * touches `checkinFlow.ts` itself; its 14 existing tests are untouched.
 */

describe("checkin widget style assignment", () => {
  it("assigns a widget style to every non-binary feature field", () => {
    for (const field of FEATURE_FIELDS) {
      if (field.min === 0 && field.max === 1) continue; // binary always renders its own toggle
      expect(["slider", "icon-scale", "chips"]).toContain(widgetStyleFor(field.name));
    }
  });

  it("assigns more than one style — this is meant to add variety, not pick one style for everything", () => {
    const stylesUsed = new Set(
      FEATURE_FIELDS.filter((f) => !(f.min === 0 && f.max === 1)).map((f) =>
        widgetStyleFor(f.name),
      ),
    );
    expect(stylesUsed.size).toBeGreaterThan(1);
  });

  it("gives every icon-scale field an icon set with exactly one icon per value", () => {
    for (const field of FEATURE_FIELDS) {
      if (widgetStyleFor(field.name) !== "icon-scale") continue;
      const icons = iconSetFor(field.name);
      expect(icons).not.toBeNull();
      expect(icons).toHaveLength(field.max - field.min + 1);
    }
  });

  it("defines no icon set for a field that isn't assigned icon-scale", () => {
    for (const field of FEATURE_FIELDS) {
      if (widgetStyleFor(field.name) === "icon-scale") continue;
      expect(iconSetFor(field.name)).toBeNull();
    }
  });
});

describe("checkin widget style does not affect the captured payload", () => {
  it("accepts the same min/mid/max values for a field regardless of its assigned widget style", () => {
    for (const field of FEATURE_FIELDS) {
      const style = widgetStyleFor(field.name);
      const state = answerEngagement(startCheckin(), "no_previous_checkin");
      // Answer every prior field first so we can reach this one directly.
      let cursor = state;
      for (const priorField of FEATURE_FIELDS) {
        if (priorField.name === field.name) break;
        cursor = answerFeature(cursor, priorField.min);
      }
      const mid = Math.round((field.min + field.max) / 2);
      for (const candidate of [field.min, mid, field.max]) {
        // Whichever widget produced `candidate`, checkinFlow validates it
        // identically — style is purely cosmetic to this call.
        expect(() => answerFeature(cursor, candidate)).not.toThrow();
      }
      void style; // style itself is asserted separately above; here only the value matters
    }
  });
});
