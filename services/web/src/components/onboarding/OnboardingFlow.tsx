import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  ArrowLeft,
  Check,
  Loader2,
  Link2,
  Database,
  AlertCircle,
  Target,
  Users,
  TrendingUp,
  Headphones,
  Mail,
  FileSpreadsheet,
  HardDrive,
  MessageSquare,
  Briefcase,
} from "lucide-react";
import { api } from "../../api/client";

interface Integration {
  provider_type: string;
  display_name: string;
  description: string;
  category: string;
}

interface ConnectedSource {
  id: string;
  provider_type: string;
  display_name: string;
  connection_id: string;
  created_at: string;
}

interface IngestResult {
  connection_id: string;
  provider_type: string;
  records_fetched: number;
  entities_created: number;
  errors: string[];
}

const STEPS = [
  { id: "intent", label: "Your Goal", Icon: Target },
  { id: "connect", label: "Connect Tools", Icon: Link2 },
  { id: "ingest", label: "Build Graph", Icon: Database },
  { id: "ready", label: "Ready", Icon: Check },
];

const PROVIDER_ICON_MAP: Record<string, typeof Mail> = {
  "google-mail": Mail,
  "google-drive": HardDrive,
  "google-sheet": FileSpreadsheet,
  hubspot: Briefcase,
  slack: MessageSquare,
};

function ProviderIcon({ provider }: { provider: string }) {
  const Icon = PROVIDER_ICON_MAP[provider] || Link2;
  return <Icon className="h-4 w-4 text-muted-foreground" />;
}

const GOALS = [
  {
    id: "renewal",
    label: "Manage renewals & retention",
    desc: "Track at-risk accounts, renewal dates, health scores",
    Icon: Target,
  },
  {
    id: "client",
    label: "360 client intelligence",
    desc: "Unified view of every client across all touchpoints",
    Icon: Users,
  },
  {
    id: "sales",
    label: "Sales pipeline intelligence",
    desc: "Deal progression, win/loss analysis, competitive intel",
    Icon: TrendingUp,
  },
  {
    id: "support",
    label: "Support & ticket insights",
    desc: "Ticket patterns, escalation tracking, SLA monitoring",
    Icon: Headphones,
  },
];

