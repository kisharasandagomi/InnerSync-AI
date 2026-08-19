import { useEffect } from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { LandingPage } from "./LandingPage";
import { AuthProvider, useAuth } from "../services/auth";

/** Signs into the real AuthContext on mount, then renders LandingPage --
 *  exercises the actual component tree rather than a hand-built fixture. */
function SignedInLandingPage({
  email,
  displayName,
}: {
  email: string;
  displayName: string | null;
}) {
  const { signIn } = useAuth();
  useEffect(() => {
    signIn("fake-token", email, displayName);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return <LandingPage />;
}

function renderSignedIn(email: string, displayName: string | null) {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <SignedInLandingPage email={email} displayName={displayName} />
      </AuthProvider>
    </MemoryRouter>,
  );
}

/**
 * Round 6 bug 3 regression guard. Root cause: this page used to interpolate
 * the raw `email` from useAuth() directly into "Welcome back, ..." instead
 * of calling resolveGreetingName -- resolveGreetingName itself was never
 * the problem (see greeting.test.ts, unchanged and already passing). These
 * tests fail if that raw-email shortcut is ever reintroduced.
 */
describe("LandingPage greeting", () => {
  it("greets by display name when one is set", async () => {
    renderSignedIn("ksbusiness.world1@gmail.com", "kisha");
    expect(await screen.findByText("Welcome back, kisha")).toBeInTheDocument();
  });

  it("falls back to the email's local part when no display name is set", async () => {
    renderSignedIn("ksbusiness.world1@gmail.com", null);
    expect(await screen.findByText("Welcome back, ksbusiness.world1")).toBeInTheDocument();
  });

  it("never renders the full email address as the greeting", async () => {
    renderSignedIn("ksbusiness.world1@gmail.com", null);
    await screen.findByText("Welcome back, ksbusiness.world1");
    expect(screen.queryByText(/Welcome back, ksbusiness\.world1@gmail\.com/)).not.toBeInTheDocument();
  });
});
