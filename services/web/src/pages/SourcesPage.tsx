import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus,
  Loader2,
  Check,
  Trash2,
  RefreshCw,
  Cable,
  Link2,
  ArrowRight,
  Mail,
  FileSpreadsheet,
  HardDrive,
  MessageSquare,
  Briefcase,
  Clock,
} from "lucide-react";
import { api } from "../api/client";

interface ConnectedSource {
  id: string;
  provider_type: string;
  display_name: string;
  connection_id: string;
  created_at: string;
}

interface AvailableIntegration {
  provider_type: string;
  display_name: string;
  description: string;
}

const PROVIDER_ICON_MAP: Record<string, typeof Mail> = {
  "google-mail": Mail,
  "google-drive": HardDrive,
  "google-sheet": FileSpreadsheet,
  hubspot: Briefcase,
  slack: MessageSquare,
};

function ProviderIcon({
  provider,
  className = "h-5 w-5",
}: {
  provider: string;
  className?: string;
}) {
  const Icon = PROVIDER_ICON_MAP[provider] || Link2;
  return <Icon className={className} />;
}

const SYNC_INTERVAL = 60 * 60 * 1000; // 1 hour

export function SourcesPage() {
  const navigate = useNavigate();
  const [connected, setConnected] = useState<ConnectedSource[]>([]);
  const [available, setAvailable] = useState<AvailableIntegration[]>([]);
  const [loading, setLoading] = useState(true);
  const [disconnecting, setDisconnecting] = useState<string | null>(null);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [showAddPanel, setShowAddPanel] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [ingestMsg, setIngestMsg] = useState("");
  const [lastSync, setLastSync] = useState<number | null>(null);
  const syncTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [connResp, availResp] = await Promise.all([
        api.get<ConnectedSource[]>("/api/v1/connectors/connected", {
          params: { viewer_id: "00000000-0000-0000-0000-000000000001" },
        }),
        api.get<AvailableIntegration[]>("/api/v1/connectors/available"),
      ]);
      setConnected(connResp.data);
      setAvailable(availResp.data);
    } catch {
      /* no-op */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Auto-sync every hour
  useEffect(() => {
    const savedLastSync = localStorage.getItem("optimus_last_sync");
    if (savedLastSync) setLastSync(parseInt(savedLastSync, 10));

    syncTimerRef.current = setInterval(() => {
      if (connected.length > 0 && !ingesting) {
        handleIngestAll(true);
      }
    }, SYNC_INTERVAL);

    return () => {
      if (syncTimerRef.current) clearInterval(syncTimerRef.current);
    };
  }, [connected.length]);

  const handleDisconnect = async (src: ConnectedSource) => {
    if (!confirm(`Disconnect ${src.display_name}? You can reconnect anytime.`))
      return;

    setDisconnecting(src.connection_id);
    try {
      await api.delete(
        `/api/v1/connectors/${encodeURIComponent(src.connection_id)}`,
        { params: { provider_config_key: src.provider_type } }
      );
      await loadData();
    } catch {
      /* no-op */
    } finally {
      setDisconnecting(null);
    }
  };

  const handleConnect = async (providerType: string) => {
    setConnecting(providerType);

    try {
      const sessionResp = await api.post<{ token?: string; error?: string }>(
        "/api/v1/connectors/session",
        null,
        { params: { viewer_id: "viewer-001" } }
      );

      if (!sessionResp.data.token) {
        alert("Failed to create connection session. Check your Nango key.");
        setConnecting(null);
        return;
      }

      const { default: Nango } = await import("@nangohq/frontend");
      const nango = new Nango({
        connectSessionToken: sessionResp.data.token,
      });

      // Suppress COOP "window.closed" console errors from Nango SDK popup polling
      const origError = console.error;
      console.error = (...args: any[]) => {
        if (typeof args[0] === "string" && args[0].includes("Cross-Origin-Opener-Policy")) return;
        origError.apply(console, args);
      };

      try {
        await nango.auth(providerType);
      } finally {
        // Restore after a delay to catch lingering interval logs
        setTimeout(() => { console.error = origError; }, 5000);
      }

      await loadData();
      setShowAddPanel(false);

      // Auto-ingest after new connection
      setTimeout(() => handleIngestAll(false), 500);
    } catch (err: any) {
      if (!err?.message?.includes("closed")) {
        alert(`Connection failed: ${err?.message || "Unknown error"}`);
      }
    } finally {
      setConnecting(null);
    }
  };

  const handleIngestAll = async (silent = false) => {
    setIngesting(true);
    if (!silent) setIngestMsg("");

    try {
      const resp = await api.post<any>("/api/v1/ingest/all", {});
      const results = Array.isArray(resp.data) ? resp.data : [resp.data];
      const total = results.reduce(
        (s: number, r: any) => s + (r.records_fetched || 0),
        0
      );
      const entities = results.reduce(
        (s: number, r: any) => s + (r.entities_created || 0),
        0
      );

      const now = Date.now();
      setLastSync(now);
      localStorage.setItem("optimus_last_sync", String(now));

      if (!silent) {
        setIngestMsg(
          `Synced ${total} records, ${entities} new entities created.`
        );
      }
    } catch (err: any) {
      if (!silent) {
        setIngestMsg(`Sync error: ${err?.message || "Unknown"}`);
      }
    } finally {
      setIngesting(false);
    }
  };

  const unconnectedIntegrations = available.filter(
    (a) => !connected.some((c) => c.provider_type === a.provider_type)
  );

  const timeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  const lastSyncText = lastSync
    ? `Last synced ${timeAgo(new Date(lastSync).toISOString())}`
    : "Not synced yet";

  return (
    <div className="space-y-6 max-w-3xl p-6 h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2 tracking-tight">
            <Cable className="h-6 w-6 text-primary" />
            Connected Sources
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your data connections. Disconnect, reconnect, or add new
            accounts.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {connected.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-muted-foreground/50 flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {lastSyncText}
              </span>
              <button
                onClick={() => handleIngestAll(false)}
                disabled={ingesting}
                className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border text-sm hover:bg-accent disabled:opacity-50 transition-all"
              >
                {ingesting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                {ingesting ? "Syncing..." : "Sync Now"}
              </button>
            </div>
          )}
          <button
            onClick={() => setShowAddPanel(!showAddPanel)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-all"
          >
            <Plus className="h-4 w-4" />
            Add Source
          </button>
        </div>
      </div>

      {/* Auto-sync indicator */}
      {connected.length > 0 && (
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground/40 px-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500/50 animate-pulse" />
          Auto-sync enabled (every hour)
        </div>
      )}

      {/* Add source panel */}
      {showAddPanel && (
        <div className="p-4 rounded-xl border border-primary/20 bg-card space-y-3 animate-fade-in">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">
              Available integrations
              {unconnectedIntegrations.length > 0 && (
                <span className="text-muted-foreground font-normal">
                  {" "}
                  ({unconnectedIntegrations.length})
                </span>
              )}
            </h3>
            <button
              onClick={() => setShowAddPanel(false)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Close
            </button>
          </div>

          {available.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No integrations configured yet. Configure integrations in your
              Nango account to see them here.
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              {available.map((int_) => {
                const isConnected = connected.some(
                  (c) => c.provider_type === int_.provider_type
                );
                const isConnecting = connecting === int_.provider_type;

                return (
                  <button
                    key={int_.provider_type}
                    onClick={() => handleConnect(int_.provider_type)}
                    disabled={isConnecting}
                    className={`flex items-center gap-3 p-3 rounded-xl border text-left transition-all disabled:opacity-50 ${
                      isConnected
                        ? "border-green-500/20 bg-green-500/5"
                        : "border-border hover:border-primary/30 hover:bg-accent/50"
                    }`}
                  >
                    <ProviderIcon
                      provider={int_.provider_type}
                      className="h-4 w-4 text-muted-foreground"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium">
                        {int_.display_name}
                      </div>
                      <div className="text-[10px] text-muted-foreground">
                        {isConnected
                          ? "Connected — click to add another account"
                          : "Click to connect"}
                      </div>
                    </div>
                    {isConnecting ? (
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    ) : isConnected ? (
                      <Check className="h-4 w-4 text-green-500" />
                    ) : (
                      <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
                    )}
                  </button>
                );
              })}
            </div>
          )}

          <p className="text-[11px] text-muted-foreground">
            Connect multiple accounts of the same type (e.g. personal + work
            Gmail). Data is automatically synced every hour.
          </p>
        </div>
      )}

      {/* Connected sources list */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      ) : connected.length > 0 ? (
        <div className="space-y-2">
          {connected.map((src) => (
            <div
              key={src.id}
              className="flex items-center justify-between p-4 rounded-xl border border-border bg-card hover:border-border/80 transition-all group"
            >
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-accent/50 flex items-center justify-center">
                  <ProviderIcon
                    provider={src.provider_type}
                    className="h-4.5 w-4.5 text-foreground/70"
                  />
                </div>
                <div>
                  <div className="text-sm font-medium">{src.display_name}</div>
                  <div className="text-[11px] text-muted-foreground flex items-center gap-2">
                    <span className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                      Connected
                    </span>
                    <span className="opacity-40">|</span>
                    <span>{timeAgo(src.created_at)}</span>
                    <span className="opacity-40">|</span>
                    <span className="font-mono text-[10px] opacity-40">
                      {src.connection_id.slice(0, 8)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => handleConnect(src.provider_type)}
                  disabled={connecting === src.provider_type}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs hover:bg-accent transition-all"
                  title="Reconnect with a different account"
                >
                  {connecting === src.provider_type ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <RefreshCw className="h-3 w-3" />
                  )}
                  Reconnect
                </button>
                <button
                  onClick={() => handleDisconnect(src)}
                  disabled={disconnecting === src.connection_id}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs text-destructive hover:bg-destructive/10 hover:border-destructive/30 transition-all"
                >
                  {disconnecting === src.connection_id ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Trash2 className="h-3 w-3" />
                  )}
                  Disconnect
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-16 space-y-4">
          <Cable className="h-10 w-10 text-muted-foreground/20 mx-auto" />
          <div>
            <h3 className="font-medium">No sources connected</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Click "Add Source" above or go through the{" "}
              <button
                onClick={() => navigate("/onboarding")}
                className="text-primary hover:underline"
              >
                onboarding flow
              </button>
              .
            </p>
          </div>
        </div>
      )}

      {/* Sync result message */}
      {ingestMsg && (
        <div className="p-3 rounded-xl bg-card border border-border text-sm text-muted-foreground animate-fade-in">
          {ingestMsg}
        </div>
      )}
    </div>
  );
}
