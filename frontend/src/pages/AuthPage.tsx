import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, forgotPassword, login, register } from "../services/api";
import { useAuth } from "../services/auth";
import { HomeContent } from "../components/HomeContent";

type Mode = "login" | "register" | "forgot";

/** Combined sign-in / create-account screen. */
export function AuthPage() {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [hobby, setHobby] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [forgotSent, setForgotSent] = useState(false);

  const { signIn } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "forgot") {
        await forgotPassword(email);
        setForgotSent(true);
        return;
      }
      if (mode === "register") {
        await register(email, password, displayName, hobby);
      }
      const { access_token, display_name } = await login(email, password);
      signIn(access_token, email, display_name);
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

  if (mode === "forgot") {
    return (
      <>
      <div className="mx-auto max-w-sm">
        <h1 className="text-xl font-semibold tracking-tight text-ink">
          Reset your password
        </h1>
        {forgotSent ? (
          <>
            <p className="mt-2 text-base leading-relaxed text-ink-soft">
              If that email is registered, a reset link has been sent. Check
              your inbox (and spam folder) for a message from InnerSync AI.
            </p>
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setForgotSent(false);
                setError(null);
              }}
              className="mt-4 text-sm font-medium text-ink underline underline-offset-2 hover:text-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              Back to sign in
            </button>
          </>
        ) : (
          <>
            <p className="mt-2 text-base leading-relaxed text-ink-soft">
              Enter your account email and we will send a link to reset your
              password.
            </p>
            <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
              <div>
                <label htmlFor="forgot-email" className="block text-base font-medium text-ink">
                  Email
                </label>
                <input
                  id="forgot-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-1 w-full rounded-md border border-line bg-card px-3 py-2 text-base text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  placeholder="you@university.ac.uk"
                />
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
                {busy ? "Sending…" : "Send reset link"}
              </button>
            </form>
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setError(null);
              }}
              className="mt-4 text-sm font-medium text-ink underline underline-offset-2 hover:text-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              Back to sign in
            </button>
          </>
        )}
      </div>
      <HomeContent />
      </>
    );
  }

  return (
    <>
    <div className="mx-auto max-w-sm">
      <h1 className="text-xl font-semibold tracking-tight text-ink">
        {mode === "login" ? "Sign in" : "Create an account"}
      </h1>
      <p className="mt-2 text-base leading-relaxed text-ink-soft">
        Your check-in answers are stored against your account so you can look back
        at them. They are not shared with your university.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
        <div>
          <label htmlFor="email" className="block text-base font-medium text-ink">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-md border border-line bg-card px-3 py-2 text-base text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            placeholder="you@university.ac.uk"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-base font-medium text-ink">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={8}
            maxLength={72}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-md border border-line bg-card px-3 py-2 text-base text-ink focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          />
          {mode === "register" && (
            <p className="mt-1 text-sm text-ink-faint">At least 8 characters.</p>
          )}
          {mode === "login" && (
            <button
              type="button"
              onClick={() => {
                setMode("forgot");
                setError(null);
              }}
              className="mt-1 text-sm text-ink-soft underline-offset-2 hover:text-accent-strong hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              Forgot password?
            </button>
          )}
        </div>

        {mode === "register" && (
          <>
            <div>
              <label htmlFor="display-name" className="block text-base font-medium text-ink">
                What should we call you?{" "}
                <span className="font-normal text-ink-faint">(optional)</span>
              </label>
              <input
                id="display-name"
                name="display_name"
                type="text"
                maxLength={80}
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="mt-1 w-full rounded-md border border-line bg-card px-3 py-2 text-base text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                placeholder="Leave blank and we'll use your email"
              />
              <p className="mt-1 text-sm text-ink-faint">Used only to greet you by name.</p>
            </div>

            <div>
              <label htmlFor="hobby" className="block text-base font-medium text-ink">
                Something you enjoy doing?{" "}
                <span className="font-normal text-ink-faint">(optional)</span>
              </label>
              <input
                id="hobby"
                name="hobby"
                type="text"
                maxLength={80}
                value={hobby}
                onChange={(e) => setHobby(e.target.value)}
                className="mt-1 w-full rounded-md border border-line bg-card px-3 py-2 text-base text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                placeholder="e.g. painting, football, reading"
              />
              <p className="mt-1 text-sm text-ink-faint">
                Occasionally referenced in a suggestion, if it's genuinely relevant.
              </p>
            </div>
          </>
        )}

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
          {busy
            ? "Please wait…"
            : mode === "login"
              ? "Sign in"
              : "Create account"}
        </button>
      </form>

      <p className="mt-5 text-base text-ink-soft">
        {mode === "login" ? "No account yet?" : "Already have an account?"}{" "}
        <button
          type="button"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError(null);
          }}
          className="font-medium text-ink underline underline-offset-2 hover:text-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          {mode === "login" ? "Create one" : "Sign in"}
        </button>
      </p>
    </div>
    <HomeContent />
    </>
  );
}
