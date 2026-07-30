import { useState, useEffect } from "react";
import {
  Search,
  Network,
  User,
  Building2,
  FileText,
  Mail,
  Ticket,
  DollarSign,
  FileSpreadsheet,
  Loader2,
  RefreshCw,
  X,
  ExternalLink,
  Copy,
  Check,
  ChevronRight,
  Clock,
  Tag,
  Link2,
} from "lucide-react";
import { api } from "../../api/client";

interface EntitySummary {
  entity_id: string;
  name: string;
  type: string;
  source_count: number;
  sources: string[];
  last_updated: string;
  properties?: Record<string, any>;
}

interface EntityGraph {
  entities: EntitySummary[];
  total: number;
  connected_sources: number;
}

const TYPE_ICONS: Record<string, typeof User> = {
  person: User,
  company: Building2,
  document: FileText,
  email: Mail,
  ticket: Ticket,
  deal: DollarSign,
  spreadsheet: FileSpreadsheet,
};

const TYPE_COLORS: Record<string, string> = {
  person: "text-blue-400 bg-blue-500/10",
  company: "text-purple-400 bg-purple-500/10",
  document: "text-amber-400 bg-amber-500/10",
  email: "text-green-400 bg-green-500/10",
  ticket: "text-red-400 bg-red-500/10",
  deal: "text-emerald-400 bg-emerald-500/10",
  spreadsheet: "text-teal-400 bg-teal-500/10",
};

const TYPE_FILTERS = [
  { value: "", label: "All" },
  { value: "person", label: "People" },
  { value: "company", label: "Companies" },
  { value: "deal", label: "Deals" },
  { value: "document", label: "Documents" },
  { value: "email", label: "Emails" },
  { value: "ticket", label: "Tickets" },
  { value: "spreadsheet", label: "Sheets" },
];

const PROP_LABELS: Record<string, string> = {
  from: "From",
  to: "To",
  cc: "CC",
  date: "Date",
  snippet: "Preview",
  labels: "Labels",
  email: "Email",
  company: "Company",
  phone: "Phone",
  job_title: "Job Title",
  domain: "Domain",
  contact_count: "Contacts",
  industry: "Industry",
  employees: "Employees",
  city: "City",
  state: "State",
  amount: "Amount",
  stage: "Stage",
  close_date: "Close Date",
  pipeline: "Pipeline",
  mime_type: "File Type",
  modified: "Modified",
  owner: "Owner",
  size: "Size",
  link: "Link",
  parsed: "Parsed",
  parsed_content: "Content",
};

function PropertyValue({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);

  if (!value || value === "undefined" || value === "null") return null;

  const isLink =
    value.startsWith("http://") || value.startsWith("https://");
  const isEmail = value.includes("@") && !value.includes(" ") && label !== "Labels";

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="group flex items-start gap-3 py-2.5 px-3 rounded-lg hover:bg-accent/30 transition-all">
      <div className="w-28 shrink-0 text-[11px] text-muted-foreground font-medium uppercase tracking-wider pt-0.5">
        {label}
      </div>
      <div className="flex-1 min-w-0 text-sm break-words">
        {isLink ? (
          <a
            href={value}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline inline-flex items-center gap-1"
          >
            {value.length > 60 ? value.slice(0, 60) + "..." : value}
            <ExternalLink className="h-3 w-3 shrink-0" />
          </a>
        ) : isEmail ? (
          <a
            href={`mailto:${value}`}
            className="text-primary hover:underline"
          >
            {value}
          </a>
        ) : label === "Content" || label === "Preview" ? (
          <div className="text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap max-h-40 overflow-auto">
            {value.slice(0, 1000)}
          </div>
        ) : (
          <span>{value.length > 200 ? value.slice(0, 200) + "..." : value}</span>
        )}
      </div>
      <button
        onClick={handleCopy}
        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-accent transition-all shrink-0"
        title="Copy value"
      >
        {copied ? (
          <Check className="h-3 w-3 text-green-500" />
        ) : (
          <Copy className="h-3 w-3 text-muted-foreground" />
        )}
      </button>
    </div>
  );
}

