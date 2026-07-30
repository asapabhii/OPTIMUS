import { useState, useEffect } from "react";
import {
  BookOpen,
  Plus,
  Check,
  X,
  Loader2,
  RefreshCw,
  Shield,
  FileCheck,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Archive,
  Trash2,
  Database,
} from "lucide-react";
import { api, getCompanyDomain, getUserId } from "../../api/client";

interface Assertion {
  id: string;
  entity_name: string;
  entity_type: string;
  field: string;
  value: string;
  source: string;
  source_type: string;
  author: string;
  citation: string;
  status: string;
  audience: string[];
  stake_level: string;
  valid_from: string;
  valid_to: string;
  created_at: string;
  updated_at: string;
  superseded_by: string;
}

interface Proposal {
  id: string;
  action: string;
  assertion_id: string;
  entity_name: string;
  entity_type: string;
  field: string;
  old_value: string;
  new_value: string;
  source: string;
  citation: string;
  proposed_by: string;
  proposal_source: string;
  stake_level: string;
  status: string;
  reason: string;
  reviewed_by: string;
  reviewed_at: string;
  review_note: string;
  created_at: string;
}

interface SoRDeclaration {
  id: string;
  entity_type: string;
  field: string;
  authoritative_source: string;
  declared_by: string;
  reason: string;
  created_at: string;
}

interface CanonOverview {
  assertions: Assertion[];
  total_assertions: number;
  active_count: number;
  pending_proposals: number;
  sor_declarations: number;
}

interface ProposalQueue {
  proposals: Proposal[];
  total: number;
  pending: number;
  approved: number;
  rejected: number;
}

type Tab = "assertions" | "proposals" | "sor";

const STATUS_STYLES: Record<string, string> = {
  active: "text-green-500 bg-green-500/10",
  superseded: "text-amber-500 bg-amber-500/10",
  revoked: "text-red-400 bg-red-500/10",
  draft: "text-blue-400 bg-blue-500/10",
};

const STAKE_STYLES: Record<string, string> = {
  low: "text-green-500",
  medium: "text-amber-500",
  high: "text-red-400",
};

