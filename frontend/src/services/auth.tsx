/**
 * Token storage.
 *
 * DECISION: the access token is held in React state only — in memory, for the
 * lifetime of the tab. It is never written to `localStorage` or
 * `sessionStorage`.
 *
 * Why not localStorage/sessionStorage: both are readable by any JavaScript on
 * the origin, so a single XSS flaw anywhere in the app (or in a dependency)
 * hands an attacker a valid token for wellbeing data. In-memory storage is not
 * immune to XSS, but it removes the trivial persistent read and means the token
 * disappears when the tab closes.
 *
 * Why not httpOnly cookies, which would be stronger: that requires the backend
 * to issue `Set-Cookie` and to carry CSRF protection, since cookies are sent
 * automatically on cross-site requests. The Phase 6 API returns a bearer token
 * in the response body, and changing that contract was out of scope for this
 * session. Recorded as the recommended next hardening step rather than silently
 * accepted — see the frontend README.
 *
 * Cost of this choice: a page refresh logs the user out. That is a deliberate
 * trade of convenience for a smaller attack surface, and is acceptable for a
 * short single-session assessment flow.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

interface AuthState {
  token: string | null;
  email: string | null;
  isAuthenticated: boolean;
  signIn: (token: string, email: string) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);

  const signIn = useCallback((nextToken: string, nextEmail: string) => {
    setToken(nextToken);
    setEmail(nextEmail);
  }, []);

  const signOut = useCallback(() => {
    setToken(null);
    setEmail(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ token, email, isAuthenticated: token !== null, signIn, signOut }),
    [token, email, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
