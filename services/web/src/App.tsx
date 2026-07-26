import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/ui/Layout";
import { AskSurface } from "./surfaces/ask/AskSurface";
import { BrowseSurface } from "./surfaces/browse/BrowseSurface";
import { DecisionsSurface } from "./surfaces/decisions/DecisionsSurface";
import { OnboardingFlow } from "./components/onboarding/OnboardingFlow";

export default function App() {
  return (
    <Routes>
      <Route path="/onboarding" element={<OnboardingFlow />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/ask" replace />} />
        <Route path="/ask" element={<AskSurface />} />
        <Route path="/browse" element={<BrowseSurface />} />
        <Route path="/browse/:entityId" element={<BrowseSurface />} />
        <Route path="/decisions" element={<DecisionsSurface />} />
      </Route>
    </Routes>
  );
}
