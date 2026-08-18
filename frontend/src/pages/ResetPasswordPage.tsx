import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, resetPassword } from "../services/api";

/**
 * Reached from the emailed reset link (`/reset-password?token=...`).
 * The token itself is opaque here -- validity, expiry, and single-use are
 * all enforced server-side (see `backend/app/api/auth.py`'s
 * `reset_password`); this page just forwards it with the new password.
 */
export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await resetPassword(token, newPassword);
      setDone(true);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not reach the server. Is the backend running?",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <div className="mx-auto max-w-sm">
        <h1 className="text-xl font-semibold tracking-tight text-ink">
          Reset link missing
        </h1>
        <p className="mt-2 text-base leading-relaxed text-ink-soft">
          This page needs a reset link from your email. Please use the link
          from the password reset email, or request a new one.
        </p>
        <Link
          to="/"
          className="mt-4 inline-block text-sm font-medium text-ink underline underline-offset-2 hover:text-accent-strong"
        >
          Back to sign in
        </Link>
      </div>
    );
  }

  if (done) {
    return (
      <div className="mx-auto max-w-sm">
        <h1 className="text-xl font-semibold tracking-tight text-ink">
          Password updated
        </h1>
        <p className="mt-2 text-base leading-relaxed text-ink-soft">
          Your password has been changed. You can now sign in with your new
          password.
        </p>
        <Link
          to="/"
          className="mt-4 inline-block rounded-md bg-accent px-4 py-2.5 text-base font-medium text-ink transition-colors hover:bg-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          Go to sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="text-xl font-semibold tracking-tight text-ink">
        Choose a new password
      </h1>
      <p className="mt-2 text-base leading-relaxed text-ink-soft">
        This reset link is single-use and expires shortly after it was sent.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
        <div>
          <label htmlFor="new-password" className="block text-base font-medium text-ink">
            New password
          </label>
          <input
            id="new-password"
            name="new_password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            maxLength={72}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="mt-1 w-full rounded-md border border-line bg-card px-3 py-2 text-base text-ink focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          />
          <p className="mt-1 text-sm text-ink-faint">At least 8 characters.</p>
        </div>

        {error && (
          <p role="alert" className="text-base text-danger">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-md bg-accent px-4 py-2.5 text-base font-medium text-ink transition-colors hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          {busy ? "Updating…" : "Update password"}
        </button>
      </form>
    </div>
  );
}
