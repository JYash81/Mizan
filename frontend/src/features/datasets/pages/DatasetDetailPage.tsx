import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle,
  Eye,
  FileText,
  Layers,
  Lock,
  Plus,
  RefreshCw,
  Trash2,
  X,
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import { apiGet, apiPost, apiDelete } from "../../../lib/api/client";
import { UploadDropzone } from "../components/UploadDropzone";
import { DocumentPreviewModal } from "../components/DocumentPreviewModal";
import type { Dataset, DatasetVersion, Document, CreateVersionPayload } from "../types";

export function DatasetDetailPage() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const { activeWorkspace } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const workspaceId = activeWorkspace?.id;

  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null);
  const [showNewVersionModal, setShowNewVersionModal] = useState(false);
  const [newVersionName, setNewVersionName] = useState("");
  const [newVersionDesc, setNewVersionDesc] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  // 1. Fetch Dataset detail
  const { data: datasetData, isLoading: loadingDataset } = useQuery<{ dataset: Dataset }>({
    queryKey: ["dataset", workspaceId, datasetId],
    queryFn: () => apiGet<{ dataset: Dataset }>(`/api/v1/workspaces/${workspaceId}/datasets/${datasetId}`),
    enabled: !!workspaceId && !!datasetId,
  });

  // 2. Fetch Dataset Versions
  const { data: versionsData, isLoading: loadingVersions } = useQuery<{ versions: DatasetVersion[] }>({
    queryKey: ["dataset_versions", workspaceId, datasetId],
    queryFn: () =>
      apiGet<{ versions: DatasetVersion[] }>(
        `/api/v1/workspaces/${workspaceId}/datasets/${datasetId}/versions`
      ),
    enabled: !!workspaceId && !!datasetId,
  });

  const versions = versionsData?.versions || [];
  const activeVersion =
    versions.find((v) => v.id === selectedVersionId) ||
    versions[0] ||
    datasetData?.dataset?.active_version;

  // 3. Fetch Documents in active version
  const currentVersionId = activeVersion?.id;
  const { data: docsData, isLoading: loadingDocs, refetch: refetchDocs } = useQuery<{
    documents: Document[];
  }>({
    queryKey: ["documents", workspaceId, datasetId, currentVersionId],
    queryFn: () =>
      apiGet<{ documents: Document[] }>(
        `/api/v1/workspaces/${workspaceId}/datasets/${datasetId}/versions/${currentVersionId}/documents`
      ),
    enabled: !!workspaceId && !!datasetId && !!currentVersionId,
  });

  // Mutations
  const createVersionMutation = useMutation({
    mutationFn: (payload: CreateVersionPayload) =>
      apiPost<{ version: DatasetVersion }>(
        `/api/v1/workspaces/${workspaceId}/datasets/${datasetId}/versions`,
        payload
      ),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["dataset_versions", workspaceId, datasetId] });
      setSelectedVersionId(res.version.id);
      setShowNewVersionModal(false);
      setNewVersionName("");
      setNewVersionDesc("");
      setActionError(null);
    },
    onError: (err: unknown) => {
      setActionError(err instanceof Error ? err.message : "Failed to create version");
    },
  });

  const finalizeVersionMutation = useMutation({
    mutationFn: () =>
      apiPost<{ version: DatasetVersion }>(
        `/api/v1/workspaces/${workspaceId}/datasets/${datasetId}/versions/${currentVersionId}/finalize`
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dataset_versions", workspaceId, datasetId] });
      queryClient.invalidateQueries({ queryKey: ["dataset", workspaceId, datasetId] });
      setActionError(null);
    },
    onError: (err: unknown) => {
      setActionError(err instanceof Error ? err.message : "Failed to finalize version");
    },
  });

  const deleteDocMutation = useMutation({
    mutationFn: (docId: string) =>
      apiDelete(`/api/v1/workspaces/${workspaceId}/documents/${docId}`),
    onSuccess: () => {
      refetchDocs();
      queryClient.invalidateQueries({ queryKey: ["dataset_versions", workspaceId, datasetId] });
    },
  });

  const reprocessDocMutation = useMutation({
    mutationFn: (docId: string) =>
      apiPost(`/api/v1/workspaces/${workspaceId}/documents/${docId}/reprocess`),
    onSuccess: () => {
      refetchDocs();
    },
  });

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  if (loadingDataset || loadingVersions) {
    return (
      <div className="page-container py-12 text-center text-gray-500 text-sm">
        Loading dataset details...
      </div>
    );
  }

  const dataset = datasetData?.dataset;
  if (!dataset) {
    return (
      <div className="page-container py-12 text-center">
        <h2 className="text-xl font-bold text-gray-800">Dataset Not Found</h2>
        <button onClick={() => navigate("/datasets")} className="btn-secondary mt-4">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Datasets
        </button>
      </div>
    );
  }

  const documents = docsData?.documents || [];
  const isDraft = activeVersion?.status === "DRAFT";

  return (
    <div className="page-container pb-20">
      {/* Top Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-gray-500 mb-4">
        <button
          onClick={() => navigate("/datasets")}
          className="flex items-center gap-1 hover:text-emerald-700 font-medium transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Datasets</span>
        </button>
        <span>/</span>
        <span className="font-mono text-gray-800">{dataset.slug}</span>
      </div>

      {/* Dataset Header */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold text-gray-900">{dataset.name}</h2>
              <span
                className={`status-pill ${
                  dataset.status === "ACTIVE" ? "active" : "bg-gray-100 text-gray-600"
                }`}
              >
                {dataset.status}
              </span>
            </div>
            <p className="text-sm text-gray-600 mt-1 max-w-2xl">
              {dataset.description || "No description provided for this dataset."}
            </p>
          </div>

          {/* Version Switcher and Actions */}
          <div className="flex items-center gap-3 self-start md:self-center">
            <div className="flex items-center gap-2 bg-gray-50 p-1.5 rounded-lg border border-gray-200 text-xs">
              <Layers className="w-4 h-4 text-gray-400 ml-1" />
              <select
                value={activeVersion?.id || ""}
                onChange={(e) => setSelectedVersionId(e.target.value)}
                className="bg-transparent border-none text-xs font-semibold text-gray-800 focus:outline-none cursor-pointer"
              >
                {versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.status}) — {v.total_documents} docs
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={() => setShowNewVersionModal(true)}
              className="btn-secondary text-xs flex items-center gap-1"
              title="Create new dataset version"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Version</span>
            </button>

            {isDraft ? (
              <button
                onClick={() => finalizeVersionMutation.mutate()}
                disabled={finalizeVersionMutation.isPending || documents.length === 0}
                className="btn-primary text-xs flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700"
                title="Freeze version and compute cryptographic hash for Gate 1"
              >
                <Lock className="w-3.5 h-3.5" />
                <span>
                  {finalizeVersionMutation.isPending ? "Freezing..." : "Freeze Version (Gate 1 Ready)"}
                </span>
              </button>
            ) : (
              <div className="flex items-center gap-1.5 bg-emerald-50 text-emerald-800 px-3 py-1.5 rounded-md border border-emerald-200 text-xs font-semibold">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                <span>Version Frozen ({activeVersion?.status})</span>
              </div>
            )}
          </div>
        </div>

        {/* Version metadata strip */}
        {activeVersion && (
          <div className="mt-6 pt-4 border-t border-gray-100 flex flex-wrap items-center gap-6 text-xs text-gray-500">
            <div>
              <span className="text-gray-400">Version:</span>{" "}
              <strong className="text-gray-800">{activeVersion.name}</strong>
            </div>
            <div>
              <span className="text-gray-400">Total Documents:</span>{" "}
              <strong className="text-gray-800">{activeVersion.total_documents}</strong>
            </div>
            <div>
              <span className="text-gray-400">Total Size:</span>{" "}
              <strong className="text-gray-800">{formatSize(activeVersion.total_raw_bytes)}</strong>
            </div>
            {activeVersion.content_hash && (
              <div className="font-mono">
                <span className="text-gray-400">Version Digest:</span>{" "}
                <span className="text-gray-700">{activeVersion.content_hash.substring(0, 16)}...</span>
              </div>
            )}
          </div>
        )}
      </div>

      {actionError && <div className="alert-error mt-4">{actionError}</div>}

      {/* Upload Dropzone Section (active when version is DRAFT) */}
      <div className="mt-8">
        <div className="mb-3 flex justify-between items-center">
          <div>
            <h3 className="text-base font-bold text-gray-900">Upload Business Documents</h3>
            <p className="text-xs text-gray-500">
              Files uploaded to the Workshop Data Plane are stored safely in Sovereign Storage and parsed locally.
            </p>
          </div>
          {!isDraft && (
            <span className="text-xs font-medium text-amber-700 bg-amber-50 px-2.5 py-1 rounded border border-amber-200">
              Version is locked. Create a new version to upload more files.
            </span>
          )}
        </div>

        <UploadDropzone
          workspaceId={workspaceId!}
          datasetId={dataset.id}
          versionId={activeVersion?.id || ""}
          disabled={!isDraft}
          onUploadSuccess={() => {
            refetchDocs();
            queryClient.invalidateQueries({ queryKey: ["dataset_versions", workspaceId, datasetId] });
          }}
        />
      </div>

      {/* Documents Table Section */}
      <div className="mt-10">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h3 className="text-base font-bold text-gray-900">
              Documents in Version ({documents.length})
            </h3>
            <p className="text-xs text-gray-500">
              Extracted texts and structure available for AI evaluation, masking, and RAG ingestion.
            </p>
          </div>
        </div>

        {loadingDocs ? (
          <div className="p-8 text-center text-gray-500 text-sm">Loading documents...</div>
        ) : documents.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-lg p-10 text-center text-gray-500">
            <FileText className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="text-sm font-medium text-gray-700">No documents in this version yet.</p>
            <p className="text-xs text-gray-400 mt-1">
              Drag and drop supported business files above to begin ingestion.
            </p>
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Document Name</th>
                  <th>Format</th>
                  <th>Size</th>
                  <th>Extracted Content</th>
                  <th>Status</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-gray-50/60 transition-colors">
                    <td>
                      <div className="flex items-center gap-2.5">
                        <FileText className="w-4 h-4 text-emerald-600 shrink-0" />
                        <div>
                          <p className="font-semibold text-gray-900">{doc.name}</p>
                          <p className="font-mono text-[10px] text-gray-400">
                            {doc.raw_sha256.substring(0, 16)}...
                          </p>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="badge-subtle uppercase">{doc.file_type}</span>
                    </td>
                    <td className="text-xs text-gray-600">{formatSize(doc.raw_file_size_bytes)}</td>
                    <td className="text-xs text-gray-600">
                      {doc.word_count.toLocaleString()} words
                      {doc.page_count ? ` • ${doc.page_count} pgs` : ""}
                    </td>
                    <td>
                      {doc.extraction_status === "COMPLETED" ? (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                          <CheckCircle className="w-3 h-3 text-emerald-600" />
                          Parsed
                        </span>
                      ) : doc.extraction_status === "PARSING" ? (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200 animate-pulse">
                          Parsing...
                        </span>
                      ) : (
                        <span
                          className="inline-flex items-center gap-1 text-xs font-semibold text-red-700 bg-red-50 px-2 py-0.5 rounded-full border border-red-200"
                          title={doc.extraction_error || "Extraction failed"}
                        >
                          Failed
                        </span>
                      )}
                    </td>
                    <td className="text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => setPreviewDoc(doc)}
                          className="btn-secondary text-xs p-1.5 px-2.5 flex items-center gap-1"
                          title="Preview Extracted Content"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Preview</span>
                        </button>

                        {isDraft && (
                          <>
                            <button
                              onClick={() => reprocessDocMutation.mutate(doc.id)}
                              className="btn-secondary text-xs p-1.5 px-2"
                              title="Reprocess Extraction"
                            >
                              <RefreshCw className="w-3.5 h-3.5 text-gray-500" />
                            </button>

                            <button
                              onClick={() => deleteDocMutation.mutate(doc.id)}
                              className="btn-destructive-ghost p-1.5"
                              title="Delete Document"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Document Preview Modal */}
      {previewDoc && (
        <DocumentPreviewModal document={previewDoc} onClose={() => setPreviewDoc(null)} />
      )}

      {/* New Version Modal */}
      {showNewVersionModal && (
        <div className="modal-backdrop" onClick={() => setShowNewVersionModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center pb-3 border-b border-gray-100">
              <h3 className="text-base font-bold text-gray-900">Create New Version</h3>
              <button
                onClick={() => setShowNewVersionModal(false)}
                className="text-gray-400 hover:text-gray-600 p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                createVersionMutation.mutate({
                  name: newVersionName.trim() || undefined,
                  description: newVersionDesc.trim() || undefined,
                });
              }}
              className="mt-4 flex flex-col gap-4"
            >
              <div className="form-group">
                <label>Version Name (optional)</label>
                <input
                  type="text"
                  placeholder={`e.g. v${versions.length + 1}`}
                  value={newVersionName}
                  onChange={(e) => setNewVersionName(e.target.value)}
                  className="input-field"
                />
              </div>

              <div className="form-group">
                <label>Version Description</label>
                <textarea
                  rows={3}
                  placeholder="Notes about changes or additions in this version..."
                  value={newVersionDesc}
                  onChange={(e) => setNewVersionDesc(e.target.value)}
                  className="input-field text-sm"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-gray-100 mt-2">
                <button
                  type="button"
                  onClick={() => setShowNewVersionModal(false)}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createVersionMutation.isPending}
                  className="btn-primary text-sm"
                >
                  {createVersionMutation.isPending ? "Creating..." : "Create Version"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
