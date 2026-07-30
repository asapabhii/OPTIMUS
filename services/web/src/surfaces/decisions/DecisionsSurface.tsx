import { useState, useEffect } from "react";
import {
  ListChecks,
  GitMerge,
  X,
  Loader2,
  RefreshCw,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  BarChart3,
  Info,
} from "lucide-react";
import { api } from "../../api/client";

interface ERDecision {
  decision_id: string;
  entity_a_name: string;
  entity_b_name: string;
  entity_type: string;
  similarity: number;
  status: string;
  sources: string[];
  created_at: string;
  evidence?: Record<string, any>;
}

interface DecisionQueue {
  decisions: ERDecision[];
  total_pending: number;
  total_resolved: number;
}

function SimilarityBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 85 ? "bg-green-500" : pct >= 70 ? "bg-amber-500" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-1.5 bg-accent rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span
        className={`text-xs font-mono font-bold ${
          pct >= 85
            ? "text-green-500"
            : pct >= 70
            ? "text-amber-500"
            : "text-red-400"
        }`}
      >
        {pct}%
      </span>
    </div>
  );
}

function EvidencePanel({ evidence }: { evidence: Record<string, any> }) {
  const reason = evidence?.reason || "No details available";
  const penalties: string[] = evidence?.penalties || [];

  const metrics = [
    { label: "Token Sort", value: evidence?.token_sort, desc: "Word-order-independent similarity" },
    { label: "Character Ratio", value: evidence?.ratio, desc: "Direct character-level match" },
    { label: "Weighted Ratio", value: evidence?.wratio, desc: "Best partial/full match combination" },
    { label: "Combined Score", value: evidence?.fuzzy_combined, desc: "Weighted combination of all metrics" },
    { label: "Attribute Bonus", value: evidence?.attr_bonus, desc: "Extra points for matching domain/email" },
    { label: "Final Score", value: evidence?.final_score, desc: "Score after bonuses and penalties" },
  ].filter((m) => m.value !== undefined);

  return (
    <div className="mt-3 pt-3 border-t border-border/50 space-y-3 animate-fade-in">
      {/* Reason summary */}
      <div className="flex items-start gap-2">
        <Info className="h-3.5 w-3.5 text-blue-400 mt-0.5 shrink-0" />
        <p className="text-xs text-muted-foreground leading-relaxed">{reason}</p>
      </div>

      {/* Normalized names */}
      {evidence?.name_a_normalized && (
        <div className="text-xs text-muted-foreground/70 space-y-0.5">
          <div>
            Comparing: <span className="font-mono text-foreground">"{evidence.name_a_normalized}"</span>{" "}
            vs <span className="font-mono text-foreground">"{evidence.name_b_normalized}"</span>
          </div>
        </div>
      )}

      {/* Score breakdown */}
      {metrics.length > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {metrics.map((m) => (
            <div key={m.label} className="p-2 rounded-lg bg-accent/30">
              <div className="text-[10px] text-muted-foreground/60">{m.label}</div>
              <div className={`text-sm font-bold font-mono ${
                (m.value || 0) >= 80 ? "text-green-500" : (m.value || 0) >= 60 ? "text-amber-500" : "text-red-400"
              }`}>
                {m.value?.toFixed(1)}%
              </div>
              <div className="text-[9px] text-muted-foreground/40">{m.desc}</div>
            </div>
          ))}
        </div>
      )}

      {/* Penalties */}
      {penalties.length > 0 && (
        <div className="space-y-1">
          <div className="text-[10px] text-red-400 font-medium uppercase tracking-wider">Penalties Applied</div>
          {penalties.map((p, i) => (
            <div key={i} className="text-xs text-red-400/80 flex items-center gap-1.5">
              <span className="w-1 h-1 rounded-full bg-red-400 shrink-0" />
              {p}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function DecisionsSurface() {
  const [data, setData] = useState<DecisionQueue | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<
    "all" | "pending" | "merged" | "rejected"
  >("all");
  const [resolving, setResolving] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchDecisions = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {
        viewer_id: "00000000-0000-0000-0000-000000000001",
      };
      if (filter !== "all") params.status = filter;

      const resp = await api.get<DecisionQueue>("/api/v1/decisions", {
        params,
      });
      setData(resp.data);
    } catch {
      setData({ decisions: [], total_pending: 0, total_resolved: 0 });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDecisions();
  }, [filter]);

  const handleResolve = async (
    decisionId: string,
    action: "merge" | "reject" | "skip"
  ) => {
    if (action === "skip") {
      setExpandedId(null);
      return;
    }
    setResolving(decisionId);
    try {
      await api.post(`/api/v1/decisions/${decisionId}/resolve`, null, {
        params: { action },
      });
      setExpandedId(null);
      await fetchDecisions();
    } catch {
      /* no-op */
    } finally {
      setResolving(null);
    }
  };

  return (
    <div className="space-y-6 p-6 h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ListChecks className="h-6 w-6 text-primary" />
            Entity Resolution Decisions
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {data
              ? `${data.total_pending} need${data.total_pending !== 1 ? "" : "s"} review · ${data.total_resolved} auto-resolved`
              : "Loading..."}
          </p>
        </div>
        <button
          onClick={fetchDecisions}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border text-sm hover:bg-accent transition-all"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-1">
        {(
          [
            { value: "all", label: "All" },
            { value: "pending", label: "Pending" },
            { value: "merged", label: "Merged" },
            { value: "rejected", label: "Rejected" },
          ] as const
        ).map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-2 rounded-lg text-xs font-medium transition-all ${
              filter === f.value
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : data && data.decisions.length > 0 ? (
        <div className="grid gap-3">
          {data.decisions.map((d) => {
            const isExpanded = expandedId === d.decision_id;

            return (
              <div
                key={d.decision_id}
                className={`rounded-xl border transition-all overflow-hidden ${
                  d.status === "pending"
                    ? "border-amber-500/20 bg-amber-500/5"
                    : d.status === "merged"
                    ? "border-green-500/20 bg-green-500/5"
                    : "border-border"
                }`}
              >
                {/* Main row — clickable */}
                <button
                  onClick={() => setExpandedId(isExpanded ? null : d.decision_id)}
                  className="w-full flex items-start justify-between p-4 text-left hover:bg-accent/20 transition-all"
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                      )}
                      {d.status === "pending" && (
                        <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                      )}
                      {d.status === "merged" && (
                        <GitMerge className="h-4 w-4 text-green-500 shrink-0" />
                      )}
                      {d.status === "rejected" && (
                        <X className="h-4 w-4 text-red-400 shrink-0" />
                      )}
                      <span className="text-sm font-medium">
                        "{d.entity_a_name}"
                      </span>
                      <span className="text-xs text-muted-foreground">may be the same as</span>
                      <span className="text-sm font-medium">
                        "{d.entity_b_name}"
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground pl-6">
                      <span className="capitalize px-1.5 py-0.5 rounded bg-accent/50">{d.entity_type}</span>
                      <SimilarityBar score={d.similarity} />
                      <span>Sources: {d.sources.join(", ")}</span>
                    </div>
                  </div>

                  {d.status !== "pending" && (
                    <span
                      className={`text-xs font-medium px-2 py-1 rounded-full shrink-0 ${
                        d.status === "merged"
                          ? "bg-green-500/10 text-green-500"
                          : "bg-accent text-muted-foreground"
                      }`}
                    >
                      {d.status}
                    </span>
                  )}
                </button>

                {/* Expanded evidence + actions */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-0">
                    {d.evidence && <EvidencePanel evidence={d.evidence} />}

                    {d.status === "pending" && (
                      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-border/50">
                        <BarChart3 className="h-3.5 w-3.5 text-muted-foreground/40" />
                        <span className="text-[10px] text-muted-foreground/40 flex-1">
                          Review the evidence above and decide if these represent the same entity
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleResolve(d.decision_id, "merge");
                          }}
                          disabled={resolving === d.decision_id}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-green-600 text-white text-xs font-medium hover:bg-green-700 disabled:opacity-50 transition-all"
                        >
                          {resolving === d.decision_id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <GitMerge className="h-3 w-3" />
                          )}
                          Yes, Merge
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleResolve(d.decision_id, "reject");
                          }}
                          disabled={resolving === d.decision_id}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border text-xs font-medium hover:bg-destructive/10 hover:text-destructive disabled:opacity-50 transition-all"
                        >
                          <X className="h-3 w-3" />
                          Not the same
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleResolve(d.decision_id, "skip");
                          }}
                          disabled={resolving === d.decision_id}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border text-xs font-medium hover:bg-muted/40 disabled:opacity-50 transition-all"
                        >
                          Skip
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-20 space-y-4">
          <ListChecks className="h-12 w-12 text-muted-foreground/30 mx-auto" />
          <div>
            <h3 className="font-medium">No decisions yet</h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
              Entity resolution decisions will appear here once data has been
              ingested from your connected sources. Potential duplicates are
              detected automatically using name similarity, domain matching, and
              attribute comparison.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