export function OnboardingFlow() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [intent, setIntent] = useState("");
  const [availableIntegrations, setAvailableIntegrations] = useState<
    Integration[]
  >([]);
  const [connectedSources, setConnectedSources] = useState<ConnectedSource[]>(
    []
  );
  const [ingestResults, setIngestResults] = useState<IngestResult[]>([]);
  const [ingesting, setIngesting] = useState(false);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [ingestProgress, setIngestProgress] = useState<string[]>([]);
  const justConnectedRef = useRef(false);

  useEffect(() => {
    api
      .get<Integration[]>("/api/v1/connectors/available")
      .then((r) => setAvailableIntegrations(r.data))
      .catch(() => {});
  }, []);

  const loadConnections = useCallback(async () => {
    try {
      const resp = await api.get<ConnectedSource[]>(
        "/api/v1/connectors/connected",
        {
          params: { viewer_id: "00000000-0000-0000-0000-000000000001" },
        }
      );
      setConnectedSources(resp.data);
    } catch {
      /* no-op */
    }
  }, []);

  useEffect(() => {
    loadConnections();
  }, [loadConnections, step]);

  // Auto-ingest when a new source is connected
  useEffect(() => {
    if (justConnectedRef.current && connectedSources.length > 0 && step === 1) {
      justConnectedRef.current = false;
      // Move to ingest step and auto-start
      setStep(2);
      setTimeout(() => handleIngest(), 300);
    }
  }, [connectedSources]);

  const handleConnect = async (providerType: string) => {
    setConnecting(providerType);
    setError("");

    try {
      const sessionResp = await api.post<{ token?: string; error?: string }>(
        "/api/v1/connectors/session",
        null,
        { params: { viewer_id: "viewer-001" } }
      );

      if (sessionResp.data.error || !sessionResp.data.token) {
        setError(
          `Session error: ${sessionResp.data.error || "No token returned"}. Check your NANGO_SECRET_KEY.`
        );
        setConnecting(null);
        return;
      }

      const { default: Nango } = await import("@nangohq/frontend");
      const nango = new Nango({
        connectSessionToken: sessionResp.data.token,
      });

      await nango.auth(providerType);
      justConnectedRef.current = true;
      await loadConnections();
      setConnecting(null);
    } catch (err: any) {
      setError(
        err?.message?.includes("closed")
          ? "OAuth window was closed. Try again."
          : `Connection failed: ${err?.message || "Unknown error"}`
      );
      setConnecting(null);
    }
  };

  const handleIngest = async () => {
    if (connectedSources.length === 0) {
      setError("Connect at least one source first.");
      return;
    }

    setIngesting(true);
    setError("");
    setIngestProgress([]);

    // Show progress messages
    const progressMessages = [
      "Authenticating with connected sources...",
      "Fetching recent records (up to 50 per source)...",
      "Extracting entities from fetched data...",
      "Running entity resolution...",
      "Building knowledge graph...",
    ];

    let progressIndex = 0;
    const progressInterval = setInterval(() => {
      if (progressIndex < progressMessages.length) {
        setIngestProgress((prev) => [...prev, progressMessages[progressIndex]]);
        progressIndex++;
      }
    }, 1500);

    try {
      const resp = await api.post<IngestResult[] | IngestResult>(
        "/api/v1/ingest/all",
        {}
      );
      const results = Array.isArray(resp.data) ? resp.data : [resp.data];
      setIngestResults(results);

      clearInterval(progressInterval);
      setIngestProgress((prev) => [...prev, "Complete."]);

      // Auto-advance to ready after brief pause
      setTimeout(() => setStep(3), 1000);
    } catch (err: any) {
      clearInterval(progressInterval);
      setError(`Ingestion failed: ${err?.message || "Unknown error"}`);
    } finally {
      setIngesting(false);
    }
  };

  const safeResults = Array.isArray(ingestResults) ? ingestResults : [];
  const totalEntities = safeResults.reduce(
    (sum, r) => sum + (r.entities_created || 0),
    0
  );
  const totalRecords = safeResults.reduce(
    (sum, r) => sum + (r.records_fetched || 0),
    0
  );

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <div className="w-56 border-r border-border bg-card p-6 flex flex-col">
        <div className="flex items-center gap-2 mb-8">
          <img src="/logo.svg" alt="Optimus" className="w-8 h-8 rounded-lg" />
          <span className="font-semibold text-sm">Setup</span>
        </div>

        <nav className="space-y-1 flex-1">
          {STEPS.map((s, i) => {
            const StepIcon = i < step ? Check : s.Icon;
            return (
              <button
                key={s.id}
                onClick={() => i <= step && setStep(i)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all text-left ${
                  i === step
                    ? "bg-primary/10 text-primary font-medium"
                    : i < step
                    ? "text-green-500"
                    : "text-muted-foreground/50"
                }`}
                disabled={i > step}
              >
                <StepIcon className="h-4 w-4" />
                {s.label}
              </button>
            );
          })}
        </nav>

        <button
          onClick={() => navigate("/ask")}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-all"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to app
        </button>
      </div>

      {/* Main */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-2xl space-y-6">
          {error && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm animate-fade-in">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span className="flex-1">{error}</span>
              <button
                onClick={() => setError("")}
                className="text-xs underline"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Step 0: Intent */}
          {step === 0 && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">
                  What are you trying to accomplish?
                </h2>
                <p className="text-muted-foreground mt-2">
                  We'll recommend the right data sources for your workflow.
                </p>
              </div>

              <div className="grid grid-cols-1 gap-3">
                {GOALS.map((opt) => (
                  <button
                    key={opt.id}
                    onClick={() => setIntent(opt.id)}
                    className={`flex items-start gap-4 text-left p-4 rounded-xl border-2 transition-all ${
                      intent === opt.id
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/30"
                    }`}
                  >
                    <opt.Icon
                      className={`h-5 w-5 mt-0.5 shrink-0 ${
                        intent === opt.id
                          ? "text-primary"
                          : "text-muted-foreground"
                      }`}
                    />
                    <div>
                      <div className="font-medium text-sm">{opt.label}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {opt.desc}
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              <button
                onClick={() => setStep(1)}
                disabled={!intent}
                className="flex items-center gap-2 px-6 py-3 rounded-xl bg-primary text-primary-foreground font-medium text-sm disabled:opacity-50 hover:bg-primary/90 transition-all"
              >
                Continue <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          )}

          {/* Step 1: Connect */}
          {step === 1 && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">
                  Connect your tools
                </h2>
                <p className="text-muted-foreground mt-2">
                  Connect at least one source to get started. Click any
                  integration to connect via OAuth.
                </p>
              </div>

              {/* Connected */}
              {connectedSources.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-green-500 flex items-center gap-2">
                    <Check className="h-4 w-4" />
                    Connected ({connectedSources.length})
                  </h3>
                  {connectedSources.map((src) => (
                    <div
                      key={src.id}
                      className="flex items-center justify-between p-3 rounded-xl border border-green-500/20 bg-green-500/5"
                    >
                      <div className="flex items-center gap-3">
                        <ProviderIcon provider={src.provider_type} />
                        <div>
                          <div className="text-sm font-medium">
                            {src.display_name}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {src.connection_id}
                          </div>
                        </div>
                      </div>
                      <span className="text-xs text-green-500 font-medium">
                        Connected
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Available */}
              <div className="grid grid-cols-2 gap-3">
                {availableIntegrations
                  .filter(
                    (int_) =>
                      !connectedSources.some(
                        (s) => s.provider_type === int_.provider_type
                      )
                  )
                  .map((int_) => {
                    const isConnecting = connecting === int_.provider_type;
                    return (
                      <button
                        key={int_.provider_type}
                        onClick={() => handleConnect(int_.provider_type)}
                        disabled={isConnecting}
                        className="flex items-center gap-3 p-4 rounded-xl border border-border hover:border-primary/40 hover:bg-card transition-all text-left disabled:opacity-50"
                      >
                        <ProviderIcon provider={int_.provider_type} />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium">
                            {int_.display_name}
                          </div>
                          <div className="text-[11px] text-muted-foreground truncate">
                            {int_.description}
                          </div>
                        </div>
                        {isConnecting ? (
                          <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        ) : (
                          <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
                        )}
                      </button>
                    );
                  })}
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => setStep(0)}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-border text-sm hover:bg-accent transition-all"
                >
                  <ArrowLeft className="h-4 w-4" /> Back
                </button>
                <button
                  onClick={() => {
                    setStep(2);
                    setTimeout(() => handleIngest(), 300);
                  }}
                  disabled={connectedSources.length === 0}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium text-sm disabled:opacity-50 hover:bg-primary/90 transition-all"
                >
                  Build Knowledge Graph <ArrowRight className="h-4 w-4" />
                </button>
              </div>

              <p className="text-xs text-muted-foreground">
                {connectedSources.length === 0
                  ? "Connect at least one source to continue."
                  : `${connectedSources.length} connected. You can add more or continue.`}
              </p>
            </div>
          )}

          {/* Step 2: Ingest with live progress */}
          {step === 2 && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">
                  Build your knowledge graph
                </h2>
                <p className="text-muted-foreground mt-2">
                  Fetching the most recent{" "}
                  <strong className="text-foreground">50 records</strong> from
                  each connected source. Full ingestion continues in the
                  background.
                </p>
              </div>

              {/* Connected sources summary */}
              <div className="p-4 rounded-xl border border-border bg-card space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">
                    {connectedSources.length} source
                    {connectedSources.length !== 1 ? "s" : ""} connected
                  </span>
                  <Database className="h-4 w-4 text-muted-foreground" />
                </div>
                {connectedSources.map((src) => (
                  <div
                    key={src.id}
                    className="flex items-center gap-2 text-sm text-muted-foreground"
                  >
                    <ProviderIcon provider={src.provider_type} />
                    {src.display_name}
                  </div>
                ))}
              </div>

              {/* Live progress */}
              {(ingesting || ingestProgress.length > 0) && (
                <div className="p-4 rounded-xl border border-border bg-card space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    {ingesting ? (
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    ) : (
                      <Check className="h-4 w-4 text-green-500" />
                    )}
                    {ingesting ? "Ingesting data..." : "Ingestion complete"}
                  </div>
                  <div className="space-y-1 pl-6">
                    {ingestProgress.map((msg, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2 text-xs text-muted-foreground animate-fade-in"
                      >
                        {i === ingestProgress.length - 1 && ingesting ? (
                          <Loader2 className="h-3 w-3 animate-spin text-primary shrink-0" />
                        ) : (
                          <Check className="h-3 w-3 text-green-500 shrink-0" />
                        )}
                        {msg}
                      </div>
                    ))}
                  </div>

                  {/* Results */}
                  {safeResults.length > 0 && (
                    <div className="border-t border-border mt-3 pt-3 space-y-1">
                      {safeResults.map((r) => (
                        <div
                          key={r.connection_id}
                          className="flex items-center justify-between text-sm"
                        >
                          <span className="flex items-center gap-2">
                            <ProviderIcon provider={r.provider_type} />
                            {r.provider_type.replace("-", " ").replace("_", " ")}
                          </span>
                          <span className="text-muted-foreground text-xs">
                            {r.records_fetched} records, {r.entities_created}{" "}
                            entities
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="flex items-center gap-3">
                <button
                  onClick={() => setStep(1)}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-border text-sm hover:bg-accent transition-all"
                  disabled={ingesting}
                >
                  <ArrowLeft className="h-4 w-4" /> Back
                </button>
                {!ingesting && safeResults.length === 0 && (
                  <button
                    onClick={handleIngest}
                    className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-all"
                  >
                    <Database className="h-4 w-4" />
                    Start Ingestion
                  </button>
                )}
                {!ingesting && safeResults.length > 0 && (
                  <button
                    onClick={() => setStep(3)}
                    className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-green-600 text-white font-medium text-sm hover:bg-green-700 transition-all"
                  >
                    Continue <ArrowRight className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Step 3: Ready */}
          {step === 3 && (
            <div className="space-y-6 animate-fade-in text-center">
              <div className="w-16 h-16 rounded-2xl bg-green-500/10 border border-green-500/20 flex items-center justify-center mx-auto">
                <Check className="h-8 w-8 text-green-500" />
              </div>

              <div>
                <h2 className="text-2xl font-bold tracking-tight">
                  You're all set
                </h2>
                <p className="text-muted-foreground mt-2 max-w-md mx-auto">
                  {totalEntities > 0
                    ? `${totalRecords} records fetched, ${totalEntities} entities created from ${connectedSources.length} source${connectedSources.length !== 1 ? "s" : ""}. Your knowledge graph is ready.`
                    : `${connectedSources.length} source${connectedSources.length !== 1 ? "s" : ""} connected. Start asking questions to explore your data.`}
                </p>
              </div>

              <div className="flex items-center justify-center gap-3">
                <button
                  onClick={() => navigate("/ask")}
                  className="flex items-center gap-2 px-8 py-3 rounded-xl bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-all"
                >
                  Start Asking Questions <ArrowRight className="h-4 w-4" />
                </button>
                <button
                  onClick={() => navigate("/browse")}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl border border-border text-sm hover:bg-accent transition-all"
                >
                  Browse Entities
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