export function CanonSurface() {
  const [tab, setTab] = useState<Tab>("assertions");
  const [canon, setCanon] = useState<CanonOverview | null>(null);
  const [proposals, setProposals] = useState<ProposalQueue | null>(null);
  const [sorList, setSorList] = useState<SoRDeclaration[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [showAddSor, setShowAddSor] = useState(false);
  const [showPropose, setShowPropose] = useState(false);
  const [resolving, setResolving] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Form state
  const [form, setForm] = useState({
    entity_name: "",
    entity_type: "company",
    field: "",
    value: "",
    source: "",
    citation: "",
    stake_level: "medium",
  });

  const [sorForm, setSorForm] = useState({
    entity_type: "company",
    field: "",
    authoritative_source: "",
    reason: "",
  });

  const [proposeForm, setProposeForm] = useState({
    entity_name: "",
    entity_type: "company",
    field: "",
    new_value: "",
    source: "",
    reason: "",
  });

  const fetchAll = async () => {
    setLoading(true);
    try {
      const domain = getCompanyDomain();
      const [canonRes, proposalRes, sorRes] = await Promise.all([
        api.get<CanonOverview>("/api/v1/canon", { params: { company_domain: domain } }),
        api.get<ProposalQueue>("/api/v1/canon/proposals", { params: { company_domain: domain } }),
        api.get<SoRDeclaration[]>("/api/v1/canon/sor"),
      ]);
      setCanon(canonRes.data);
      setProposals(proposalRes.data);
      setSorList(sorRes.data);
    } catch {
      /* no-op */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleCreateAssertion = async () => {
    if (!form.entity_name || !form.field || !form.value) return;
    try {
      await api.post("/api/v1/canon/assertions", {
        ...form,
        author: getUserId(),
        company_domain: getCompanyDomain(),
      });
      setForm({ entity_name: "", entity_type: "company", field: "", value: "", source: "", citation: "", stake_level: "medium" });
      setShowAdd(false);
      await fetchAll();
    } catch {
      /* no-op */
    }
  };

  const handleCreateProposal = async () => {
    if (!proposeForm.entity_name || !proposeForm.field || !proposeForm.new_value) return;
    try {
      await api.post("/api/v1/canon/proposals", {
        ...proposeForm,
        action: "create",
        proposed_by: getUserId(),
        proposal_source: "user",
        company_domain: getCompanyDomain(),
      });
      setProposeForm({ entity_name: "", entity_type: "company", field: "", new_value: "", source: "", reason: "" });
      setShowPropose(false);
      await fetchAll();
    } catch {
      /* no-op */
    }
  };

  const handleCreateSoR = async () => {
    if (!sorForm.field || !sorForm.authoritative_source) return;
    try {
      await api.post("/api/v1/canon/sor", { ...sorForm, declared_by: "admin" });
      setSorForm({ entity_type: "company", field: "", authoritative_source: "", reason: "" });
      setShowAddSor(false);
      await fetchAll();
    } catch {
      /* no-op */
    }
  };

  const handleResolveProposal = async (id: string, action: "approve" | "reject") => {
    setResolving(id);
    try {
      await api.post(`/api/v1/canon/proposals/${id}/${action}`, null, {
        params: { reviewer: "admin" },
      });
      await fetchAll();
    } catch {
      /* no-op */
    } finally {
      setResolving(null);
    }
  };

  const handleRevokeAssertion = async (id: string) => {
    if (!confirm("Revoke this assertion? It will remain in history.")) return;
    try {
      await api.delete(`/api/v1/canon/assertions/${id}`);
      await fetchAll();
    } catch {
      /* no-op */
    }
  };

  const handleDeleteSoR = async (id: string) => {
    try {
      await api.delete(`/api/v1/canon/sor/${id}`);
      await fetchAll();
    } catch {
      /* no-op */
    }
  };

  const TABS: { id: Tab; label: string; icon: typeof BookOpen; count?: number }[] = [
    { id: "assertions", label: "Company Knowledge", icon: BookOpen, count: canon?.active_count },
    { id: "proposals", label: "Approval Queue", icon: FileCheck, count: proposals?.pending },
    { id: "sor", label: "Systems of Record", icon: Database, count: sorList.length },
  ];

  return (
    <div className="space-y-6 p-6 h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2 tracking-tight">
            <Shield className="h-6 w-6 text-primary" />
            Company Canon
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Governed, versioned company knowledge. Every fact has an author, a citation, and an approval.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchAll}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border text-sm hover:bg-accent transition-all"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          {tab === "assertions" && (
            <button
              onClick={() => setShowAdd(!showAdd)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-all"
            >
              <Plus className="h-4 w-4" />
              Add Assertion
            </button>
          )}
          {tab === "proposals" && (
            <button
              onClick={() => setShowPropose(!showPropose)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-all"
            >
              <Plus className="h-4 w-4" />
              Propose Change
            </button>
          )}
          {tab === "sor" && (
            <button
              onClick={() => setShowAddSor(!showAddSor)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-all"
            >
              <Plus className="h-4 w-4" />
              Declare SoR
            </button>
          )}
        </div>
      </div>

      {/* Stats row */}
      {canon && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Active Assertions", value: canon.active_count, color: "text-green-500" },
            { label: "Total (incl. history)", value: canon.total_assertions, color: "text-muted-foreground" },
            { label: "Pending Proposals", value: canon.pending_proposals, color: canon.pending_proposals > 0 ? "text-amber-500" : "text-muted-foreground" },
            { label: "SoR Declarations", value: canon.sor_declarations, color: "text-blue-400" },
          ].map((s) => (
            <div key={s.label} className="p-3 rounded-xl border border-border bg-card">
              <div className={`text-xl font-bold ${s.color}`}>{s.value}</div>
              <div className="text-[11px] text-muted-foreground mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-border pb-0">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all ${
              tab === t.id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
            {t.count !== undefined && t.count > 0 && (
              <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                t.id === "proposals" && t.count > 0
                  ? "bg-amber-500/10 text-amber-500"
                  : "bg-accent text-muted-foreground"
              }`}>
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Add Assertion form */}
      {showAdd && tab === "assertions" && (
        <div className="p-4 rounded-xl border border-primary/20 bg-card space-y-3 animate-fade-in">
          <h3 className="text-sm font-medium">New Company Assertion</h3>
          <div className="grid grid-cols-2 gap-3">
            <input className="px-3 py-2 rounded-lg border border-border bg-background text-sm" placeholder="Entity name (e.g. Acme Corp)" value={form.entity_name} onChange={(e) => setForm({ ...form, entity_name: e.target.value })} />
            <select className="px-3 py-2 rounded-lg border border-border bg-background text-sm" value={form.entity_type} onChange={(e) => setForm({ ...form, entity_type: e.target.value })}>
              <option value="company">Company</option>
              <option value="person">Person</option>
              <option value="deal">Deal</option>
              <option value="product">Product</option>
              <option value="process">Process</option>
              <option value="policy">Policy</option>
            </select>
            <input className="px-3 py-2 rounded-lg border border-border bg-background text-sm" placeholder="Field (e.g. contract_value)" value={form.field} onChange={(e) => setForm({ ...form, field: e.target.value })} />
            <input className="px-3 py-2 rounded-lg border border-border bg-background text-sm" placeholder="Value (e.g. $500K)" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} />
            <input className="px-3 py-2 rounded-lg border border-border bg-background text-sm" placeholder="Source (e.g. HubSpot)" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} />
            <input className="px-3 py-2 rounded-lg border border-border bg-background text-sm" placeholder="Citation / evidence" value={form.citation} onChange={(e) => setForm({ ...form, citation: e.target.value })} />
          </div>
          <div className="flex items-center gap-2">
            <select className="px-3 py-2 rounded-lg border border-border bg-background text-sm" value={form.stake_level} onChange={(e) => setForm({ ...form, stake_level: e.target.value })}>
              <option value="low">Low stake</option>
              <option value="medium">Medium stake</option>
              <option value="high">High stake</option>
            </select>
            <button onClick={handleCreateAssertion} className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90">
              Create
            </button>
            <button onClick={() => setShowAdd(false)} className="px-4 py-2 rounded-lg border border-border text-sm hover:bg-accent">Cancel</button>
          </div>
        </div>
      )}

      {/* Propose Change form */}
      {showPropose && tab === "proposals" && (
        <div className="p-4 rounded-xl border border-amber-500/20 bg-card space-y-3 animate-fade-in">
          <h3 className="text-sm font-medium">Propose a Change</h3>
          <div className="grid grid-cols-2 gap-3">
            <input className="px-3 py-2 rounded-lg border border-border bg-background text-sm" placeholder="Entity name" value={proposeForm.entity_name} onChange={(e) => setProposeForm({ ...proposeForm, entity_name: e.target.value })} />
            <select className="px-3 py-2 rounded-lg border border-border bg-background text-sm" value={proposeForm.entity_type} onChange={(e) => setProposeForm({ ...proposeForm, entity_type: e.target.value })}>
              <option value="company">Company</option>
              <option value="person">Person</option>
              <option value="deal">Deal</option>
              <option value="product">Product</option>
            </select>
            <input className="px-3 py-2 rounded-lg border border-border bg-background text-sm" placeholder="Field" value={proposeForm.field} onChange={(e) => setProposeForm({ ...proposeForm, field: e.target.value })} />
            <input className="px-3 py-2 rounded-lg border border-border bg-background text-sm" placeholder="Proposed value" value={proposeForm.new_value} onChange={(e) => setProposeForm({ ...proposeForm, new_value: e.target.value })} />
            <input className="px-3 py-2 rounded-lg border border-border bg-background text-sm col-span-2" placeholder="Reason for this change" value={proposeForm.reason} onChange={(e) => setProposeForm({ ...proposeForm, reason: e.target.value })} />
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreateProposal} className="px-4 py-2 rounded-lg bg-amber-600 text-white text-sm font-medium hover:bg-amber-700">Submit Proposal</button>
            <button onClick={() => setShowPropose(false)} className="px-4 py-2 rounded-lg border border-border text-sm hover:bg-accent">Cancel</button>
          </div>
        </div>
      )}

      {/* Add SoR form */}
      {showAddSor && tab === "sor" && (
        <div className="p-4 rounded-xl border border-blue-500/20 bg-card space-y-3 animate-fade-in">
          <h3 className="text-sm font-medium">Declare System of Record</h3>
          <p className="text-xs text-muted-foreground">Which source is authoritative for which data? This determines conflict resolution.</p>
          <div className="grid grid-cols-2 gap-3">
            <select className="px-3 py-2 rounded-lg border border-border bg-background text-sm" value={sorForm.entity_type} onChange={(e) => setSorForm({ ...sorForm, entity_type: e.target.value })}>
              <option value="company">Company</option>
              <option value="person">Person</option>
              <option value="deal">Deal</option>
            </select>
            <input className="px-3 py-2 rounded-lg border border-border bg-background text-sm" placeholder="Field (e.g. contract_value)" value={sorForm.field} onChange={(e) => setSorForm({ ...sorForm, field: e.target.value })} />
            <input className="px-3 py-2 rounded-lg border border-border bg-background text-sm" placeholder="Authoritative source (e.g. HubSpot)" value={sorForm.authoritative_source} onChange={(e) => setSorForm({ ...sorForm, authoritative_source: e.target.value })} />
            <input className="px-3 py-2 rounded-lg border border-border bg-background text-sm" placeholder="Reason" value={sorForm.reason} onChange={(e) => setSorForm({ ...sorForm, reason: e.target.value })} />
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreateSoR} className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700">Declare</button>
            <button onClick={() => setShowAddSor(false)} className="px-4 py-2 rounded-lg border border-border text-sm hover:bg-accent">Cancel</button>
          </div>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : (
        <>
          {/* Assertions tab */}
          {tab === "assertions" && (
            <div className="space-y-2">
              {canon && canon.assertions.length > 0 ? (
                canon.assertions.map((a) => {
                  const isExpanded = expandedId === a.id;
                  return (
                    <div key={a.id} className="rounded-xl border border-border bg-card overflow-hidden transition-all">
                      <button
                        onClick={() => setExpandedId(isExpanded ? null : a.id)}
                        className="w-full flex items-center gap-3 p-4 text-left hover:bg-accent/30 transition-all"
                      >
                        {isExpanded ? <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" /> : <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{a.entity_name}</span>
                            <span className="text-xs text-muted-foreground capitalize">{a.entity_type}</span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${STATUS_STYLES[a.status] || ""}`}>{a.status}</span>
                          </div>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            <span className="font-mono">{a.field}</span> = <span className="font-medium text-foreground">{a.value}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className={`text-[10px] font-medium ${STAKE_STYLES[a.stake_level] || ""}`}>
                            {a.stake_level}
                          </span>
                          <span className="text-[10px] text-muted-foreground/50">{a.created_at.slice(0, 10)}</span>
                        </div>
                      </button>
                      {isExpanded && (
                        <div className="px-4 pb-4 pt-0 border-t border-border/50 space-y-2 animate-fade-in">
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div><span className="text-muted-foreground">Source:</span> {a.source || "—"}</div>
                            <div><span className="text-muted-foreground">Author:</span> {a.author}</div>
                            <div><span className="text-muted-foreground">Citation:</span> {a.citation || "—"}</div>
                            <div><span className="text-muted-foreground">Audience:</span> {a.audience.join(", ")}</div>
                            <div><span className="text-muted-foreground">Valid from:</span> {a.valid_from ? a.valid_from.slice(0, 10) : "—"}</div>
                            <div><span className="text-muted-foreground">Valid to:</span> {a.valid_to ? a.valid_to.slice(0, 10) : "Current"}</div>
                          </div>
                          {a.status === "active" && (
                            <div className="flex gap-2 pt-1">
                              <button onClick={() => handleRevokeAssertion(a.id)} className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border text-xs text-destructive hover:bg-destructive/10 transition-all">
                                <Trash2 className="h-3 w-3" /> Revoke
                              </button>
                            </div>
                          )}
                          {a.superseded_by && (
                            <div className="text-xs text-amber-500 flex items-center gap-1">
                              <Archive className="h-3 w-3" /> Superseded by newer version
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-20 space-y-4">
                  <BookOpen className="h-10 w-10 text-muted-foreground/20 mx-auto" />
                  <div>
                    <h3 className="font-medium">No company knowledge yet</h3>
                    <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
                      Start by adding assertions about your company's key facts — contract values, renewal dates, team assignments.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Proposals tab */}
          {tab === "proposals" && (
            <div className="space-y-2">
              {proposals && proposals.proposals.length > 0 ? (
                proposals.proposals.map((p) => {
                  const isExpanded = expandedId === `p-${p.id}`;
                  const actionLabel =
                    p.action === "create"
                      ? "Add to Canon"
                      : p.action === "update"
                      ? "Update"
                      : p.action === "revoke"
                      ? "Remove from Canon"
                      : p.action;

                  return (
                    <div
                      key={p.id}
                      className={`rounded-xl border transition-all overflow-hidden ${
                        p.status === "pending"
                          ? "border-amber-500/20 bg-amber-500/5"
                          : p.status === "approved"
                          ? "border-green-500/20 bg-green-500/5"
                          : "border-border"
                      }`}
                    >
                      {/* Main row — clickable */}
                      <button
                        onClick={() => setExpandedId(isExpanded ? null : `p-${p.id}`)}
                        className="w-full flex items-start justify-between p-4 text-left hover:bg-accent/20 transition-all"
                      >
                        <div className="space-y-1.5 flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            {isExpanded ? (
                              <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                            ) : (
                              <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                            )}
                            {p.status === "pending" && <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />}
                            {p.status === "approved" && <Check className="h-4 w-4 text-green-500 shrink-0" />}
                            {p.status === "rejected" && <X className="h-4 w-4 text-red-400 shrink-0" />}
                            <span className="text-xs text-muted-foreground font-medium">{actionLabel}:</span>
                            <span className="text-sm font-medium">{p.entity_name}</span>
                            <span className="text-xs text-muted-foreground capitalize px-1.5 py-0.5 rounded bg-accent/50">{p.entity_type}</span>
                          </div>
                          <div className="text-xs text-muted-foreground pl-6">
                            {p.action === "create" ? (
                              <>
                                <span className="text-muted-foreground/70">{p.field}: </span>
                                <span className="font-medium text-foreground">{p.new_value}</span>
                                <span className="text-muted-foreground/50 ml-1.5">
                                  (from {p.source || "system"})
                                </span>
                              </>
                            ) : p.action === "update" ? (
                              <>
                                Change <span className="font-mono text-foreground">{p.field}</span>
                                {p.old_value && <span className="text-muted-foreground/50"> from {p.old_value}</span>}
                                {" "}to <span className="font-medium text-foreground">{p.new_value}</span>
                              </>
                            ) : (
                              <>
                                Revoke <span className="font-mono text-foreground">{p.field}</span>
                                {p.old_value && <span>: {p.old_value}</span>}
                              </>
                            )}
                          </div>
                        </div>
                        {p.status !== "pending" && (
                          <span className={`text-xs font-medium px-2 py-1 rounded-full shrink-0 ${
                            p.status === "approved" ? "bg-green-500/10 text-green-500" : "bg-accent text-muted-foreground"
                          }`}>
                            {p.status}
                          </span>
                        )}
                      </button>

                      {/* Expanded details */}
                      {isExpanded && (
                        <div className="px-4 pb-4 pt-0 border-t border-border/50 animate-fade-in">
                          <div className="grid grid-cols-2 gap-2 text-xs mt-3">
                            <div><span className="text-muted-foreground">Source:</span> <span className="font-medium">{p.source || "System"}</span></div>
                            <div><span className="text-muted-foreground">Proposed by:</span> <span className="font-medium capitalize">{p.proposed_by}</span></div>
                            <div><span className="text-muted-foreground">Proposal source:</span> <span className="capitalize">{p.proposal_source}</span></div>
                            <div><span className="text-muted-foreground">Stake level:</span> <span className={`font-medium capitalize ${
                              p.stake_level === "high" ? "text-red-400" : p.stake_level === "medium" ? "text-amber-500" : "text-green-500"
                            }`}>{p.stake_level}</span></div>
                            <div><span className="text-muted-foreground">Submitted:</span> {p.created_at.slice(0, 10)}</div>
                            {p.reviewed_by && (
                              <div><span className="text-muted-foreground">Reviewed by:</span> {p.reviewed_by} on {p.reviewed_at?.slice(0, 10)}</div>
                            )}
                          </div>

                          {p.reason && (
                            <div className="mt-3 p-2.5 rounded-lg bg-accent/30 text-xs text-muted-foreground">
                              <span className="font-medium text-foreground">Evidence: </span>{p.reason}
                            </div>
                          )}

                          {p.review_note && (
                            <div className="mt-2 p-2.5 rounded-lg bg-blue-500/10 text-xs text-blue-400">
                              <span className="font-medium">Review note: </span>{p.review_note}
                            </div>
                          )}

                          {p.status === "pending" && (
                            <div className="flex items-center gap-2 mt-4 pt-3 border-t border-border/50">
                              <span className="text-[10px] text-muted-foreground/40 flex-1">
                                Approving will add this fact to the company canon. Rejecting will discard it.
                              </span>
                              <button
                                onClick={() => handleResolveProposal(p.id, "approve")}
                                disabled={resolving === p.id}
                                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-green-600 text-white text-xs font-medium hover:bg-green-700 disabled:opacity-50"
                              >
                                {resolving === p.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                                Approve
                              </button>
                              <button
                                onClick={() => handleResolveProposal(p.id, "reject")}
                                disabled={resolving === p.id}
                                className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border text-xs font-medium hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                              >
                                <X className="h-3 w-3" /> Reject
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-20 space-y-4">
                  <FileCheck className="h-10 w-10 text-muted-foreground/20 mx-auto" />
                  <div>
                    <h3 className="font-medium">No proposals</h3>
                    <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
                      Proposals appear when data is ingested from your connected sources.
                      The system auto-detects companies, contacts, and deals worth promoting
                      to company-wide knowledge. Every change must be approved before it enters the canon.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* SoR tab */}
          {tab === "sor" && (
            <div className="space-y-2">
              {sorList.length > 0 ? (
                sorList.map((s) => (
                  <div key={s.id} className="flex items-center justify-between p-4 rounded-xl border border-border bg-card group">
                    <div>
                      <div className="text-sm">
                        For <span className="font-medium capitalize">{s.entity_type}</span> . <span className="font-mono text-xs">{s.field}</span>
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        Authoritative source: <span className="font-medium text-blue-400">{s.authoritative_source}</span>
                        {s.reason && <span className="ml-2 italic">({s.reason})</span>}
                      </div>
                      <div className="text-[10px] text-muted-foreground/40 mt-0.5">
                        Declared by {s.declared_by} on {s.created_at.slice(0, 10)}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteSoR(s.id)}
                      className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-destructive/10 text-destructive transition-all"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))
              ) : (
                <div className="text-center py-20 space-y-4">
                  <Database className="h-10 w-10 text-muted-foreground/20 mx-auto" />
                  <div>
                    <h3 className="font-medium">No SoR declarations</h3>
                    <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
                      Declare which source is the system of record for each data field.
                      This tells Optimus which source wins when two disagree.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
