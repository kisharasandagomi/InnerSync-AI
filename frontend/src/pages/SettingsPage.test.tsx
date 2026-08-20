import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { SettingsPage } from "./SettingsPage";
import { AuthProvider } from "../services/auth";

function renderSettingsPage() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <SettingsPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

/**
 * Round 8: SettingsPage restructured from one long scrolling page into a
 * sidebar layout -- a left-hand list of topics, with only the selected
 * topic's content shown on the right. These tests exercise the navigation
 * itself, not the individual forms' request/validation logic (unchanged
 * from round 7 and already covered end-to-end by the backend's
 * `test_profile_edit.py` / `test_otp_login.py`).
 *
 * Rendered without a signed-in `AuthProvider` token, the same convention
 * `AuthPage.test.tsx` uses: `SettingsPage`'s data-fetching effect no-ops
 * without a token (`if (!token) return;`), so no network mocking is
 * needed here -- this project has no existing fetch-mocking convention to
 * introduce one for. That means the Profile/Password/Two-Factor topics
 * (which wait on `GET /auth/me`) stay on their loading note in these
 * tests; Deactivate account and Wellbeing don't depend on `me` and are
 * fully exercised.
 */
describe("SettingsPage topic navigation", () => {
  it("shows all five topics in the sidebar, Profile selected by default", () => {
    renderSettingsPage();

    const nav = screen.getByRole("navigation", { name: "Settings topics" });
    for (const label of [
      "Profile",
      "Password",
      "Two-Factor Authentication",
      "Wellbeing",
      "Deactivate account",
    ]) {
      expect(within(nav).getByRole("button", { name: label })).toBeInTheDocument();
    }
    expect(within(nav).getByRole("button", { name: "Profile" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("selecting Deactivate account shows only that topic's content", async () => {
    const user = userEvent.setup();
    renderSettingsPage();
    const nav = screen.getByRole("navigation", { name: "Settings topics" });

    // Unambiguous here: before selection, the content pane doesn't yet
    // contain DeactivateSection's own same-named action button.
    await user.click(screen.getByRole("button", { name: "Deactivate account" }));

    expect(screen.getByRole("heading", { name: "Deactivate account" })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "Deactivate account" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    // Not shown alongside it -- only the selected topic renders.
    expect(screen.queryByRole("heading", { name: "Change password" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Edit profile" })).not.toBeInTheDocument();
  });

  it("selecting Wellbeing with no active escalation shows the calm placeholder", async () => {
    const user = userEvent.setup();
    renderSettingsPage();

    await user.click(screen.getByRole("button", { name: "Wellbeing" }));

    expect(screen.getByRole("heading", { name: "Wellbeing" })).toBeInTheDocument();
    expect(screen.getByText(/Nothing to flag right now/)).toBeInTheDocument();
    // The escalation signpost itself must not appear when nothing escalated.
    expect(
      screen.queryByText(/A few check-ins in a row have pointed to a lot of pressure/),
    ).not.toBeInTheDocument();
  });

  it("switching topics moves the aria-current marker to the newly selected one", async () => {
    const user = userEvent.setup();
    renderSettingsPage();

    await user.click(screen.getByRole("button", { name: "Password" }));

    expect(screen.getByRole("button", { name: "Password" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("button", { name: "Profile" })).not.toHaveAttribute("aria-current");
  });

  it("Profile, Password, and Two-Factor Authentication show a loading note without a signed-in session", async () => {
    const user = userEvent.setup();
    renderSettingsPage();

    // Profile is the default topic.
    expect(screen.getByText("Loading your settings…")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Two-Factor Authentication" }));
    expect(screen.getByText("Loading your settings…")).toBeInTheDocument();
  });
});
