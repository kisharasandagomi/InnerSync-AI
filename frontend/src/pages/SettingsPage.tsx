import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ApiError,
  changePassword,
  deactivateAccount,
  getEscalationStatus,
  getMe,
  updateDisplayName,
  updateOtpSetting,
  type MeResponse,
} from "../services/api";
import { NIMH_ENTRY, SUMITHRAYO_ENTRY } from "../components/HomeContent";
import { useAuth } from "../services/auth";

/** One left-hand navigation topic. `"deactivate"` is not in the requested
 *  Profile / Password / Two-Factor Authentication / Wellbeing list but is
 *  kept as its own topic so the existing deactivation flow stays reachable
 *  -- omitting it would silently remove functionality rather than just
 *  relayout it. */
type SettingsTopic = "profile" | "password" | "2fa" | "wellbeing" | "deactivate";

const SETTINGS_TOPICS: { id: SettingsTopic; label: string }[] = [
  { id: "profile", label: "Profile" },
  { id: "password", label: "Password" },
  { id: "2fa", label: "Two-Factor Authentication" },
  { id: "wellbeing", label: "Wellbeing" },
  { id: "deactivate", label: "Deactivate account" },
];

/**
 * Account settings.
 *
 * Round 8: restructured from one long scrolling page into a sidebar layout
 * -- a left-hand list of topics, with only the selected topic's fields
 * shown on the right. Layout only: every field, form, request, and
 * validation rule below is unchanged from round 7, just mounted inside
 * `SettingsTopicContent` instead of stacked directly on the page. Reuses
 * this page's existing card styling (`border-line`/`bg-card` sections,
 * `border-accent`/`bg-accent-soft` for the selected nav item, matching
 * `TwoFactorSection`'s own on/off button treatment) rather than introducing
 * new visual language.
 *
 * Round 7 added edit-profile (display name, in-session password change), an
 * opt-in email one-time-code sign-in toggle, and the persistent wellbeing
 * signpost, all above the existing deactivation section. `me` is loaded
 * fresh from `GET /auth/me` on mount rather than trusted from the
 * login-time snapshot on `AuthContext`, so a value changed in another tab or
 * a page reload never shows stale state here (see `MeResponse`'s docstring).
 *
 * Deactivation is unchanged from round 4: soft-delete only (see
 * `backend/app/api/auth.py`'s `deactivate_account` and
 * `docs/governance/data_management_plan.md`'s retention section) -- the
 * account can no longer log in afterward, but no data is removed. Requires
 * re-entering the current password, the same confirmation pattern edit
 * profile's password change and deactivation both use. Deliberately not
 * gated on `me` being loaded (unlike the profile/password/2FA topics
 * below), the same as before this round's restructure -- deactivation only
 * needs `token`, not the fetched profile.
 */
