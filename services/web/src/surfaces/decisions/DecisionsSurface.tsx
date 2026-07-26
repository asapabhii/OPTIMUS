import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ListChecks, RotateCcw, Check, AlertTriangle } from "lucide-react";
import { api } from "../../api/client";

interface AutoDecision {
  id: string;
  decision_type: string;
  input_data: Record<string, string>;
  output_data: Record<string, string>;
  explanation: string;
  confidence: number;
  applied_automatically: boolean;
  reversed: boolean;
  reversed_at: string | null;
  reversed_reason: string | null;
  created_at: string;
}

export function DecisionsSurface() {
  const queryClient = useQueryClient();

  const decisionsQuery = useQuery({
    queryKey: ["decisions"],
    queryFn: async () => {
      const response = await api.get<{
        decisions: AutoDecision[];
        total: number;
      }>("/api/v1/decisions", {
        params: {
          viewer_id: "00000000-0000-0000-0000-000000000001",
        },
      });
      return response.data;
    },
  });

  const revertMutation = useMutation({
    mutationFn: async (decisionId: string) => {
      return api.post("/api/v1/decisions/revert", {
        decision_id: decisionId,
        reason: "User review",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["decisions"] });
    },
  });

  const decisions = decisionsQuery.data?.decisions ?? [];

  const decisionTypeLabels: Record<string, string> = {
    entity_merge: "Entity Merge",
    freshness_classification: "Freshness Classification",
    storage_policy: "Storage Policy",
    resolution_rule_applied: "Resolution Rule Applied",
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-border px-8 py-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <ListChecks className="h-5 w-5" />
          Decisions
        </h2>
        <p className="text-sm text-muted-foreground">
          Every automatic decision is visible and reversible in one click
        </p>
      </div>

      {/* Decision list */}
      <div className="flex-1 overflow-auto px-8 py-6">
        {decisions.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-3">
              <ListChecks className="h-12 w-12 text-muted-foreground mx-auto" />
              <h3 className="text-lg font-medium text-muted-foreground">
                No decisions yet
              </h3>
              <p className="text-sm text-muted-foreground max-w-md">
                As the system resolves entities and classifies data, every
                automatic decision will appear here for your review.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {decisions.map((decision) => (
              <div
                key={decision.id}
                className={`border rounded-lg p-4 transition-colors ${
                  decision.reversed
                    ? "border-muted bg-muted/30 opacity-60"
                    : "border-border hover:border-foreground/20"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-accent text-accent-foreground font-medium">
                        {decisionTypeLabels[decision.decision_type] ??
                          decision.decision_type}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        Confidence: {(decision.confidence * 100).toFixed(0)}%
                      </span>
                      {decision.reversed && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-destructive/10 text-destructive font-medium">
                          Reversed
                        </span>
                      )}
                    </div>
                    <p className="text-sm">{decision.explanation}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(decision.created_at).toLocaleString()}
                    </p>
                  </div>

                  {!decision.reversed && (
                    <button
                      onClick={() => revertMutation.mutate(decision.id)}
                      disabled={revertMutation.isPending}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md border border-border text-muted-foreground hover:bg-destructive/10 hover:text-destructive hover:border-destructive/20 transition-colors"
                    >
                      <RotateCcw className="h-3 w-3" />
                      Revert
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
