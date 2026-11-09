import { useState, useEffect, type FormEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Archive,
  ArrowRight,
  Database,
  FileText,
  HardDrive,
  Layers,
  Plus,
  Search,
  X,
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import { apiGet, apiPost, apiDelete } from "../../../lib/api/client";
import type { Dataset, CreateDatasetPayload } from "../types";

export function DatasetsPage() {
  const { activeWorkspace } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  // Auto-generate slug when name changes if user hasn't typed custom slug
  const [isSlugManual, setIsSlugManual] = useState(false);

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

  const workspaceId = activeWorkspace?.id;

  const { data, isLoading, error } = useQuery<{ datasets: Dataset[] }>({
    queryKey: ["datasets", workspaceId],
    queryFn: () => apiGet<{ datasets: Dataset[] }>(`/workspaces/${workspaceId}/datasets`),
    enabled: !!workspaceId,
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreateDatasetPayload) =>
      apiPost<{ dataset: Dataset }>(`/workspaces/${workspaceId}/datasets`, payload),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["datasets", workspaceId] });
      setShowCreateModal(false);
      setName("");
      setSlug("");
      setDescription("");
      setIsSlugManual(false);
      setFormError(null);
      navigate(`/datasets/${res.dataset.id}`);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to create dataset";
      setFormError(msg);
    },
  });

  const archiveMutation = useMutation({
    mutationFn: (datasetId: string) =>
      apiDelete(`/workspaces/${workspaceId}/datasets/${datasetId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["datasets", workspaceId] });
    },
  });

  const handleCreateSubmit = (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!name.trim()) {
      setFormError("Dataset name is required.");
      return;
    }
    createMutation.mutate({
      name: name.trim(),
      slug: slug.trim() || undefined,
      description: description.trim() || undefined,
    });
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const datasets: Dataset[] = Array.isArray(data)
    ? data
    : Array.isArray((data as any)?.datasets)
    ? (data as any).datasets
    : [];
  const filteredDatasets = datasets.filter(
    (d) =>
      d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.slug.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (d.description && d.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const totalDocuments = datasets.reduce(
    (acc, d) => acc + (d.active_version?.total_documents || 0),
    0
  );
  const totalBytes = datasets.reduce(
    (acc, d) => acc + (d.active_version?.total_raw_bytes || 0),
    0
  );

  return (
    <div className="page-container pb-16">
      <div className="page-header">
        <div>
          <p className="eyebrow">DATA PLANE — WORKSHOP</p>
          <h2>Business Datasets</h2>
          <p>
            Manage knowledge bases, documents, and reference archives for AI experimentation in{" "}
            <strong>{activeWorkspace?.name || "your workspace"}</strong>.
          </p>
        </div>
        <button
          onClick={() => {
            setShowCreateModal(true);
            setFormError(null);
          }}
          className="btn-primary"
        >
          <Plus className="w-4 h-4" />
          <span>New Dataset</span>
        </button>
      </div>

      {/* Overview Stats */}
      <div className="overview-grid mt-6">
        <div className="feature-card">
          <div className="feature-icon">
            <Database className="w-5 h-5" />
          </div>
          <h3>Datasets Container</h3>
          <p className="text-2xl font-bold text-gray-900 mt-1">{datasets.length}</p>
          <span className="planned">Workspace Scope</span>
        </div>

        <div className="feature-card">
          <div className="feature-icon">
            <FileText className="w-5 h-5" />
          </div>
          <h3>Total Documents</h3>
          <p className="text-2xl font-bold text-gray-900 mt-1">{totalDocuments.toLocaleString()}</p>
          <span className="planned">Extracted & Bounded</span>
        </div>

        <div className="feature-card">
          <div className="feature-icon">
            <HardDrive className="w-5 h-5" />
          </div>
          <h3>Raw Storage Footprint</h3>
          <p className="text-2xl font-bold text-gray-900 mt-1">{formatSize(totalBytes)}</p>
          <span className="planned">Sovereign Data Store</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="mt-8 flex justify-between items-center gap-4 bg-white p-4 rounded-lg border border-gray-200">
        <div className="input-icon-wrap flex-1 max-w-md">
          <Search className="input-icon w-4 h-4" />
          <input
            type="text"
            placeholder="Search datasets by name or slug..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field"
          />
        </div>
        <span className="text-xs text-gray-500 font-medium">
          Showing {filteredDatasets.length} of {datasets.length} datasets
        </span>
      </div>

      {/* Dataset Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-xl p-6 space-y-4 animate-pulse shadow-sm">
              <div className="h-4 bg-gray-100 rounded w-1/3" />
              <div className="h-6 bg-gray-100 rounded w-3/4" />
              <div className="h-10 bg-gray-100 rounded w-full" />
              <div className="h-8 bg-gray-100 rounded w-full" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="bg-white border border-rose-200 rounded-xl p-8 text-center space-y-3 mt-6 shadow-sm">
          <div className="w-10 h-10 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center mx-auto">
            <X className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-gray-900">Failed to Load Datasets</h3>
          <p className="text-xs text-gray-600 max-w-md mx-auto">
            {error instanceof Error ? error.message : "Could not retrieve datasets for this workspace. The cloud backend may be waking up."}
          </p>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ["datasets", workspaceId] })}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg transition"
          >
            Retry Request
          </button>
        </div>
      ) : filteredDatasets.length === 0 ? (
        <div className="empty mx-auto mt-8 text-center">
          <div className="feature-icon mx-auto">
            <Database className="w-6 h-6" />
          </div>
          <h2>No Datasets Found</h2>
          <p className="text-sm text-gray-600 max-w-sm mx-auto mt-2">
            {searchQuery
              ? "No datasets match your search criteria. Try a different search term."
              : "Upload and organize business documents to prepare for AI evaluation and masking."}
          </p>
          {!searchQuery && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="btn-primary mx-auto mt-4"
            >
              <Plus className="w-4 h-4" />
              <span>Create First Dataset</span>
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
          {filteredDatasets.map((dataset) => {
            const ver = dataset.active_version;
            return (
              <div
                key={dataset.id}
                className="bg-white border border-gray-200 rounded-lg p-5 flex flex-col justify-between hover:border-emerald-500 transition-all shadow-sm"
              >
                <div>
                  <div className="flex justify-between items-start">
                    <span className="font-mono text-xs text-gray-500">{dataset.slug}</span>
                    <span
                      className={`status-pill ${
                        dataset.status === "ACTIVE" ? "active" : "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {dataset.status}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-gray-900 mt-2">{dataset.name}</h3>
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                    {dataset.description || "No description provided."}
                  </p>

                  <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between text-xs text-gray-600">
                    <div className="flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-gray-400" />
                      <span>{ver?.name || "v1"}</span>
                      <span className="badge-subtle uppercase">{ver?.status || "DRAFT"}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span>{ver?.total_documents || 0} docs</span>
                      <span>•</span>
                      <span>{formatSize(ver?.total_raw_bytes || 0)}</span>
                    </div>
                  </div>
                </div>

                <div className="mt-5 pt-3 border-t border-gray-100 flex items-center justify-between">
                  <button
                    onClick={() => archiveMutation.mutate(dataset.id)}
                    className="btn-destructive-ghost text-xs flex items-center gap-1 p-1"
                    title="Archive dataset"
                  >
                    <Archive className="w-3.5 h-3.5" />
                    <span>Archive</span>
                  </button>

                  <button
                    onClick={() => navigate(`/datasets/${dataset.id}`)}
                    className="btn-secondary text-xs flex items-center gap-1.5"
                  >
                    <span>Open Dataset</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Dataset Modal */}
      {showCreateModal && (
        <div className="modal-backdrop" onClick={() => setShowCreateModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center pb-3 border-b border-gray-100">
              <h3 className="text-base font-bold text-gray-900">Create New Dataset</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-400 hover:text-gray-600 p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && <div className="alert-error mt-4">{formError}</div>}

            <form onSubmit={handleCreateSubmit} className="mt-4 flex flex-col gap-4">
              <div className="form-group">
                <label>Dataset Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. HR Policies & Onboarding"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="input-field"
                />
              </div>

              <div className="form-group">
                <label>URL Slug *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. hr-policies"
                  value={slug}
                  onChange={(e) => {
                    setIsSlugManual(true);
                    setSlug(e.target.value);
                  }}
                  className="input-field font-mono text-xs"
                />
                <small className="text-gray-400 text-xs mt-1">
                  Lowercase letters, numbers, and hyphens only.
                </small>
              </div>

              <div className="form-group">
                <label>Description</label>
                <textarea
                  rows={3}
                  placeholder="Summarize the purpose of this dataset collection..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="input-field text-sm"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-gray-100 mt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="btn-primary text-sm"
                >
                  {createMutation.isPending ? "Creating..." : "Create Dataset"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
