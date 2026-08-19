import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../services/auth";
import { getAssessmentHistory } from "../services/api";
import { MoodAvatar, type MoodLevel } from "./MoodAvatar";
import { DISCLAIMER_TEXT } from "../services/disclaimer";

/**
 * Page shell: masthead, centred column, and the standing non-clinical notice.
 *
 * The chat page gets a wider content column than the rest of the app
 * (`max-w-5xl` vs. `max-w-3xl`) — round 2 UX feedback was that the chat felt
 * cramped, closer to a modern chat UI's proportions than a form-width
 * column. Still centred with visible margins either side, not full-bleed;
 * header and footer stay at the normal site width so nav doesn't stretch
 * awkwardly wide.
 *
 * Round 4: the header is the one place in the app with a solid navy fill
 * (the "nav" leg of the navy/gold/off-white theme) rather than the usual
 * off-white page background, so every text/icon colour inside it is
 * inverted to a light or gold tone rather than the site's normal ink/accent
 * pairing — navy-on-navy would be invisible, and gold reads fine here
 * specifically because it sits on a dark surface (see index.css's token
 * comment on why gold is avoided as text elsewhere).
 */
const MOOD_PANEL_ROUTES = ["/assessment", "/results", "/progress"];

export function Layout({ children }: { children: ReactNode }) {
  const { isAuthenticated, email, token, signOut } = useAuth();
  const location = useLocation();
  const isChatRoute = location.pathname.startsWith("/chat");
  // Round 5: the mood avatar moved out of the nav bar into a left-side
  // panel, shown only on the pages it's actually relevant to reading --
  // not on the landing page, chat (which has its own layout and
  // messaging-focused width), or settings.
  const showMoodPanel = isAuthenticated && MOOD_PANEL_ROUTES.includes(location.pathname);

  // The mood avatar's only data dependency: the most recent check-in's
  // level. Fetched once per sign-in, not per navigation -- decorative, so a
  // fetch failure is swallowed rather than shown as an error; the avatar
  // just falls back to its calm default (see MoodAvatar's `level: null` case).
  const [latestLevel, setLatestLevel] = useState<MoodLevel | null>(null);
  useEffect(() => {
    if (!token) {
      setLatestLevel(null);
      return;
    }
    let cancelled = false;
    getAssessmentHistory(token)
      .then((history) => {
        if (cancelled || history.length === 0) return;
        setLatestLevel(history[history.length - 1].stress_level);
      })
      .catch(() => {
        // Decorative only -- no error surface for this.
      });
    return () => {
      cancelled = true;
    };
    // Round 6 bug fix: re-fetch on every navigation (location.key), not just
    // once per token -- see the comment above this effect's declaration.
  }, [token, location.key]);

  return (
    <div className="min-h-full flex flex-col">
      <header className="bg-ink">
        <div className="mx-auto w-full max-w-3xl px-6 py-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-base font-semibold tracking-tight text-white">
              InnerSync
            </p>
            <p className="text-xs text-white/70">Wellbeing check-in</p>
          </div>
          {isAuthenticated && (
            <div className="flex items-center gap-3 text-xs text-white/70">
              <Link
                to="/chat"
                className="hidden rounded-md px-2 py-1.5 text-white/80 transition-colors hover:bg-white/10 hover:text-accent sm:inline"
              >
                Chat
              </Link>
              <Link
                to="/progress"
                className="hidden rounded-md px-2 py-1.5 text-white/80 transition-colors hover:bg-white/10 hover:text-accent sm:inline"
              >
                My Trends
              </Link>
              <Link
                to="/resources"
                className="hidden rounded-md px-2 py-1.5 text-white/80 transition-colors hover:bg-white/10 hover:text-accent sm:inline"
              >
                Resources
              </Link>
              <Link
                to="/settings"
                className="hidden rounded-md px-2 py-1.5 text-white/80 transition-colors hover:bg-white/10 hover:text-accent sm:inline"
              >
                Settings
              </Link>
              <span className="hidden sm:inline">{email}</span>
              <button
                type="button"
                onClick={signOut}
                className="rounded-md border border-white/25 px-3 py-1.5 text-white/80 transition-colors hover:bg-white/10 hover:text-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </header>

      <main
        className={`mx-auto w-full flex-1 px-6 py-10 ${
          isChatRoute ? "max-w-5xl" : showMoodPanel ? "max-w-4xl" : "max-w-3xl"
        }`}
      >
        {showMoodPanel ? (
          <div className="flex flex-col gap-8 sm:flex-row sm:items-start">
            {/* Larger and more present than the old nav icon, but still a
                static, quiet presence -- no animation, no numbers, no
                streaks. Same expression logic as before: purely a function
                of the most recent check-in's level. */}
            <div className="flex shrink-0 flex-col items-center gap-3 sm:w-40">
              <MoodAvatar level={latestLevel} className="h-28 w-28" />
              <p className="text-center text-xs text-ink-faint">
                Reflects your most recent check-in
              </p>
            </div>
            <div className="min-w-0 flex-1">{children}</div>
          </div>
        ) : (
          children
        )}
      </main>

      <footer className="border-t border-line px-6 py-5">
        <p className="mx-auto max-w-3xl text-sm leading-relaxed text-ink-faint">
          {DISCLAIMER_TEXT}
        </p>
      </footer>
    </div>
  );
}
