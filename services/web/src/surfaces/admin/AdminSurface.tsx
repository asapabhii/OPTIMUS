import { useState, useEffect } from "react";
import {
  Shield,
  Cog,
  Activity,
  ChevronDown,
  ChevronRight,
  Globe,
  Mail,
  MessageSquare,
  Lock,
  FileText,
  Play,
  RotateCcw,
} from "lucide-react";
import { api, getUserId } from "../../api/client";

type AdminTab = "permissions" | "gateways" | "processes" | "writeback" | "jobs";

interface GatewayStatus {
  slack: { enabled: boolean; paired: number };
  email: { enabled: boolean; paired: number };
  total_messages: number;
}

interface Program {
  id: string;
  name: string;
  description: string;
  steps: { index: number; name: string; type: string }[];
  parameters: string[];
  category: string;
  usage_count: number;
}

interface DecisionTable {
  id: string;
  name: string;
  description: string;
  entity_type: string;
  rules: { condition: string; action: string; priority: number }[];
}

interface Saga {
  id: string;
  target_source: string;
  entity_type: string;
  field: string;
  old_value: string;
  new_value: string;
  reason: string;
  status: string;
  revert_token: string;
  created_at: string;
}

interface Job {
  id: string;
  name: string;
  status: string;
  iteration: number;
  max_iterations: number;
  current_phase: string;
  created_at: string;
  steps: number;
}

