import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AssessmentPage } from "./pages/AssessmentPage";
import { AuthPage } from "./pages/AuthPage";
import { ChatPage } from "./pages/ChatPage";
import { LandingPage } from "./pages/LandingPage";
import { ProgressPage } from "./pages/ProgressPage";
import { ResultsPage } from "./pages/ResultsPage";
import { useAuth } from "./services/auth";

/** Sends unauthenticated visitors back to the sign-in screen. */
function RequireAuth({ children }: { children: React.ReactElement }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/" replace />;
}

export function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Layout>
      <Routes>
        <Route
          path="/"
          element={isAuthenticated ? <LandingPage /> : <AuthPage />}
        />
        <Route
          path="/assessment"
          element={
            <RequireAuth>
              <AssessmentPage />
            </RequireAuth>
          }
        />
        <Route
          path="/results"
          element={
            <RequireAuth>
              <ResultsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/progress"
          element={
            <RequireAuth>
              <ProgressPage />
            </RequireAuth>
          }
        />
        <Route
          path="/chat"
          element={
            <RequireAuth>
              <ChatPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
