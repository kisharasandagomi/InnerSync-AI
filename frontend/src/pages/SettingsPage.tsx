import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, deactivateAccount } from "../services/api";
import { useAuth } from "../services/auth";

/**
 * Account settings (round 4): currently just deactivation.
 *
 * Deactivation is soft-delete only (see `backend/app/api/auth.py`'s
 * `deactivate_account` and `docs/governance/data_management_plan.md`'s
 * retention section) -- the account can no longer log in afterward, but no
 * data is removed. Requires re-entering the current password, the same
 * confirmation pattern any destructive account action should use.
 */
export function SettingsPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

  const { token, signOut } = useAuth();
  const navigate = useNavigate();

  async function handleDeactivate(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    setError(null);
    setBusy(true);
    try {
      await deactivateAccount(password, token);
      // Logged out immediately: the account can no longer authenticate
      // anyway (see get_current_user's is_active check), so there is
      // nothing left for this session to do but clear local state.
      signOut();
      navigate("/");
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

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="text-xl font-semibold tracking-tight text-ink">
        Account settings
      </h1>

      <section className="mt-8 rounded-lg border border-line bg-card p-6">
        <h2 className="text-base font-semibold tracking-tight text-ink">
          Deactivate account
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">
          This signs you out and stops you from logging back in. Your past
          check-ins are kept, not deleted, in line with our data retention
          approach. If you want your data removed entirely, contact us
          separately.
        </p>

        {!confirming ? (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className="mt-4 rounded-md border border-danger px-4 py-2 text-sm font-medium text-danger transition-colors hover:bg-danger/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            Deactivate account
          </button>
        ) : (
          <form onSubmit={handleDeactivate} className="mt-4 space-y-3" noValidate>
            <div>
              <label
                htmlFor="deactivate-password"
                className="block text-sm font-medium text-ink"
              >
                Confirm your password to continue
              </label>
              <input
                id="deactivate-password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-md border border-line bg-card px-3 py-2 text-base text-ink focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              />
            </div>

            {error && (
              <p role="alert" className="text-sm text-danger">
                {error}
              </p>
            )}

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={busy || !password}
                className="rounded-md bg-danger px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
              >
                {busy ? "Deactivating…" : "Confirm deactivation"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setConfirming(false);
                  setPassword("");
                  setError(null);
                }}
                className="rounded-md border border-line px-4 py-2 text-sm text-ink-soft transition-colors hover:bg-accent-soft focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  );
}