export function SettingsPage() {
  const { token, signOut } = useAuth();
  const navigate = useNavigate();

  const [me, setMe] = useState<MeResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  // Fetched independently of `me` (its own endpoint, GET
  // /assessments/escalation-status), the same pattern ProgressPage's
  // devSummary already uses -- a failure here must not block the rest of
  // Settings from loading, and this section's own visibility does not
  // depend on the edit-profile/2FA sections being ready.
  const [escalating, setEscalating] = useState(false);
  const [activeTopic, setActiveTopic] = useState<SettingsTopic>("profile");

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    getMe(token)
      .then((result) => {
        if (!cancelled) setMe(result);
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(
          err instanceof ApiError
            ? err.message
            : "Could not reach the server. Is the backend running?",
        );
      });
    getEscalationStatus(token)
      .then((result) => {
        if (!cancelled) setEscalating(result.is_escalation);
      })
      .catch(() => {
        // Non-critical: if this fails to load, the signpost simply does not
        // show this time rather than breaking the rest of the page. It will
        // be re-checked the next time this page mounts.
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-xl font-semibold tracking-tight text-ink">
        Account settings
      </h1>

      {/* Persistent regardless of which topic is selected below -- see
          WellbeingSignpostSection's own docstring for why this must not be
          gated behind navigation (no dismiss control, must stay visible
          until a later check-in no longer escalates). The "Wellbeing" nav
          topic below additionally surfaces the same content on demand. */}
      {escalating && <WellbeingSignpostSection />}

      {loadError && (
        <p className="mt-6 rounded-lg border border-line bg-card p-4 text-sm text-ink-soft">
          {loadError}
        </p>
      )}

      <div className="mt-6 flex flex-col gap-6 md:flex-row md:items-start">
        <nav
          aria-label="Settings topics"
          className="flex shrink-0 gap-2 overflow-x-auto md:w-56 md:flex-col md:overflow-visible"
        >
          {SETTINGS_TOPICS.map((topic) => (
            <button
              key={topic.id}
              type="button"
              onClick={() => setActiveTopic(topic.id)}
              aria-current={activeTopic === topic.id ? "page" : undefined}
              className={`shrink-0 rounded-md border px-4 py-2 text-left text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                activeTopic === topic.id
                  ? "border-accent bg-accent-soft text-ink"
                  : "border-line text-ink-soft hover:bg-accent-soft"
              }`}
            >
              {topic.label}
            </button>
          ))}
        </nav>

        <div className="min-w-0 flex-1">
          {activeTopic === "profile" &&
            (!loadError && me !== null && token ? (
              <EditProfileSection token={token} me={me} onUpdated={setMe} />
            ) : (
              <SettingsLoadingNote />
            ))}

          {activeTopic === "password" &&
            (!loadError && me !== null && token ? (
              <ChangePasswordSection token={token} />
            ) : (
              <SettingsLoadingNote />
            ))}

          {activeTopic === "2fa" &&
            (!loadError && me !== null && token ? (
              <TwoFactorSection token={token} me={me} onUpdated={setMe} />
            ) : (
              <SettingsLoadingNote />
            ))}

          {activeTopic === "wellbeing" && <WellbeingTopicContent escalating={escalating} />}

          {activeTopic === "deactivate" && (
            <DeactivateSection token={token} signOut={signOut} navigate={navigate} />
          )}
        </div>
      </div>
    </div>
  );
}

/** Shown in the content pane while `me` is still loading (or failed to),
 *  for the topics that need it -- the exact same "Loading your settings…"
 *  wording the single-page layout showed before this round. */
function SettingsLoadingNote() {
  return <p className="text-sm text-ink-faint">Loading your settings…</p>;
}

/** The "Wellbeing" nav topic's content: the same signpost when escalating
 *  (so it stays reachable even after a student scrolls past the persistent
 *  banner above), or a calm explanation of what this section is for
 *  otherwise. Never a separate escalation calculation -- `escalating` is
 *  the same prop `SettingsPage` already fetched once. */
function WellbeingTopicContent({ escalating }: { escalating: boolean }) {
  if (escalating) {
    return <WellbeingSignpostSection />;
  }
  return (
    <section className="rounded-lg border border-line bg-card p-6">
      <h2 className="text-base font-semibold tracking-tight text-ink">Wellbeing</h2>
      <p className="mt-2 text-sm leading-relaxed text-ink-soft">
        Nothing to flag right now. If a future check-in shows a sustained
        pattern of high stress, a note with support options will appear
        here, and at the top of this page, until things ease.
      </p>
    </section>
  );
}

/**
 * Persistent wellbeing signpost (round 7): shown when the caller's most
 * recent check-in is a sustained-high-stress escalation
 * (`GET /assessments/escalation-status`), and stays visible across page
 * visits until a later check-in no longer escalates -- there is
 * deliberately no dismiss control, matching the ethical framework's
 * "persistent, non-intrusive signposting" mitigation (see
 * `docs/governance/ethical_framework.md`'s Risk Mitigation table). Wired to
 * the same `Recommendation.is_escalation` flag the Adaptive Recovery
 * Framework already computes -- this component runs no severity calculation
 * of its own.
 *
 * Deliberately styled like every other card on this page (`border-line`,
 * `bg-card`), not `border-danger`/red -- per WHO safe-messaging guidance and
 * this project's own no-red/no-siren-UI rule for wellbeing content, urgency
 * is carried by the wording, not by alarming colour or iconography.
 * `NIMH_ENTRY` and `SUMITHRAYO_ENTRY` are imported from `HomeContent.tsx`
 * rather than retyped, so this box and Article A's highlighted numbers can
 * never drift apart (see that file's `DIRECTORY` comment).
 */
function WellbeingSignpostSection() {
  return (
    <section
      role="status"
      aria-label="Wellbeing support"
      className="mt-6 rounded-lg border border-accent bg-accent-soft/50 p-6"
    >
      <h2 className="text-base font-semibold tracking-tight text-ink">
        A note about your recent check-ins
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-ink">
        A few check-ins in a row have pointed to a lot of pressure, not just
        one hard day. That's the kind of pattern worth talking to a person
        about, not something to work through with an app alone. Your
        university's wellbeing service is a good place to start, and the{" "}
        {NIMH_ENTRY.name} ({NIMH_ENTRY.lines[0]}) or {SUMITHRAYO_ENTRY.name.split(" (")[0]} (
        {SUMITHRAYO_ENTRY.lines[0]}) are there too, any time you'd rather
        talk something through first.
      </p>
      <p className="mt-3 text-sm leading-relaxed text-ink">
        You'll find the full directory on the{" "}
        <Link
          to="/resources"
          className="font-medium text-ink underline underline-offset-2 hover:text-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          Resources page
        </Link>
        . This note will stay here until things ease, and reaching out is a
        good sign, not a setback.
      </p>
    </section>
  );
}

/** Display name only -- see `UpdateProfileRequest`'s docstring for why this
 *  doesn't require a password (not a destructive or security action). */
function EditProfileSection({
  token,
  me,
  onUpdated,
}: {
  token: string;
  me: MeResponse;
  onUpdated: (me: MeResponse) => void;
}) {
  const [displayName, setDisplayName] = useState(me.display_name ?? "");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaved(false);
    setBusy(true);
    try {
      const updated = await updateDisplayName(displayName.trim() || null, token);
      onUpdated(updated);
      setDisplayName(updated.display_name ?? "");
      setSaved(true);
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
    <section className="mt-8 rounded-lg border border-line bg-card p-6">
      <h2 className="text-base font-semibold tracking-tight text-ink">
        Edit profile
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-ink-soft">
        Used only to greet you by name. Leave blank to use your email instead.
      </p>

      <form onSubmit={handleSubmit} className="mt-4 space-y-3" noValidate>
        <div>
          <label htmlFor="settings-display-name" className="block text-sm font-medium text-ink">
            Display name
          </label>
          <input
            id="settings-display-name"
            name="display_name"
            type="text"
            maxLength={80}
            value={displayName}
            onChange={(e) => {
              setDisplayName(e.target.value);
              setSaved(false);
            }}
            className="mt-1 w-full rounded-md border border-line bg-card px-3 py-2 text-base text-ink focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          />
        </div>

        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
        {saved && !error && (
          <p className="text-sm text-ink-soft">Saved.</p>
        )}

        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          {busy ? "Saving…" : "Save name"}
        </button>
      </form>
    </section>
  );
}

/** In-session password change -- requires the current password, distinct
 *  from the forgot/reset-password flow at `/reset-password`. */
function ChangePasswordSection({ token }: { token: string }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaved(false);
    setBusy(true);
    try {
      await changePassword(currentPassword, newPassword, token);
      setCurrentPassword("");
      setNewPassword("");
      setSaved(true);
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
    <section className="mt-6 rounded-lg border border-line bg-card p-6">
      <h2 className="text-base font-semibold tracking-tight text-ink">
        Change password
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-ink-soft">
        Enter your current password, then choose a new one.
      </p>

      <form onSubmit={handleSubmit} className="mt-4 space-y-3" noValidate>
        <div>
          <label htmlFor="current-password" className="block text-sm font-medium text-ink">
            Current password
          </label>
          <input
            id="current-password"
            name="current_password"
            type="password"
            autoComplete="current-password"
            required
            value={currentPassword}
            onChange={(e) => {
              setCurrentPassword(e.target.value);
              setSaved(false);
            }}
            className="mt-1 w-full rounded-md border border-line bg-card px-3 py-2 text-base text-ink focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          />
        </div>

        <div>
          <label htmlFor="new-password" className="block text-sm font-medium text-ink">
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
            onChange={(e) => {
              setNewPassword(e.target.value);
              setSaved(false);
            }}
            className="mt-1 w-full rounded-md border border-line bg-card px-3 py-2 text-base text-ink focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          />
          <p className="mt-1 text-sm text-ink-faint">At least 8 characters.</p>
        </div>

        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
        {saved && !error && (
          <p className="text-sm text-ink-soft">Password updated.</p>
        )}

        <button
          type="submit"
          disabled={busy || !currentPassword || !newPassword}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          {busy ? "Updating…" : "Update password"}
        </button>
      </form>
    </section>
  );
}

/** Opt-in email one-time-code sign-in (round 7). Default off -- see
 *  `User.otp_enabled`'s docstring. Reuses the existing Resend integration
 *  used for password reset, not a new authenticator/QR-code flow. */
function TwoFactorSection({
  token,
  me,
  onUpdated,
}: {
  token: string;
  me: MeResponse;
  onUpdated: (me: MeResponse) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleToggle() {
    setError(null);
    setBusy(true);
    try {
      const updated = await updateOtpSetting(!me.otp_enabled, token);
      onUpdated(updated);
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
    <section className="mt-6 rounded-lg border border-line bg-card p-6">
      <h2 className="text-base font-semibold tracking-tight text-ink">
        Two-factor authentication
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-ink-soft">
        When turned on, signing in also requires a short code we email you,
        alongside your password. Off by default.
      </p>

      {error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {error}
        </p>
      )}

      <button
        type="button"
        role="switch"
        aria-checked={me.otp_enabled}
        onClick={handleToggle}
        disabled={busy}
        className={`mt-4 flex items-center gap-3 rounded-md border px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:cursor-not-allowed disabled:opacity-60 ${
          me.otp_enabled
            ? "border-accent bg-accent-soft text-ink"
            : "border-line text-ink-soft hover:bg-accent-soft"
        }`}
      >
        {me.otp_enabled ? "On — sign-in codes required" : "Off — turn on sign-in codes"}
      </button>
    </section>
  );
}

/** Soft-delete account deactivation. Unchanged from round 4 beyond moving
 *  into its own component alongside the new sections above it. */
function DeactivateSection({
  token,
  signOut,
  navigate,
}: {
  token: string | null;
  signOut: () => void;
  navigate: (path: string) => void;
}) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

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
    <section className="mt-6 rounded-lg border border-line bg-card p-6">
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
  );
}
