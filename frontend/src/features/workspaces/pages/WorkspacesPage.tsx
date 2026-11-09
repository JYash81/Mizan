import { useState, useEffect, type FormEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  FolderKanban,
  Plus,
  Search,
  CheckCircle2,
  ArrowRight,
  Database,
  FlaskConical,
  Award,
  Shield,
  X,
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import { apiGet, apiPost, ApiError } from "../../../lib/api/client";
import type { WorkspaceSummary } from "../../auth/types";

export function WorkspacesPage() {
  const { activeOrganization, activeWorkspace, switchWorkspace, workspaces: authWorkspaces } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [isSlugManual, setIsSlugManual] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const orgId = activeOrganization?.id;

  useEffect(() => {
    if (!isSlugManual && name) {
      const generated = name
        .toLowerCase()
        .replace(/[^\w\s-]/g, "")
        .replace(/[\s_-]+/g, "-")
        .replace(/^-+|-+$/g, "");
      setSlug(generated);
    }
  }, [name, isSlugManual]);

  const { data: workspaces = authWorkspaces, isLoading } = useQuery<WorkspaceSummary[]>({
    queryKey: ["org-workspaces", orgId],
    queryFn: () => apiGet<WorkspaceSummary[]>(`/organizations/${orgId}/workspaces`),
    enabled: !!orgId,
  });

  const createMutation = useMutation({
    mutationFn: (payload: { name: string; slug?: string; description?: string }) =>
      apiPost<WorkspaceSummary>(`/organizations/${orgId}/workspaces`, payload),
    onSuccess: (newWs) => {
      queryClient.invalidateQueries({ queryKey: ["org-workspaces", orgId] });
      setShowCreateModal(false);
      setName("");
      setSlug("");
      setDescription("");
      setIsSlugManual(false);
      setFormError(null);
      if (newWs?.id) {
        switchWorkspace(newWs.id);
      }
    },
    onError: (err: unknown) => {
      setFormError(err instanceof ApiError ? err.message : "Failed to create workspace");
    },
  });

  const handleCreateSubmit = (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!name.trim()) {
      setFormError("Workspace name is required.");
      return;
    }
    createMutation.mutate({
      name: name.trim(),
      slug: slug.trim() || undefined,
      description: description.trim() || undefined,
    });
  };

  const filteredWorkspaces = workspaces.filter(
    (w) =>
      w.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      w.slug.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (w.description && w.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6 sm:p-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <Shield className="w-3.5 h-3.5" />
              {activeOrganization?.name ?? "ORGANIZATION"}
            </span>
            <span className="text-xs text-muted-foreground">Governance Boundaries</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <FolderKanban className="w-6 h-6 text-emerald-600" />
            Organization Workspaces
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
            Isolate datasets, model experiments, and cryptographic release approvals into dedicated security environments.
          </p>
        </div>

        <button
          onClick={() => {
            setShowCreateModal(true);
            setFormError(null);
          }}
          className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2.5 rounded-lg font-medium text-sm transition-all shadow-sm self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>New Workspace</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-card border border-border p-4 rounded-xl shadow-sm">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search workspaces by name or slug..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg bg-background border border-input text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 transition"
          />
        </div>
        <span className="text-xs text-muted-foreground font-medium self-end sm:self-center">
          Showing {filteredWorkspaces.length} of {workspaces.length} environments
        </span>
      </div>

      {/* Workspace Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-card border border-border rounded-xl p-6 space-y-4 animate-pulse">
              <div className="h-4 bg-muted rounded w-1/3" />
              <div className="h-6 bg-muted rounded w-3/4" />
              <div className="h-12 bg-muted rounded w-full" />
              <div className="h-8 bg-muted rounded w-full" />
            </div>
          ))}
        </div>
      ) : filteredWorkspaces.length === 0 ? (
        <div className="bg-card border border-border rounded-xl p-12 text-center space-y-4 shadow-sm">
          <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
            <FolderKanban className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-foreground">No Workspaces Found</h3>
          <p className="text-sm text-muted-foreground max-w-sm mx-auto">
            {searchQuery
              ? "No workspaces match your search criteria. Try a different query."
              : "Create your first workspace to isolate experiments, datasets, and hardware approvals."}
          </p>
          {!searchQuery && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg font-medium text-xs transition"
            >
              <Plus className="w-4 h-4" />
              Create First Workspace
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredWorkspaces.map((ws) => {
            const isActive = activeWorkspace?.id === ws.id;
            return (
              <div
                key={ws.id}
                className={`bg-card border rounded-xl p-5 flex flex-col justify-between transition-all shadow-sm ${
                  isActive
                    ? "border-emerald-500 ring-2 ring-emerald-500/20 shadow-md"
                    : "border-border hover:border-emerald-300"
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-mono text-xs text-muted-foreground bg-muted/60 px-2 py-0.5 rounded">
                      {ws.slug}
                    </span>
                    {isActive ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <CheckCircle2 className="w-3 h-3" /> ACTIVE
                      </span>
                    ) : (
                      <span className="text-[11px] font-medium text-muted-foreground">
                        {ws.status || "READY"}
                      </span>
                    )}
                  </div>

                  <h3 className="text-base font-bold text-foreground mt-3 flex items-center gap-2">
                    {ws.name}
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2 min-h-[32px]">
                    {ws.description || "No description provided."}
                  </p>

                  {/* Quick links to features */}
                  <div className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-border/60 text-xs">
                    <button
                      onClick={() => {
                        if (!isActive) switchWorkspace(ws.id);
                        navigate("/datasets");
                      }}
                      className="flex items-center gap-1.5 p-2 rounded-lg bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground transition text-[11px]"
                      title="Open Datasets"
                    >
                      <Database className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Data</span>
                    </button>
                    <button
                      onClick={() => {
                        if (!isActive) switchWorkspace(ws.id);
                        navigate("/experiments");
                      }}
                      className="flex items-center gap-1.5 p-2 rounded-lg bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground transition text-[11px]"
                      title="Open Experiments"
                    >
                      <FlaskConical className="w-3.5 h-3.5 text-indigo-600" />
                      <span>Trials</span>
                    </button>
                    <button
                      onClick={() => {
                        if (!isActive) switchWorkspace(ws.id);
                        navigate("/evaluation");
                      }}
                      className="flex items-center gap-1.5 p-2 rounded-lg bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground transition text-[11px]"
                      title="Open Evaluation"
                    >
                      <Award className="w-3.5 h-3.5 text-amber-600" />
                      <span>Eval</span>
                    </button>
                  </div>
                </div>

                <div className="mt-5 pt-3 border-t border-border/60 flex items-center justify-between">
                  <span className="text-[11px] text-muted-foreground">
                    Role: <strong className="text-foreground">{ws.role || "MEMBER"}</strong>
                  </span>

                  {isActive ? (
                    <span className="text-xs font-semibold text-emerald-700 flex items-center gap-1">
                      Current <CheckCircle2 className="w-3.5 h-3.5" />
                    </span>
                  ) : (
                    <button
                      onClick={() => switchWorkspace(ws.id)}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 hover:text-emerald-700 transition"
                    >
                      Switch to Workspace <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Workspace Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl p-6 sm:p-8 max-w-md w-full shadow-2xl space-y-6">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
                  <FolderKanban className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-bold text-foreground">Create Workspace</h3>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-lg hover:bg-muted transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded-lg">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-foreground font-semibold mb-1">
                  Workspace Name <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Risk Analytics & Forecasting"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-input text-foreground text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 transition"
                />
              </div>

              <div>
                <label className="block text-foreground font-semibold mb-1">
                  Identifier Slug
                </label>
                <input
                  type="text"
                  placeholder="e.g. risk-analytics"
                  value={slug}
                  onChange={(e) => {
                    setIsSlugManual(true);
                    setSlug(e.target.value);
                  }}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-input text-foreground text-xs font-mono placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 transition"
                />
                <p className="text-[11px] text-muted-foreground mt-1">
                  Unique URL path component. Letters, numbers, and dashes only.
                </p>
              </div>

              <div>
                <label className="block text-foreground font-semibold mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  placeholder="State the objective, boundary, or business purpose..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-input text-foreground text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 transition"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-lg border border-border text-foreground hover:bg-muted font-medium transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold transition disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
                >
                  {createMutation.isPending ? "Creating..." : "Create Workspace"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
