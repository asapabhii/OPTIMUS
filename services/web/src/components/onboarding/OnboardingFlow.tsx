import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  Loader2,
  Plug,
  Network,
  FileCheck,
  MessageSquare,
} from "lucide-react";
import { api } from "../../api/client";

type OnboardingStep = "intent" | "connecting" | "ingesting" | "declaring" | "proving" | "complete";

interface ConnectorBundle {
  provider_type: string;
  display_name: string;
  description: string;
  default_source_class: string;
}

export function OnboardingFlow() {
  const navigate = useNavigate();
  const [step, setStep] = useState<OnboardingStep>("intent");
  const [intent, setIntent] = useState("");
  const [connectors, setConnectors] = useState<ConnectorBundle[]>([]);

  const intentMutation = useMutation({
    mutationFn: async (intentText: string) => {
      const response = await api.post<{
        recommended_connectors: ConnectorBundle[];
        message: string;
      }>("/api/v1/onboarding/intent", {
        viewer_id: "00000000-0000-0000-0000-000000000001",
        intent: intentText,
      });
      return response.data;
    },
    onSuccess: (data) => {
      setConnectors(data.recommended_connectors);
      setStep("connecting");
    },
  });

  const steps = [
    { key: "intent", label: "What do you need?", icon: MessageSquare },
    { key: "connecting", label: "Connect tools", icon: Plug },
    { key: "ingesting", label: "Building graph", icon: Network },
    { key: "declaring", label: "Declarations", icon: FileCheck },
    { key: "proving", label: "Proof answers", icon: CheckCircle2 },
  ];

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <div className="border-b border-border px-8 py-6">
        <h1 className="text-2xl font-semibold tracking-tight">
          Optimus
          <span className="text-muted-foreground font-normal ml-2">
            TrustLayer
          </span>
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Let's get you set up in under 15 minutes
        </p>
      </div>

      {/* Step indicators */}
      <div className="px-8 py-4 border-b border-border">
        <div className="flex items-center gap-2 max-w-2xl">
          {steps.map(({ key, label, icon: Icon }, i) => {
            const stepIndex = steps.findIndex((s) => s.key === step);
            const isActive = key === step;
            const isComplete = i < stepIndex;

            return (
              <div key={key} className="flex items-center gap-2 flex-1">
                <div
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : isComplete
                        ? "bg-accent text-accent-foreground"
                        : "text-muted-foreground"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">{label}</span>
                </div>
                {i < steps.length - 1 && (
                  <div
                    className={`h-px flex-1 ${
                      isComplete ? "bg-primary/50" : "bg-border"
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Step content */}
      <div className="flex-1 flex items-center justify-center px-8 py-12">
        {step === "intent" && (
          <div className="max-w-lg w-full space-y-6 text-center">
            <h2 className="text-xl font-semibold">
              What do you want help with?
            </h2>
            <p className="text-sm text-muted-foreground">
              Tell us what you're working on and we'll recommend the right tools
              to connect.
            </p>
            <div className="space-y-3">
              <input
                type="text"
                value={intent}
                onChange={(e) => setIntent(e.target.value)}
                placeholder="e.g., tracking renewals, managing client health, inventory..."
                className="w-full px-4 py-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <button
                onClick={() => intentMutation.mutate(intent)}
                disabled={!intent.trim() || intentMutation.isPending}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {intentMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    Continue
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
            <div className="flex flex-wrap gap-2 justify-center">
              {[
                "Renewals & contract management",
                "Client health & success",
                "Sales pipeline accuracy",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setIntent(suggestion);
                    intentMutation.mutate(suggestion);
                  }}
                  className="px-3 py-1.5 text-xs rounded-full border border-border text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === "connecting" && (
          <div className="max-w-lg w-full space-y-6">
            <div className="text-center space-y-2">
              <h2 className="text-xl font-semibold">Connect your tools</h2>
              <p className="text-sm text-muted-foreground">
                We'll securely connect to these sources using your own
                credentials.
              </p>
            </div>
            <div className="space-y-3">
              {connectors.map((connector) => (
                <button
                  key={connector.provider_type}
                  className="w-full flex items-center justify-between p-4 rounded-lg border border-border hover:border-foreground/20 transition-colors text-left"
                  onClick={() => {
                    // TODO: Trigger Nango OAuth
                  }}
                >
                  <div>
                    <div className="font-medium text-sm">
                      {connector.display_name}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {connector.description}
                    </div>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded mt-1 inline-block ${
                        connector.default_source_class === "authority"
                          ? "bg-layer-canon/10 text-layer-canon"
                          : "bg-layer-personal/10 text-layer-personal"
                      }`}
                    >
                      {connector.default_source_class}
                    </span>
                  </div>
                  <Plug className="h-5 w-5 text-muted-foreground" />
                </button>
              ))}
            </div>
            <button
              onClick={() => setStep("ingesting")}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-colors"
            >
              Continue
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}

        {step === "ingesting" && (
          <div className="max-w-lg w-full space-y-6 text-center">
            <div className="space-y-2">
              <Network className="h-16 w-16 text-primary mx-auto animate-pulse" />
              <h2 className="text-xl font-semibold">Building your graph</h2>
              <p className="text-sm text-muted-foreground">
                We're ingesting your most recent data and resolving entities.
                Full ingestion continues in the background.
              </p>
            </div>
            {/* Progress bar */}
            <div className="w-full bg-muted rounded-full h-2">
              <div className="bg-primary h-2 rounded-full transition-all duration-1000 w-[45%]" />
            </div>
            <p className="text-xs text-muted-foreground">
              0 entities resolved so far...
            </p>
            <button
              onClick={() => setStep("declaring")}
              className="px-4 py-2 rounded-lg border border-border text-sm text-muted-foreground hover:bg-accent transition-colors"
            >
              Skip to declarations
            </button>
          </div>
        )}

        {step === "declaring" && (
          <div className="max-w-lg w-full space-y-6 text-center">
            <h2 className="text-xl font-semibold">Quick declarations</h2>
            <p className="text-sm text-muted-foreground">
              We've inferred most of these. Just confirm or override.
            </p>
            <p className="text-xs text-muted-foreground">
              No declarations to review yet — connect your tools first.
            </p>
            <button
              onClick={() => setStep("proving")}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-colors"
            >
              Continue
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}

        {step === "proving" && (
          <div className="max-w-lg w-full space-y-6 text-center">
            <CheckCircle2 className="h-16 w-16 text-freshness-live mx-auto" />
            <h2 className="text-xl font-semibold">You're all set!</h2>
            <p className="text-sm text-muted-foreground">
              Start asking questions. We'll show you real conflicts in your
              data.
            </p>
            <button
              onClick={() => navigate("/ask")}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-colors"
            >
              Start asking
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