export function AdminSurface() {
  const [tab, setTab] = useState<AdminTab>("gateways");
  const [gatewayStatus, setGatewayStatus] = useState<GatewayStatus | null>(null);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [tables, setTables] = useState<DecisionTable[]>([]);
  const [sagas, setSagas] = useState<Saga[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [programResults, setProgramResults] = useState<Record<string, string>>({});
  const [programParams, setProgramParams] = useState<Record<string, string>>({});

  useEffect(() => {
    loadData();
  }, [tab]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (tab === "gateways") {
        const resp = await api.get<GatewayStatus>("/api/v1/gateway/status");
        setGatewayStatus(resp.data);
      } else if (tab === "processes") {
        const [progs, tbls] = await Promise.all([
          api.get<Program[]>("/api/v1/processes/programs"),
          api.get<DecisionTable[]>("/api/v1/processes/tables"),
        ]);
        setPrograms(progs.data);
        setTables(tbls.data);
      } else if (tab === "writeback") {
        const resp = await api.get<Saga[]>("/api/v1/writeback/sagas");
        setSagas(resp.data);
      } else if (tab === "jobs") {
        const resp = await api.get<Job[]>("/api/v1/jobs");
        setJobs(resp.data);
      }
    } catch { /* ignore */ }
    setLoading(false);
  };

  const runProgram = async (program: Program) => {
    try {
      const resp = await api.post<{ run_id: string; status: string; results: { output?: string }[] }>(
        `/api/v1/processes/programs/${program.id}/run`,
        programParams,
        { params: { viewer_id: getUserId() } }
      );
      const output = resp.data.results?.map((r) => r.output || "").join("\n\n") || "Completed";
      setProgramResults({ ...programResults, [program.id]: output.slice(0, 500) });
    } catch { /* ignore */ }
  };

  const tabs: { id: AdminTab; label: string; icon: typeof Shield }[] = [
    { id: "gateways", label: "Gateways", icon: Globe },
    { id: "permissions", label: "Permissions", icon: Lock },
    { id: "processes", label: "Processes", icon: Cog },
    { id: "writeback", label: "Write-back", icon: RotateCcw },
    { id: "jobs", label: "Jobs", icon: Activity },
  ];

  return (
    <div className="h-full overflow-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Shield className="h-6 w-6 text-primary" />
          Administration
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Permissions, gateways, processes, write-back sagas, and long-horizon jobs
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-border overflow-x-auto">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all whitespace-nowrap ${
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

      {/* Gateways */}
      {tab === "gateways" && gatewayStatus && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border border-border rounded-xl p-5">
              <div className="flex items-center gap-3 mb-3">
                <MessageSquare className="h-5 w-5 text-purple-400" />
                <h3 className="font-medium">Slack Gateway</h3>
                <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${
                  gatewayStatus.slack.enabled ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                }`}>
                  {gatewayStatus.slack.enabled ? "Connected" : "Not configured"}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                Users can interact with the agent via Slack DM. DM pairing ensures security.
              </p>
              <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                <span>{gatewayStatus.slack.paired} paired users</span>
              </div>
              {!gatewayStatus.slack.enabled && (
                <p className="mt-3 text-xs text-yellow-400">
                  Set SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET in environment variables.
                </p>
              )}
            </div>
            <div className="border border-border rounded-xl p-5">
              <div className="flex items-center gap-3 mb-3">
                <Mail className="h-5 w-5 text-blue-400" />
                <h3 className="font-medium">Email Gateway</h3>
                <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${
                  gatewayStatus.email.enabled ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                }`}>
                  {gatewayStatus.email.enabled ? "Connected" : "Not configured"}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                The agent can receive and reply to emails. Auto-pairs by email address.
              </p>
              <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                <span>{gatewayStatus.email.paired} paired users</span>
              </div>
              {!gatewayStatus.email.enabled && (
                <p className="mt-3 text-xs text-yellow-400">
                  Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in environment variables.
                </p>
              )}
            </div>
          </div>
          <div className="text-xs text-muted-foreground">
            Total gateway messages: {gatewayStatus.total_messages}
          </div>
        </div>
      )}

      {/* Permissions */}
      {tab === "permissions" && (
        <div className="space-y-4">
          <div className="border border-border rounded-xl p-5">
            <h3 className="font-medium flex items-center gap-2 mb-2">
              <Lock className="h-4 w-4 text-primary" />
              AuthZed Permission Model
            </h3>
            <p className="text-xs text-muted-foreground mb-4">
              Two independent gates per query: Source gate (live viewer-token check) and Audience gate
              (AuthZed relationship check). No fact is served unless both pass.
            </p>
            <div className="space-y-2">
              <div className="p-3 rounded-lg bg-muted/20 border border-border/50">
                <span className="text-xs font-mono text-primary">user</span>
                <span className="text-xs text-muted-foreground ml-2">
                  Base subject type. All access checks start from a user.
                </span>
              </div>
              <div className="p-3 rounded-lg bg-muted/20 border border-border/50">
                <span className="text-xs font-mono text-primary">team</span>
                <span className="text-xs text-muted-foreground ml-2">
                  member, admin. Permission: view = member + admin, manage = admin.
                </span>
              </div>
              <div className="p-3 rounded-lg bg-muted/20 border border-border/50">
                <span className="text-xs font-mono text-primary">organization</span>
                <span className="text-xs text-muted-foreground ml-2">
                  member, admin, owner. Permission: view = member + admin + owner.
                </span>
              </div>
              <div className="p-3 rounded-lg bg-muted/20 border border-border/50">
                <span className="text-xs font-mono text-primary">entity</span>
                <span className="text-xs text-muted-foreground ml-2">
                  owner, viewer. Permission: view = owner + viewer, edit = owner.
                </span>
              </div>
              <div className="p-3 rounded-lg bg-muted/20 border border-border/50">
                <span className="text-xs font-mono text-primary">canon_assertion</span>
                <span className="text-xs text-muted-foreground ml-2">
                  author, audience. Permission: view = audience + org member, approve = org admin.
                </span>
              </div>
            </div>
          </div>
          <div className="text-xs text-muted-foreground">
            Configure AUTHZED_ENDPOINT and AUTHZED_TOKEN for production. In development, permissions
            use a local fallback (allow all when no relationships exist).
          </div>
        </div>
      )}

      {/* Processes */}
      {tab === "processes" && (
        <div className="space-y-6">
          <div>
            <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              Saved Programs ({programs.length})
            </h3>
            <div className="space-y-3">
              {programs.map((program) => (
                <div key={program.id} className="border border-border rounded-xl overflow-hidden">
                  <button
                    onClick={() => setExpandedId(expandedId === program.id ? null : program.id)}
                    className="w-full flex items-center gap-3 p-4 text-left hover:bg-accent/10 transition-all"
                  >
                    {expandedId === program.id ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    <div className="flex-1">
                      <span className="text-sm font-medium">{program.name}</span>
                      <p className="text-xs text-muted-foreground">{program.description}</p>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                      {program.steps.length} steps
                    </span>
                    <span className="text-[10px] text-muted-foreground">{program.usage_count} runs</span>
                  </button>
                  {expandedId === program.id && (
                    <div className="px-4 pb-4 border-t border-border/50 space-y-3">
                      <div className="space-y-1 mt-3">
                        {program.steps.map((step) => (
                          <div key={step.index} className="flex items-center gap-2 text-xs p-2 rounded bg-muted/20">
                            <span className="text-primary font-mono w-5">{step.index}</span>
                            <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                              step.type === "deterministic" ? "bg-blue-500/20 text-blue-400" :
                              step.type === "judgment" ? "bg-yellow-500/20 text-yellow-400" :
                              step.type === "human" ? "bg-purple-500/20 text-purple-400" :
                              "bg-green-500/20 text-green-400"
                            }`}>{step.type}</span>
                            <span>{step.name}</span>
                          </div>
                        ))}
                      </div>
                      {program.parameters.length > 0 && (
                        <div className="flex gap-2 flex-wrap">
                          {program.parameters.map((p) => (
                            <input
                              key={p}
                              placeholder={p}
                              value={programParams[p] || ""}
                              onChange={(e) => setProgramParams({ ...programParams, [p]: e.target.value })}
                              className="px-3 py-1.5 rounded-lg border border-input bg-background text-xs focus:outline-none focus:ring-1 focus:ring-primary/30"
                            />
                          ))}
                        </div>
                      )}
                      <button
                        onClick={() => runProgram(program)}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-all"
                      >
                        <Play className="h-3 w-3" />
                        Run program
                      </button>
                      {programResults[program.id] && (
                        <div className="p-3 rounded-lg bg-muted/20 border border-border/50 text-xs">
                          {programResults[program.id]}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
              <Cog className="h-4 w-4 text-primary" />
              Decision Tables ({tables.length})
            </h3>
            <div className="space-y-3">
              {tables.map((table) => (
                <div key={table.id} className="border border-border rounded-xl p-4">
                  <h4 className="text-sm font-medium">{table.name}</h4>
                  <p className="text-xs text-muted-foreground">{table.description}</p>
                  <div className="mt-2 space-y-1">
                    {table.rules.map((rule, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <span className="text-muted-foreground font-mono">if</span>
                        <span className="text-primary">{rule.condition}</span>
                        <span className="text-muted-foreground">then</span>
                        <span className="font-medium">{rule.action}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Write-back */}
      {tab === "writeback" && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Write-back sagas ensure exactly-once semantics for mutations to systems of record.
            Each saga follows: Propose, Dry-run, Approve, Execute, Verify, with a one-click Revert.
          </p>
          {sagas.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <RotateCcw className="h-8 w-8 mx-auto mb-3 opacity-50" />
              <p className="text-sm">No write-back sagas yet</p>
              <p className="text-xs mt-1">Write-backs are created when you modify data in a system of record</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sagas.map((saga) => (
                <div key={saga.id} className="border border-border rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">{saga.target_source} / {saga.field}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      saga.status === "completed" ? "bg-green-500/20 text-green-400" :
                      saga.status === "failed" ? "bg-red-500/20 text-red-400" :
                      saga.status === "reverted" ? "bg-yellow-500/20 text-yellow-400" :
                      "bg-blue-500/20 text-blue-400"
                    }`}>{saga.status}</span>
                  </div>
                  <div className="text-xs text-muted-foreground space-y-1">
                    <div><span className="text-red-400">{saga.old_value}</span> <span className="mx-1">-&gt;</span> <span className="text-green-400">{saga.new_value}</span></div>
                    {saga.reason && <div>{saga.reason}</div>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Long-horizon Jobs */}
      {tab === "jobs" && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Multi-week autonomous jobs that wake on signals, evaluate decisions, execute tasks,
            and send interactions. The system goes dormant between iterations.
          </p>
          {jobs.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Activity className="h-8 w-8 mx-auto mb-3 opacity-50" />
              <p className="text-sm">No long-horizon jobs yet</p>
              <p className="text-xs mt-1">Create jobs for multi-week autonomous tasks like renewals, onboarding sequences, or collections</p>
            </div>
          ) : (
            <div className="space-y-3">
              {jobs.map((job) => (
                <div key={job.id} className="border border-border rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">{job.name}</span>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        job.status === "active" || job.status === "processing" ? "bg-green-500/20 text-green-400" :
                        job.status === "dormant" ? "bg-blue-500/20 text-blue-400" :
                        job.status === "completed" ? "bg-gray-500/20 text-gray-400" :
                        "bg-red-500/20 text-red-400"
                      }`}>{job.status}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>Phase: {job.current_phase}</span>
                    <span>Iteration: {job.iteration}/{job.max_iterations}</span>
                    <span>{job.steps} steps executed</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
