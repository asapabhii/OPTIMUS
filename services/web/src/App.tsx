import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/ui/Layout";
import { AskSurface } from "./surfaces/ask/AskSurface";
import { BrowseSurface } from "./surfaces/browse/BrowseSurface";
import { DecisionsSurface } from "./surfaces/decisions/DecisionsSurface";
import { CanonSurface } from "./surfaces/canon/CanonSurface";
import { OnboardingFlow } from "./components/onboarding/OnboardingFlow";
import { LoginPage } from "./pages/LoginPage";
import { SourcesPage } from "./pages/SourcesPage";
import { isAuthenticated } from "./api/client";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/onboarding"
        element={
          <ProtectedRoute>
            <OnboardingFlow />
          </ProtectedRoute>
        }
      />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/ask" replace />} />
        <Route path="/ask" element={<AskSurface />} />
        <Route path="/browse" element={<BrowseSurface />} />
        <Route path="/browse/:entityId" element={<BrowseSurface />} />
        <Route path="/decisions" element={<DecisionsSurface />} />
        <Route path="/canon" element={<CanonSurface />} />
        <Route path="/sources" element={<SourcesPage />} />
      </Route>
      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