function EntityDetailPanel({
  entity,
  onClose,
  allEntities,
  onNavigate,
}: {
  entity: EntitySummary;
  onClose: () => void;
  allEntities: EntitySummary[];
  onNavigate: (e: EntitySummary) => void;
}) {
  const Icon = TYPE_ICONS[entity.type] || FileText;
  const colorClass = TYPE_COLORS[entity.type] || "text-gray-400 bg-gray-500/10";
  const props = entity.properties || {};

  // Find related entities using multiple signals
  const entityName = entity.name.toLowerCase();
  const entityDomain = (entity.properties?.domain || "").toLowerCase();
  const entityEmail = (entity.properties?.email || "").toLowerCase();
  const entityCompany = (entity.properties?.company || "").toLowerCase();

  const related = allEntities.filter((e) => {
    if (e.entity_id === entity.entity_id) return false;
    const eName = e.name.toLowerCase();
    const eProps = e.properties || {};

    // Person <-> Email: person mentioned in email from/to
    if (entity.type === "person" && e.type === "email") {
      const from = (eProps.from || "").toLowerCase();
      const to = (eProps.to || "").toLowerCase();
      if (entityEmail && (from.includes(entityEmail) || to.includes(entityEmail))) return true;
      if (entityName.length > 3 && (from.includes(entityName) || to.includes(entityName))) return true;
    }
    if (entity.type === "email" && e.type === "person") {
      const from = (props.from || "").toLowerCase();
      const to = (props.to || "").toLowerCase();
      const pEmail = (eProps.email || "").toLowerCase();
      if (pEmail && (from.includes(pEmail) || to.includes(pEmail))) return true;
    }

    // Company <-> Person: person works at company (by domain or company field)
    if (entity.type === "company" && e.type === "person") {
      const pEmail = (eProps.email || "").toLowerCase();
      const pCompany = (eProps.company || "").toLowerCase();
      if (entityDomain && pEmail.includes(entityDomain)) return true;
      if (entityName.length > 2 && pCompany.includes(entityName)) return true;
    }
    if (entity.type === "person" && e.type === "company") {
      const cDomain = (eProps.domain || "").toLowerCase();
      if (cDomain && entityEmail.includes(cDomain)) return true;
      if (entityCompany && eName.includes(entityCompany)) return true;
    }

    // Company <-> Deal: deal belongs to company (by name overlap)
    if (entity.type === "company" && e.type === "deal") {
      if (entityName.length > 2 && eName.includes(entityName)) return true;
    }
    if (entity.type === "deal" && e.type === "company") {
      if (eName.length > 2 && entityName.includes(eName)) return true;
    }

    // Same name across different sources (cross-source match)
    if (e.type === entity.type && eName === entityName && !e.sources.every((s) => entity.sources.includes(s))) {
      return true;
    }

    return false;
  }).slice(0, 10);

  // Organize properties into sections
  const primaryProps: [string, string][] = [];
  const metaProps: [string, string][] = [];
  const contentProps: [string, string][] = [];

  const primaryKeys = new Set([
    "from", "to", "cc", "email", "company", "phone", "job_title",
    "domain", "contact_count", "industry", "employees",
    "amount", "stage", "close_date", "pipeline",
  ]);
  const contentKeys = new Set(["snippet", "parsed_content"]);
  const skipKeys = new Set(["id", "_id"]);

  for (const [key, val] of Object.entries(props)) {
    if (skipKeys.has(key) || key.startsWith("_")) continue;
    const strVal = typeof val === "object" ? JSON.stringify(val) : String(val);
    if (!strVal || strVal === "undefined" || strVal === "null" || strVal === "") continue;

    if (contentKeys.has(key)) {
      contentProps.push([PROP_LABELS[key] || key, strVal]);
    } else if (primaryKeys.has(key)) {
      primaryProps.push([PROP_LABELS[key] || key, strVal]);
    } else {
      metaProps.push([PROP_LABELS[key] || key, strVal]);
    }
  }

  return (
    <div className="fixed inset-y-0 right-0 w-[480px] bg-[#0d1117] border-l border-border shadow-2xl z-50 flex flex-col animate-slide-in-right">
      {/* Header */}
      <div className="p-5 border-b border-border bg-[#0d1117]">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 min-w-0">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${colorClass}`}>
              <Icon className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <h2 className="text-lg font-semibold truncate leading-tight">
                {entity.name}
              </h2>
              <div className="flex items-center gap-2 mt-1">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full capitalize ${colorClass}`}>
                  {entity.type}
                </span>
                <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                  <Link2 className="h-2.5 w-2.5" />
                  {entity.sources.join(", ")}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-accent transition-all shrink-0"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-auto">
        {/* Primary properties */}
        {primaryProps.length > 0 && (
          <div className="p-4 border-b border-border/50">
            <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-3">
              Details
            </h3>
            <div className="space-y-0">
              {primaryProps.map(([label, value]) => (
                <PropertyValue key={label} label={label} value={value} />
              ))}
            </div>
          </div>
        )}

        {/* Meta properties */}
        {metaProps.length > 0 && (
          <div className="p-4 border-b border-border/50">
            <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-3">
              Metadata
            </h3>
            <div className="space-y-0">
              {metaProps.map(([label, value]) => (
                <PropertyValue key={label} label={label} value={value} />
              ))}
            </div>
          </div>
        )}

        {/* Content section */}
        {contentProps.length > 0 && (
          <div className="p-4 border-b border-border/50">
            <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-3">
              Content
            </h3>
            <div className="space-y-0">
              {contentProps.map(([label, value]) => (
                <PropertyValue key={label} label={label} value={value} />
              ))}
            </div>
          </div>
        )}

        {/* Source info */}
        <div className="p-4 border-b border-border/50">
          <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-3">
            Source
          </h3>
          <div className="space-y-0">
            <PropertyValue label="Source" value={entity.sources.join(", ")} />
            <PropertyValue
              label="Last updated"
              value={entity.last_updated.slice(0, 19).replace("T", " ")}
            />
            <PropertyValue label="Entity ID" value={entity.entity_id} />
          </div>
        </div>

        {/* Related entities */}
        {related.length > 0 && (
          <div className="p-4">
            <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-3">
              Related ({related.length})
            </h3>
            <div className="space-y-1">
              {related.map((r) => {
                const RIcon = TYPE_ICONS[r.type] || FileText;
                const rColor = TYPE_COLORS[r.type] || "text-gray-400 bg-gray-500/10";
                return (
                  <button
                    key={r.entity_id}
                    onClick={() => onNavigate(r)}
                    className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-accent/50 text-left transition-all group"
                  >
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${rColor}`}>
                      <RIcon className="h-3.5 w-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium truncate">{r.name}</div>
                      <div className="text-[10px] text-muted-foreground">{r.type}</div>
                    </div>
                    <ChevronRight className="h-3 w-3 text-muted-foreground/30 group-hover:text-muted-foreground transition-all" />
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Empty state if no props at all */}
        {primaryProps.length === 0 && metaProps.length === 0 && contentProps.length === 0 && (
          <div className="p-8 text-center">
            <Tag className="h-8 w-8 text-muted-foreground/20 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              No additional properties available for this entity.
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-border flex items-center justify-between text-[10px] text-muted-foreground/40">
        <span className="flex items-center gap-1">
          <Clock className="h-2.5 w-2.5" />
          Fetched {entity.last_updated.slice(0, 10)}
        </span>
        <span>{entity.type} / {entity.sources.join(", ")}</span>
      </div>
    </div>
  );
}

