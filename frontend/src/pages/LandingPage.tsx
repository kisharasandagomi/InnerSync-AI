import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../services/auth";

/**
 * The default view after signing in.
 *
 * One clear primary action — start a check-in through the chat flow — with
 * quieter secondary paths beneath it. Chat is the promoted route per this
 * session's UX change; the slider form at `/assessment` is kept working and
 * reachable, just de-emphasised here rather than removed (confirmed with
 * the project owner rather than decided unilaterally — see
 * `docs/research/methodology.md` § Chat-Driven Check-In Delivery).
 */
export function LandingPage() {
  const { email } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="mx-auto max-w-xl text-center">
      <p className="text-sm uppercase tracking-wider text-ink-faint">
        {email ? `Welcome back, ${email}` : "Welcome"}
      </p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
        How are things going?
      </h1>
      <p className="mt-3 text-base leading-relaxed text-ink-soft">
        A check-in takes a couple of minutes. You'll be asked a short series of
        questions in chat, one at a time, and get a plain-language read on
        things right after.
      </p>

      <button
        type="button"
        onClick={() => navigate("/chat", { state: { mode: "checkin" } })}
        className="mt-8 w-full rounded-md bg-accent px-6 py-3.5 text-base font-medium text-white transition-colors hover:bg-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 sm:w-auto"
      >
        Start your check-in
      </button>

      <div className="mt-6 flex flex-col items-center gap-2 text-sm text-ink-soft">
        <button
          type="button"
          onClick={() => navigate("/chat", { state: { mode: "talk" } })}
          className="underline-offset-4 hover:text-accent-strong hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          Just want to talk instead? Open chat
        </button>
        <Link
          to="/assessment"
          className="text-ink-faint underline-offset-4 hover:text-accent-strong hover:underline"
        >
          Prefer the classic form?
        </Link>
      </div>
    </div>
  );
}
