import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { AnswerEnvelope } from "../../components/answer-envelope/AnswerEnvelope";
import { api } from "../../api/client";

interface AskResponse {
  envelope: {
    id: string;
    question: string;
    summary: string;
    claims: Array<{
      text: string;
      citation: {
        source_name: string;
        source_ref: string;
        snippet: string;
      };
      freshness: {
        status: "live" | "cached" | "immutable";
        cache_age_seconds?: number;
      };
      layer: "canon_declared" | "personal";
      is_downgraded: boolean;
    }>;
    conflicts: Array<{
      fact_description: string;
      value_a: string;
      value_a_source: string;
      value_a_age: string;
      value_b: string;
      value_b_source: string;
      value_b_age: string;
      winner: "a" | "b";
      arbitration_rule: string;
    }>;
    promotion_prompt?: {
      claim_text: string;
      replaces_value?: string;
      replaces_age?: string;
    };
    live_reads_count: number;
    cached_reads_count: number;
  };
}

export function AskSurface() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<AskResponse[]>([]);

  const askMutation = useMutation({
    mutationFn: async (q: string) => {
      const response = await api.post<AskResponse>("/api/v1/ask", {
        question: q,
        viewer_id: "00000000-0000-0000-0000-000000000001",
      });
      return response.data;
    },
    onSuccess: (data) => {
      setHistory((prev) => [...prev, data]);
      setQuestion("");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim()) {
      askMutation.mutate(question.trim());
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-border px-8 py-4">
        <h2 className="text-lg font-semibold">Ask</h2>
        <p className="text-sm text-muted-foreground">
          Every answer carries citations, freshness, and surfaces conflicts
        </p>
      </div>

      {/* Answer history */}
      <div className="flex-1 overflow-auto px-8 py-6 space-y-6">
        {history.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-3">
              <h3 className="text-xl font-medium text-muted-foreground">
                What do you want to know?
              </h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Ask about your customers, deals, renewals, or anything across
                your connected tools. Every answer shows its sources, freshness,
                and any conflicts found.
              </p>
              <div className="flex flex-wrap gap-2 justify-center pt-4">
                {[
                  "When does the Meridian renewal close?",
                  "What's our current pricing for enterprise tier?",
                  "Summarize all interactions with Acme Corp",
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => {
                      setQuestion(q);
                      askMutation.mutate(q);
                    }}
                    className="px-3 py-1.5 text-xs rounded-full border border-border text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {history.map((response, i) => (
          <AnswerEnvelope key={i} envelope={response.envelope} />
        ))}
      </div>

      {/* Input */}
      <div className="border-t border-border p-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="relative">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about your connected data..."
              className="w-full px-4 py-3 pr-12 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              disabled={askMutation.isPending}
            />
            <button
              type="submit"
              disabled={!question.trim() || askMutation.isPending}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-md hover:bg-accent disabled:opacity-50 transition-colors"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
