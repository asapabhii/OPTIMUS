import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { Network, Search, Filter } from "lucide-react";
import { api } from "../../api/client";
import { EntityCard } from "../../components/entity/EntityCard";
import { useState } from "react";

interface EntitySummary {
  id: string;
  canonical_name: string;
  entity_type: string;
  source_count: number;
  belief_count: number;
  has_conflicts: boolean;
  last_refreshed: string | null;
}

interface GraphView {
  entities: EntitySummary[];
  total_count: number;
  total_sources: number;
  total_beliefs: number;
  total_conflicts: number;
}

export function BrowseSurface() {
  const { entityId } = useParams();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string | null>(null);

  const graphQuery = useQuery({
    queryKey: ["graph", typeFilter],
    queryFn: async () => {
      const params = new URLSearchParams({
        viewer_id: "00000000-0000-0000-0000-000000000001",
      });
      if (typeFilter) params.set("entity_type", typeFilter);
      const response = await api.get<GraphView>(
        `/api/v1/browse/graph?${params}`
      );
      return response.data;
    },
  });

  const graph = graphQuery.data;

  return (
    <div className="flex flex-col h-full">
      {/* Header with stats */}
      <div className="border-b border-border px-8 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Network className="h-5 w-5" />
              Browse
            </h2>
            <p className="text-sm text-muted-foreground">
              Entity graph with sources, beliefs, and freshness
            </p>
          </div>
          {graph && (
            <div className="flex gap-6 text-sm">
              <div className="text-center">
                <div className="font-semibold text-foreground">
                  {graph.total_count}
                </div>
                <div className="text-muted-foreground">Entities</div>
              </div>
              <div className="text-center">
                <div className="font-semibold text-foreground">
                  {graph.total_sources}
                </div>
                <div className="text-muted-foreground">Sources</div>
              </div>
              <div className="text-center">
                <div className="font-semibold text-foreground">
                  {graph.total_conflicts}
                </div>
                <div className="text-muted-foreground">Conflicts</div>
              </div>
            </div>
          )}
        </div>

        {/* Search and filter */}
        <div className="flex gap-3 mt-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search entities..."
              className="w-full pl-10 pr-4 py-2 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div className="flex gap-2">
            {["customer", "person", "product_sku", "deal", "project"].map(
              (type) => (
                <button
                  key={type}
                  onClick={() =>
                    setTypeFilter(typeFilter === type ? null : type)
                  }
                  className={`px-3 py-1.5 text-xs rounded-full border transition-colors ${
                    typeFilter === type
                      ? "bg-primary text-primary-foreground border-primary"
                      : "border-border text-muted-foreground hover:bg-accent"
                  }`}
                >
                  {type.replace("_", " ")}
                </button>
              )
            )}
          </div>
        </div>
      </div>

      {/* Entity grid */}
      <div className="flex-1 overflow-auto px-8 py-6">
        {graphQuery.isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-muted-foreground">Loading entities...</div>
          </div>
        ) : graph && graph.entities.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {graph.entities
              .filter(
                (e) =>
                  !search ||
                  e.canonical_name
                    .toLowerCase()
                    .includes(search.toLowerCase())
              )
              .map((entity) => (
                <EntityCard key={entity.id} entity={entity} />
              ))}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-3">
              <Network className="h-12 w-12 text-muted-foreground mx-auto" />
              <h3 className="text-lg font-medium text-muted-foreground">
                No entities yet
              </h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Connect your tools and the entity graph will build
                automatically.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
