import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  ExternalLink,
  Sparkles,
  Shield,
} from "lucide-react";

interface FreshnessInfo {
  status: "live" | "cached" | "immutable";
  cache_age_seconds?: number;
}

interface Citation {
  source_name: string;
  source_ref: string;
  snippet: string;
}

interface Claim {
  text: string;
  citation: Citation;
  freshness: FreshnessInfo;
  layer: "canon_declared" | "personal";
  is_downgraded: boolean;
}

interface ConflictBlock {
  fact_description: string;
  value_a: string;
  value_a_source: string;
  value_a_age: string;
  value_b: string;
  value_b_source: string;
  value_b_age: string;
  winner: "a" | "b";
  arbitration_rule: string;
}

interface PromotionPrompt {
  claim_text: string;
  replaces_value?: string;
  replaces_age?: string;
}

interface Envelope {
  question: string;
  summary: string;
  claims: Claim[];
  conflicts: ConflictBlock[];
  promotion_prompt?: PromotionPrompt;
  live_reads_count: number;
  cached_reads_count: number;
}

function FreshnessBadge({ freshness }: { freshness: FreshnessInfo }) {
  const config = {
    live: {
      label: "Live",
      className: "bg-freshness-live/10 text-freshness-live border-freshness-live/20",
      icon: CheckCircle2,
    },
    cached: {
      label: freshness.cache_age_seconds
        ? `Cached ${Math.round(freshness.cache_age_seconds / 60)}m ago`
        : "Cached",
      className: "bg-freshness-cached/10 text-freshness-cached border-freshness-cached/20",
      icon: Clock,
    },
    immutable: {
      label: "Immutable",
      className: "bg-freshness-immutable/10 text-freshness-immutable border-freshness-immutable/20",
      icon: Shield,
    },
  }[freshness.status];

  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded border ${config.className}`}
    >
      <Icon className="h-2.5 w-2.5" />
      {config.label}
    </span>
  );
}

function LayerIndicator({ layer }: { layer: "canon_declared" | "personal" }) {
  return (
    <span
      className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
        layer === "canon_declared"
          ? "bg-layer-canon/10 text-layer-canon"
          : "bg-layer-personal/10 text-layer-personal"
      }`}
    >
      {layer === "canon_declared" ? "Canon" : "Personal"}
    </span>
  );
}

function ConflictDisplay({ conflict }: { conflict: ConflictBlock }) {
  return (
    <div className="border border-conflict-border bg-conflict-surface rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium">
        <AlertTriangle className="h-4 w-4 text-destructive" />
        <span>Conflict: {conflict.fact_description}</span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div
          className={`p-3 rounded-md border ${
            conflict.winner === "a"
              ? "bg-conflict-winner border-green-300"
              : "border-border bg-background"
          }`}
        >
          <div className="text-xs text-muted-foreground mb-1">
            {conflict.value_a_source}{" "}
            <span className="text-[10px]">({conflict.value_a_age})</span>
          </div>
          <div className="text-sm font-medium">{conflict.value_a}</div>
          {conflict.winner === "a" && (
            <div className="text-[10px] text-green-700 mt-1 font-medium">
              Winner
            </div>
          )}
        </div>

        <div
          className={`p-3 rounded-md border ${
            conflict.winner === "b"
              ? "bg-conflict-winner border-green-300"
              : "border-border bg-background"
          }`}
        >
          <div className="text-xs text-muted-foreground mb-1">
            {conflict.value_b_source}{" "}
            <span className="text-[10px]">({conflict.value_b_age})</span>
          </div>
          <div className="text-sm font-medium">{conflict.value_b}</div>
          {conflict.winner === "b" && (
            <div className="text-[10px] text-green-700 mt-1 font-medium">
              Winner
            </div>
          )}
        </div>
      </div>

      <p className="text-xs text-muted-foreground italic">
        {conflict.arbitration_rule}
      </p>
    </div>
  );
}

export function AnswerEnvelope({ envelope }: { envelope: Envelope }) {
  return (
    <div className="space-y-4 max-w-3xl">
      {/* Question */}
      <div className="flex items-start gap-3">
        <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center shrink-0 mt-0.5">
          <span className="text-xs font-medium">Q</span>
        </div>
        <p className="text-sm font-medium pt-1">{envelope.question}</p>
      </div>

      {/* Answer */}
      <div className="flex items-start gap-3">
        <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
        </div>
        <div className="space-y-4 flex-1">
          <p className="text-sm leading-relaxed">{envelope.summary}</p>

          {/* Claims with inline citations */}
          {envelope.claims.length > 0 && (
            <div className="space-y-2">
              {envelope.claims.map((claim, i) => (
                <div
                  key={i}
                  className={`text-sm p-3 rounded-md border ${
                    claim.is_downgraded
                      ? "border-dashed border-muted opacity-70"
                      : "border-border"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="flex-1">{claim.text}</p>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <FreshnessBadge freshness={claim.freshness} />
                      <LayerIndicator layer={claim.layer} />
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                    <ExternalLink className="h-3 w-3" />
                    <span>
                      {claim.citation.source_name} — {claim.citation.source_ref}
                    </span>
                  </div>
                  {claim.is_downgraded && (
                    <p className="text-[10px] text-destructive mt-1">
                      Could not be verified live — shown with reduced confidence
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Conflicts — NEVER silently resolved */}
          {envelope.conflicts.map((conflict, i) => (
            <ConflictDisplay key={i} conflict={conflict} />
          ))}

          {/* Promotion prompt — at most one */}
          {envelope.promotion_prompt && (
            <div className="border border-primary/20 bg-primary/5 rounded-lg p-4 space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Sparkles className="h-4 w-4 text-primary" />
                Would you like to declare this?
              </div>
              <p className="text-sm">
                {envelope.promotion_prompt.claim_text}
              </p>
              {envelope.promotion_prompt.replaces_value && (
                <p className="text-xs text-muted-foreground">
                  Replaces: {envelope.promotion_prompt.replaces_value} (
                  {envelope.promotion_prompt.replaces_age})
                </p>
              )}
              <div className="flex gap-2 pt-1">
                <button className="px-3 py-1.5 text-xs rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
                  Accept
                </button>
                <button className="px-3 py-1.5 text-xs rounded-md border border-border text-muted-foreground hover:bg-accent transition-colors">
                  Dismiss
                </button>
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="flex gap-4 text-[10px] text-muted-foreground">
            <span>{envelope.live_reads_count} live reads</span>
            <span>{envelope.cached_reads_count} cached reads</span>
          </div>
        </div>
      </div>
    </div>
  );
}
