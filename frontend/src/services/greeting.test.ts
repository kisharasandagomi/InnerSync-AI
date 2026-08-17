import { describe, expect, it } from "vitest";
import { checkinGreeting, resolveGreetingName } from "./greeting";

describe("resolveGreetingName", () => {
  it("uses the display name when set", () => {
    expect(resolveGreetingName("Sam", "sam.k@example.ac.uk")).toBe("Sam");
  });

  it("falls back to the email's local part when unset", () => {
    expect(resolveGreetingName(null, "sam.k@example.ac.uk")).toBe("sam.k");
  });

  it("falls back when the display name is blank/whitespace-only", () => {
    expect(resolveGreetingName("   ", "sam.k@example.ac.uk")).toBe("sam.k");
  });

  it("trims surrounding whitespace from a real name", () => {
    expect(resolveGreetingName("  Sam  ", "sam.k@example.ac.uk")).toBe("Sam");
  });

  it("never returns a blank string, even for an edge-case email", () => {
    expect(resolveGreetingName(null, "x@example.ac.uk")).toBe("x");
  });
});

describe("checkinGreeting", () => {
  it("builds the fixed template with the resolved name", () => {
    expect(checkinGreeting("Sam", "sam.k@example.ac.uk")).toBe(
      "Hi Sam, ready for your check-in?",
    );
  });

  it("uses the email fallback in the same template when no name is set", () => {
    expect(checkinGreeting(null, "sam.k@example.ac.uk")).toBe(
      "Hi sam.k, ready for your check-in?",
    );
  });
});