export function BrowseSurface() {
  const [data, setData] = useState<EntityGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [selectedEntity, setSelectedEntity] = useState<EntitySummary | null>(null);

  const fetchEntities = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {
        viewer_id: "00000000-0000-0000-0000-000000000001",
      };
      if (typeFilter) params.entity_type = typeFilter;
      if (search) params.search = search;

      const resp = await api.get<EntityGraph>("/api/v1/browse/entities", {
        params,
      });
      setData(resp.data);
    } catch {
      setData({ entities: [], total: 0, connected_sources: 0 });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntities();
  }, [typeFilter]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchEntities();
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Close detail panel on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelectedEntity(null);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  return (
    <div className="h-full relative">
    <div className="space-y-6 p-6 h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Network className="h-6 w-6 text-primary" />
            Entity Graph
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {data
              ? `${data.total} entities from ${data.connected_sources} source${data.connected_sources !== 1 ? "s" : ""}`
              : "Loading..."}
          </p>
        </div>
        <button
          onClick={fetchEntities}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border text-sm hover:bg-accent transition-all"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Search + filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search entities..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
          />
        </div>
        <div className="flex items-center gap-1">
          {TYPE_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setTypeFilter(f.value)}
              className={`px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                typeFilter === f.value
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : data && data.entities.length > 0 ? (
        <div className="grid gap-2">
          {data.entities.map((entity) => {
            const Icon = TYPE_ICONS[entity.type] || FileText;
            const colorClass =
              TYPE_COLORS[entity.type] || "text-gray-500 bg-gray-50";
            const isSelected = selectedEntity?.entity_id === entity.entity_id;

            return (
              <button
                key={entity.entity_id}
                onClick={() => setSelectedEntity(isSelected ? null : entity)}
                className={`w-full flex items-center gap-4 p-4 rounded-xl border text-left transition-all ${
                  isSelected
                    ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                    : "border-border hover:border-primary/30 hover:bg-accent/50"
                }`}
              >
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center ${colorClass}`}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm truncate">
                    {entity.name}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    {entity.type} · {entity.sources.join(", ")} ·{" "}
                    {entity.source_count} source
                    {entity.source_count !== 1 ? "s" : ""}
                  </div>
                </div>
                <ChevronRight
                  className={`h-4 w-4 text-muted-foreground/30 transition-transform ${
                    isSelected ? "rotate-90 text-primary" : ""
                  }`}
                />
                <div className="text-xs text-muted-foreground">
                  {entity.last_updated.slice(0, 10)}
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-20 space-y-4">
          <Network className="h-12 w-12 text-muted-foreground/30 mx-auto" />
          <div>
            <h3 className="font-medium">No entities yet</h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
              Connect your data sources and run ingestion through the{" "}
              <a href="/onboarding" className="text-primary underline">
                Onboarding flow
              </a>{" "}
              to populate your knowledge graph.
            </p>
          </div>
        </div>
      )}

    </div>

      {/* Detail Panel (slide-out) — outside overflow container */}
      {selectedEntity && (
        <>
          <div
            className="fixed inset-0 bg-black/40 z-40 backdrop-blur-sm"
            onClick={() => setSelectedEntity(null)}
          />
          <EntityDetailPanel
            entity={selectedEntity}
            onClose={() => setSelectedEntity(null)}
            allEntities={data?.entities || []}
            onNavigate={(e) => setSelectedEntity(e)}
          />
        </>
      )}
    </div>
  );
}
