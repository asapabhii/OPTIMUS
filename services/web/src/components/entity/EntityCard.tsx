import { Link } from "react-router-dom";
import { AlertTriangle, ExternalLink, Clock } from "lucide-react";

interface EntitySummary {
  id: string;
  canonical_name: string;
  entity_type: string;
  source_count: number;
  belief_count: number;
  has_conflicts: boolean;
  last_refreshed: string | null;
}

const entityTypeConfig: Record<
  string,
  { label: string; color: string }
> = {
  customer: { label: "Customer", color: "bg-blue-500/10 text-blue-500" },
  person: { label: "Person", color: "bg-green-500/10 text-green-500" },
  product_sku: { label: "Product", color: "bg-purple-500/10 text-purple-500" },
  deal: { label: "Deal", color: "bg-amber-500/10 text-amber-500" },
  project: { label: "Project", color: "bg-pink-500/10 text-pink-500" },
};

export function EntityCard({ entity }: { entity: EntitySummary }) {
  const typeConfig = entityTypeConfig[entity.entity_type] ?? {
    label: entity.entity_type,
    color: "bg-gray-500/10 text-gray-500",
  };

  return (
    <Link
      to={`/browse/${entity.id}`}
      className="block border border-border rounded-lg p-4 hover:border-foreground/20 transition-colors group"
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <h3 className="font-medium text-sm group-hover:text-primary transition-colors">
            {entity.canonical_name}
          </h3>
          <span
            className={`inline-flex text-[10px] font-medium px-1.5 py-0.5 rounded ${typeConfig.color}`}
          >
            {typeConfig.label}
          </span>
        </div>
        {entity.has_conflicts && (
          <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
        )}
      </div>

      <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <ExternalLink className="h-3 w-3" />
          {entity.source_count} sources
        </span>
        <span>{entity.belief_count} beliefs</span>
        {entity.last_refreshed && (
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {entity.last_refreshed}
          </span>
        )}
      </div>
    </Link>
  );
}
