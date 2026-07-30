import { useState, useEffect } from "react";
import {
  Play,
  Loader2,
  Zap,
  ListTodo,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Wrench,
  Send,
  Calendar,
  BookOpen,
} from "lucide-react";
import { api, getUserId } from "../../api/client";

interface WorkResult {
  task_id: string;
  status: string;
  result: { output?: string; skill?: string };
  steps: { tool: string; args: Record<string, unknown>; result_summary: string; iteration: number }[];
  latency_ms: number;
}

interface Skill {
  id: string;
  name: string;
  description: string;
  prompt_template: string;
  parameters: string[];
  category: string;
  usage_count: number;
}

interface CrewPlan {
  plan_id: string;
  message: string;
  workstreams: { index: number; objective: string; kind: string; depends_on: number[] }[];
}

type Tab = "agent" | "crew" | "skills" | "brief";

export function WorkSurface() {
  const [tab, setTab] = useState<Tab>("agent");
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WorkResult | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [crewPlan, setCrewPlan] = useState<CrewPlan | null>(null);
  const [crewResults, setCrewResults] = useState<Record<string, unknown>[] | null>(null);
  const [briefResult, setBriefResult] = useState<WorkResult | null>(null);
  const [expandedSteps, setExpandedSteps] = useState(false);
  const [skillParams, setSkillParams] = useState<Record<string, string>>({});

  useEffect(() => {
    loadSkills();
  }, []);

  const loadSkills = async () => {
    try {
      const resp = await api.get<Skill[]>("/api/v1/work/skills");
      setSkills(resp.data);
    } catch { /* ignore */ }
  };

  const executeTask = async () => {
    if (!prompt.trim() || loading) return;
    setLoading(true);
    setResult(null);
    try {
      const resp = await api.post<WorkResult>("/api/v1/work/execute", {
        objective: prompt,
        viewer_id: getUserId(),
      });
      setResult(resp.data);
    } catch { /* ignore */ }
    setLoading(false);
  };

  const planCrew = async () => {
    if (!prompt.trim() || loading) return;
    setLoading(true);
    setCrewPlan(null);
    setCrewResults(null);
    try {
      const resp = await api.post<CrewPlan>("/api/v1/work/crew/plan", {
        brain_dump: prompt,
        viewer_id: getUserId(),
      });
      setCrewPlan(resp.data);
    } catch { /* ignore */ }
    setLoading(false);
  };

  const confirmCrew = async () => {
    if (!crewPlan || loading) return;
    setLoading(true);
    try {
      const resp = await api.post<{ results: Record<string, unknown>[] }>(
        `/api/v1/work/crew/${crewPlan.plan_id}/confirm`, {}
      );
      setCrewResults(resp.data.results);
    } catch { /* ignore */ }
    setLoading(false);
  };

  const runSkill = async (skill: Skill) => {
    setLoading(true);
    setResult(null);
    setTab("agent");
    try {
      const resp = await api.post<WorkResult>(
        `/api/v1/work/skills/${skill.id}/run`, skillParams
      );
      setResult(resp.data);
    } catch { /* ignore */ }
    setLoading(false);
  };

  const generateBrief = async () => {
    setLoading(true);
    setBriefResult(null);
    try {
      const resp = await api.post<WorkResult>("/api/v1/work/daily-brief", null, {
        params: { viewer_id: getUserId() },
      });
      setBriefResult(resp.data);
    } catch { /* ignore */ }
    setLoading(false);
  };

  const tabs: { id: Tab; label: string; icon: typeof Zap }[] = [
    { id: "agent", label: "Agent", icon: Zap },
    { id: "crew", label: "Crew", icon: ListTodo },
    { id: "skills", label: "Skills", icon: BookOpen },
    { id: "brief", label: "Daily Brief", icon: Calendar },
  ];

  return (
    <div className="h-full overflow-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Wrench className="h-6 w-6 text-primary" />
          Work Layer
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Agent engine, Crew delegation, Skills, and Daily Brief
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-border">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all ${
              tab === id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Agent tab */}
      {tab === "agent" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <input
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") executeTask(); }}
              placeholder="Describe what you need done (e.g., 'Analyze my deal pipeline and flag at-risk deals')"
              className="flex-1 px-4 py-3 rounded-xl border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
            />
            <button
              onClick={executeTask}
              disabled={loading || !prompt.trim()}
              className="flex items-center gap-2 px-5 py-3 rounded-xl bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-all"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Execute
            </button>
          </div>

          {result && (
            <div className="border border-border rounded-xl overflow-hidden">
              <div className="p-4 border-b border-border bg-card flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  <span className="text-sm font-medium">Task completed</span>
                </div>
                <span className="text-xs text-muted-foreground">{result.latency_ms}ms</span>
              </div>
              <div className="p-4">
                <div className="prose prose-invert prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: formatMarkdown(result.result.output || "") }} />
              </div>
              {result.steps.length > 0 && (
                <div className="border-t border-border">
                  <button
                    onClick={() => setExpandedSteps(!expandedSteps)}
                    className="w-full flex items-center gap-2 px-4 py-2 text-xs text-muted-foreground hover:bg-accent/30 transition-all"
                  >
                    {expandedSteps ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                    {result.steps.length} tool calls
                  </button>
                  {expandedSteps && (
                    <div className="px-4 pb-3 space-y-2">
                      {result.steps.map((step, i) => (
                        <div key={i} className="text-xs p-2 rounded bg-muted/20 border border-border/50">
                          <span className="font-mono text-primary">{step.tool}</span>
                          <span className="text-muted-foreground ml-2">{step.result_summary.slice(0, 150)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Crew tab */}
      {tab === "crew" && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Brain-dump everything you need done. The system decomposes it into workstreams, confirms with you, then dispatches sequentially.
          </p>
          <div className="flex gap-2">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Brain dump everything... (e.g., 'Review this week's pipeline, prep for the Acme renewal call, check if any contacts changed companies, and draft a weekly team update')"
              rows={4}
              className="flex-1 px-4 py-3 rounded-xl border border-input bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
            />
          </div>
          <button
            onClick={planCrew}
            disabled={loading || !prompt.trim()}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-all"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ListTodo className="h-4 w-4" />}
            Plan workstreams
          </button>

          {crewPlan && !crewResults && (
            <div className="border border-border rounded-xl p-4 space-y-3">
              <p className="text-sm font-medium">{crewPlan.message}</p>
              <div className="space-y-2">
                {crewPlan.workstreams.map((ws) => (
                  <div key={ws.index} className="flex items-start gap-3 p-3 rounded-lg bg-muted/20 border border-border/50">
                    <span className="text-xs font-mono text-primary mt-0.5">{ws.index}</span>
                    <div>
                      <p className="text-sm">{ws.objective}</p>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                        ws.kind === "ship" ? "bg-blue-500/20 text-blue-400" : "bg-yellow-500/20 text-yellow-400"
                      }`}>
                        {ws.kind}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              <button
                onClick={confirmCrew}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-all"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                Confirm and dispatch
              </button>
            </div>
          )}

          {crewResults && (
            <div className="border border-border rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <span className="text-sm font-medium">All workstreams completed</span>
              </div>
              {crewResults.map((r, i) => (
                <div key={i} className="p-3 rounded-lg bg-muted/20 border border-border/50">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-mono text-primary">{String(r.workstream)}</span>
                    <span className="text-sm font-medium">{String(r.objective)}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{String(r.output).slice(0, 300)}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Skills tab */}
      {tab === "skills" && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Pre-built workflows that run against your data. Click to execute.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {skills.map((skill) => (
              <div key={skill.id} className="border border-border rounded-xl p-4 hover:border-primary/30 transition-all">
                <h3 className="text-sm font-medium">{skill.name}</h3>
                <p className="text-xs text-muted-foreground mt-1">{skill.description}</p>
                {skill.parameters.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {skill.parameters.map((param) => (
                      <input
                        key={param}
                        placeholder={param.replace(/_/g, " ")}
                        value={skillParams[param] || ""}
                        onChange={(e) => setSkillParams({ ...skillParams, [param]: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-input bg-background text-xs focus:outline-none focus:ring-1 focus:ring-primary/30"
                      />
                    ))}
                  </div>
                )}
                <div className="flex items-center justify-between mt-3">
                  <span className="text-[10px] text-muted-foreground">{skill.usage_count} runs</span>
                  <button
                    onClick={() => runSkill(skill)}
                    disabled={loading}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50 transition-all"
                  >
                    <Play className="h-3 w-3" />
                    Run
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Daily Brief tab */}
      {tab === "brief" && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Generate a proactive daily brief from all your connected data.
          </p>
          <button
            onClick={generateBrief}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-all"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Calendar className="h-4 w-4" />}
            Generate daily brief
          </button>

          {briefResult && (
            <div className="border border-border rounded-xl overflow-hidden">
              <div className="p-4 border-b border-border bg-card flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-primary" />
                  <span className="text-sm font-medium">Daily Brief</span>
                </div>
                <span className="text-xs text-muted-foreground">{briefResult.latency_ms}ms</span>
              </div>
              <div className="p-4">
                <div className="prose prose-invert prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: formatMarkdown(briefResult.result.output || "") }} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function formatMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, "<code>$1</code>")
    .replace(/^### (.*$)/gm, "<h3>$1</h3>")
    .replace(/^## (.*$)/gm, "<h2>$1</h2>")
    .replace(/^# (.*$)/gm, "<h1>$1</h1>")
    .replace(/^- (.*$)/gm, "<li>$1</li>")
    .replace(/^\d+\. (.*$)/gm, "<li>$1</li>")
    .replace(/\n/g, "<br/>");
}
