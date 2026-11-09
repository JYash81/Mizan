import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  PackageCheck,
  Plus,
  Search,
  Settings2,
} from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { discoverModels } from "../api";
import { ModelCard } from "../components/ModelCard";
import { NewModelListingModal } from "../components/NewModelListingModal";

export function ModelZooPage() {
  const { activeWorkspace } = useAuth();
  const workspaceId = activeWorkspace?.id;

  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [badgeFilter, setBadgeFilter] = useState<string>("");
  const [visibilityFilter, setVisibilityFilter] = useState("");
  const [page, setPage] = useState(1);
  const [isPublishModalOpen, setIsPublishModalOpen] = useState(false);

  const modelsQuery = useQuery({
    queryKey: ["zoo-models", searchTerm, categoryFilter, badgeFilter, visibilityFilter, page],
    queryFn: () =>
      discoverModels({
        query: searchTerm || undefined,
        category: categoryFilter || undefined,
        hardware_badge: badgeFilter || undefined,
        visibility: visibilityFilter || undefined,
        page,
        page_size: 12,
      }),
  });

  const data = modelsQuery.data;
  const items = data?.items || [];
  const totalPages = data?.total_pages || 1;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <PackageCheck className="w-6 h-6 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Model Zoo</h1>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Enterprise catalog of approved, cryptographically attested AI model releases and adapters.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {workspaceId && (
            <>
              <Link
                to={`/workspaces/${workspaceId}/zoo/manage`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md border bg-background hover:bg-muted text-foreground transition-colors shadow-sm"
              >
                <Settings2 className="w-3.5 h-3.5" />
                <span>Catalog Publisher Hub</span>
              </Link>

              <button
                type="button"
                onClick={() => setIsPublishModalOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Publish Release</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 bg-card p-4 rounded-lg border shadow-sm">
        <div className="relative md:col-span-1">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search models, tags, architecture..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(1);
            }}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-md border bg-background text-foreground"
          />
        </div>

        <div>
          <select
            value={categoryFilter}
            onChange={(e) => {
              setCategoryFilter(e.target.value);
              setPage(1);
            }}
            className="w-full px-3 py-1.5 text-xs rounded-md border bg-background text-foreground"
          >
            <option value="">All Categories</option>
            <option value="TEXT_GENERATION">Text Generation</option>
            <option value="CUSTOMER_SUPPORT">Customer Support</option>
            <option value="CODE_GENERATION">Code Generation</option>
            <option value="RAG_EMBEDDINGS">RAG & Embeddings</option>
            <option value="CLASSIFICATION">Classification</option>
            <option value="REASONING">Reasoning</option>
          </select>
        </div>

        <div>
          <select
            value={badgeFilter}
            onChange={(e) => {
              setBadgeFilter(e.target.value);
              setPage(1);
            }}
            className="w-full px-3 py-1.5 text-xs rounded-md border bg-background text-foreground"
          >
            <option value="">All Hardware Badges</option>
            <option value="TESTED">TESTED (Measured physical benchmark)</option>
            <option value="ESTIMATED">ESTIMATED (M8 calculated)</option>
            <option value="INCOMPATIBLE">INCOMPATIBLE</option>
            <option value="UNKNOWN">UNKNOWN</option>
          </select>
        </div>

        <div>
          <select
            value={visibilityFilter}
            onChange={(e) => {
              setVisibilityFilter(e.target.value);
              setPage(1);
            }}
            className="w-full px-3 py-1.5 text-xs rounded-md border bg-background text-foreground"
          >
            <option value="">All Visibilities</option>
            <option value="PUBLIC">Public</option>
            <option value="ORGANIZATION">Organization</option>
            <option value="WORKSPACE">Workspace</option>
          </select>
        </div>
      </div>

      {/* Grid of Models */}
      {modelsQuery.isLoading ? (
        <div className="p-12 text-center text-xs text-muted-foreground">
          Loading Model Zoo listings...
        </div>
      ) : modelsQuery.isError ? (
        <div className="p-8 text-center text-xs text-destructive border rounded-lg bg-destructive/5">
          Failed to load Model Zoo. Please try again.
        </div>
      ) : items.length === 0 ? (
        <div className="p-12 text-center rounded-lg border border-dashed bg-muted/20">
          <PackageCheck className="w-10 h-10 mx-auto text-muted-foreground/60 mb-2" />
          <h3 className="text-sm font-semibold text-foreground">No model releases found</h3>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
            Try adjusting your search filters or publish an approved Gate 3 release from your workspace.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((listing) => (
            <ModelCard key={listing.id} listing={listing} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t pt-4 text-xs text-muted-foreground">
          <div>
            Showing page {page} of {totalPages}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="px-3 py-1 rounded border bg-background hover:bg-muted disabled:opacity-50"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              className="px-3 py-1 rounded border bg-background hover:bg-muted disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* New Listing Modal */}
      {workspaceId && (
        <NewModelListingModal
          workspaceId={workspaceId}
          isOpen={isPublishModalOpen}
          onClose={() => setIsPublishModalOpen(false)}
          onSuccess={() => modelsQuery.refetch()}
        />
      )}
    </div>
  );
}
