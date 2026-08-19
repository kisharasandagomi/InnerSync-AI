import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AuthPage } from "./AuthPage";
import { AuthProvider } from "../services/auth";

function renderAuthPage() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <AuthPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

/**
 * Round 5 item 1: the public entry point is now a welcome screen with two
 * buttons, not straight to the sign-in form. Guards that both buttons
 * actually reach their respective form, and that the homepage content
 * (articles, crisis directory) is visible on the welcome screen itself
 * without needing either button clicked.
 */
describe("AuthPage welcome screen", () => {
  it("shows a welcome screen with Sign In and Create Account buttons by default", () => {
    renderAuthPage();
    expect(screen.getByText("Welcome to InnerSync AI")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign In" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create Account" })).toBeInTheDocument();
    // Neither form's fields are shown yet -- only reachable via a button.
    expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
  });

  it("shows the homepage content on the welcome screen without any interaction", () => {
    renderAuthPage();
    expect(
      screen.getByText("Sri Lanka mental health support directory"),
    ).toBeInTheDocument();
    expect(screen.getByText("How this works")).toBeInTheDocument();
  });

  it("Sign In navigates to the login form", async () => {
    const user = userEvent.setup();
    renderAuthPage();

    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    // Register-only fields must not appear on the login form.
    expect(screen.queryByLabelText(/What should we call you/)).not.toBeInTheDocument();
  });

  it("Create Account navigates to the registration form", async () => {
    const user = userEvent.setup();
    renderAuthPage();

    await user.click(screen.getByRole("button", { name: "Create Account" }));

    expect(screen.getByRole("heading", { name: "Create an account" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText(/What should we call you/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Something you enjoy doing/)).toBeInTheDocument();
  });

  it("the homepage content stays visible after navigating into either form", async () => {
    const user = userEvent.setup();
    renderAuthPage();

    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(
      screen.getByText("Sri Lanka mental health support directory"),
    ).toBeInTheDocument();
  });
});
