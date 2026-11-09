import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Boxes, Plus, Search, Settings2 } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { discoverApps } from "../api";
import { AppCard } from "../components/AppCard";
import { NewAppModal } from "../components/NewAppModal";

export function AppZooPage() {
  const { activeWorkspace } = useAuth();
  const workspaceId = activeWorkspace?.id;

  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [visibilityFilter, setVisibilityFilter] = useState("");
  const [page, setPage] = useState(1);
  const [isRegisterModalOpen, setIsRegisterModalOpen] = useState(false);

  const appsQuery = useQuery({
    queryKey: ["zoo-apps", searchTerm, categoryFilter, visibilityFilter, page],
    queryFn: () =>
      discoverApps({
        query: searchTerm || undefined,
        category: categoryFilter || undefined,
        visibility: visibilityFilter || undefined,
        page,
        page_size: 12,
      }),
  });

  const data = appsQuery.data;
  const items = data?.items || [];
  const totalPages = data?.total_pages || 1;

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6 sm:p-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Boxes className="w-6 h-6 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight text-foreground">App Zoo</h1>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Declarative enterprise AI application configurations, tools, and pipelines bound to approved model releases.
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
                onClick={() => setIsRegisterModalOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Register App</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 bg-card p-4 rounded-lg border shadow-sm">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search applications, capabilities..."
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
            <option value="CUSTOMER_SUPPORT">Customer Support</option>
            <option value="LEGAL_ANALYSIS">Legal & Contracts</option>
            <option value="INTERNAL_SEARCH">Internal Search / RAG</option>
            <option value="DEVELOPER_TOOLS">Developer Tools</option>
            <option value="OPERATIONS">Operations</option>
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
            <option value="ORGANIZATION">Organization</option>
            <option value="WORKSPACE">Workspace</option>
            <option value="PUBLIC">Public</option>
          </select>
        </div>
      </div>

      {/* Grid of Apps */}
      {appsQuery.isLoading ? (
        <div className="p-12 text-center text-xs text-muted-foreground">Loading App Zoo listings...</div>
      ) : appsQuery.isError ? (
        <div className="p-8 text-center text-xs text-destructive border rounded-lg bg-destructive/5">
          Failed to load App Zoo. Please try again.
        </div>
      ) : items.length === 0 ? (
        <div className="p-12 text-center rounded-lg border border-dashed bg-muted/20">
          <Boxes className="w-10 h-10 mx-auto text-muted-foreground/60 mb-2" />
          <h3 className="text-sm font-semibold text-foreground">No applications found</h3>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
            Register a new application package bound to your approved model releases.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((listing) => (
            <AppCard key={listing.id} listing={listing} />
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

      {/* Register App Modal */}
      {workspaceId && (
        <NewAppModal
          workspaceId={workspaceId}
          isOpen={isRegisterModalOpen}
          onClose={() => setIsRegisterModalOpen(false)}
          onSuccess={() => appsQuery.refetch()}
        />
      )}
    </div>
  );
}
