import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../services/auth";

/** Page shell: masthead, centred column, and the standing non-clinical notice. */
export function Layout({ children }: { children: ReactNode }) {
  const { isAuthenticated, email, signOut } = useAuth();

  return (
    <div className="min-h-full flex flex-col">
      <header className="border-b border-line bg-card">
        <div className="mx-auto w-full max-w-3xl px-6 py-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-[15px] font-semibold tracking-tight text-ink">
              InnerSync
            </p>
            <p className="text-xs text-ink-faint">Wellbeing check-in</p>
          </div>
          {isAuthenticated && (
            <div className="flex items-center gap-3 text-xs text-ink-faint">
              <Link
                to="/progress"
                className="hidden rounded-md px-2 py-1.5 text-ink-soft transition-colors hover:bg-accent-soft hover:text-accent-strong sm:inline"
              >
                Your trends
              </Link>
              <span className="hidden sm:inline">{email}</span>
              <button
                type="button"
                onClick={signOut}
                className="rounded-md border border-line px-3 py-1.5 text-ink-soft transition-colors hover:bg-accent-soft hover:text-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-10">{children}</main>

      <footer className="border-t border-line px-6 py-5">
        <p className="mx-auto max-w-3xl text-xs leading-relaxed text-ink-faint">
          InnerSync offers wellbeing support and is not a diagnostic tool. It does
          not replace a doctor, counsellor, or your university wellbeing service.
          If you are struggling, please talk to someone.
        </p>
      </footer>
    </div>
  );
}
