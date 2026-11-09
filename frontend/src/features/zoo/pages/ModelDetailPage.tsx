import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  Download,
  Globe,
  HardDrive,
  Lock,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { authorizeModelArtifactDownload, getModelDetail } from "../api";
import { HardwareSnapshotList } from "../components/HardwareBadgePill";
import { InstallationSnippetViewer } from "../components/InstallationSnippetViewer";
import type { DownloadAuthorizationResponse } from "../types";

export function ModelDetailPage() {
  const { listingId } = useParams<{ listingId: string }>();
  const { activeWorkspace } = useAuth();
  const workspaceId = activeWorkspace?.id;

  const [activeTab, setActiveTab] = useState<
    "OVERVIEW" | "HARDWARE" | "ARTIFACTS" | "INSTALL" | "AUDIT"
  >("OVERVIEW");

  const [downloadModalData, setDownloadModalData] = useState<DownloadAuthorizationResponse | null>(
    null
  );
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [isAuthorizing, setIsAuthorizing] = useState(false);

  const detailQuery = useQuery({
    queryKey: ["zoo-model-detail", listingId],
    queryFn: () => (listingId ? getModelDetail(listingId) : Promise.reject("No listing ID")),
    enabled: Boolean(listingId),
  });

  const detail = detailQuery.data;

  const handleDownload = async (artifactId: string) => {
    if (!workspaceId || !listingId) return;
    try {
      setIsAuthorizing(true);
      setDownloadError(null);
      const res = await authorizeModelArtifactDownload(workspaceId, listingId, artifactId);
      setDownloadModalData(res);
    } catch (err: unknown) {
      setDownloadError(err instanceof Error ? err.message : "Download authorization failed");
    } finally {
      setIsAuthorizing(false);
    }
  };

  if (detailQuery.isLoading) {
    return <div className="max-w-7xl mx-auto p-12 text-center text-sm text-muted-foreground">Loading release details...</div>;
  }

  if (detailQuery.isError || !detail) {
    return (
      <div className="max-w-7xl mx-auto p-8 my-6 text-center text-xs text-destructive border rounded-xl bg-destructive/5">
        Failed to load model release details. It may be private or unapproved.
      </div>
    );
  }

  const { listing, model_family, model_version, artifacts, hardware_badges, installation_snippets } = detail;
  const isDownloadable = listing.distribution_status === "DOWNLOADABLE";

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6 sm:p-8">
      {/* Top back link */}
      <div>
        <Link
          to="/zoo/models"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Model Zoo
        </Link>

        {/* Title Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-muted font-semibold text-foreground">
                {model_version.version_tag}
              </span>
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/40 dark:text-blue-300">
                {listing.category.replace(/_/g, " ")}
              </span>
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200 dark:bg-purple-950/40 dark:text-purple-300">
                {listing.visibility === "PUBLIC" ? <Globe className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
                {listing.visibility}
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">{listing.title}</h1>
            <p className="text-xs text-muted-foreground mt-1 max-w-2xl">{listing.description}</p>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border ${
                isDownloadable
                  ? "bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300"
                  : "bg-zinc-100 text-zinc-600 border-zinc-300 dark:bg-zinc-800 dark:text-zinc-400"
              }`}
            >
              {isDownloadable ? <Download className="w-4 h-4" /> : <HardDrive className="w-4 h-4" />}
              {isDownloadable ? "Distribution: Downloadable" : "Distribution: Metadata Only"}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b text-xs font-medium space-x-6">
        {(
          [
            { key: "OVERVIEW", label: "Overview & Specs" },
            { key: "HARDWARE", label: "Hardware Matrix" },
            { key: "ARTIFACTS", label: `Artifacts (${artifacts.length})` },
            { key: "INSTALL", label: "Installation Guides" },
            { key: "AUDIT", label: "Cryptographic Provenance" },
          ] as const
        ).map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setActiveTab(t.key)}
            className={`pb-3 border-b-2 font-semibold transition-colors ${
              activeTab === t.key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* TAB CONTENT: Overview */}
      {activeTab === "OVERVIEW" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg border bg-card">
              <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">
                Base Architecture
              </span>
              <span className="text-sm font-semibold font-mono text-foreground">
                {model_version.source_model_key}
              </span>
              <span className="text-xs text-muted-foreground block mt-1">
                Revision: {model_version.source_model_revision || "default"}
              </span>
            </div>

            <div className="p-4 rounded-lg border bg-card">
              <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">
                Fine-Tuning Recipe
              </span>
              <span className="text-sm font-semibold font-mono text-foreground">
                {model_version.recipe_key || "Direct Release"}
              </span>
              <span className="text-xs text-muted-foreground block mt-1">
                Task: {model_family.task_type}
              </span>
            </div>

            <div className="p-4 rounded-lg border bg-card">
              <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">
                Evaluation Quality
              </span>
              <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                {model_version.final_evaluation_score != null
                  ? `${(model_version.final_evaluation_score * 100).toFixed(1)}%`
                  : "N/A"}
              </span>
              <span className="text-xs text-muted-foreground block mt-1">
                {model_version.quality_delta != null
                  ? `Delta: ${(model_version.quality_delta * 100).toFixed(1)}% vs base`
                  : "Certified benchmark"}
              </span>
            </div>
          </div>

          {listing.detailed_description && (
            <div className="p-5 rounded-lg border bg-card">
              <h3 className="text-sm font-semibold text-foreground mb-2">Description & Usage Guidelines</h3>
              <p className="text-xs text-muted-foreground whitespace-pre-wrap leading-relaxed">
                {listing.detailed_description}
              </p>
            </div>
          )}

          {listing.tags && listing.tags.length > 0 && (
            <div>
              <span className="text-xs font-semibold text-muted-foreground block mb-2">Tags</span>
              <div className="flex flex-wrap gap-1.5">
                {listing.tags.map((t) => (
                  <span key={t} className="px-2 py-0.5 rounded text-xs bg-muted text-muted-foreground font-mono">
                    #{t}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: Hardware Compatibility Matrix */}
      {activeTab === "HARDWARE" && (
        <div className="space-y-6">
          <div className="p-4 rounded-lg border bg-card">
            <h3 className="text-sm font-semibold text-foreground mb-1">Hardware Compatibility Snapshots</h3>
            <p className="text-xs text-muted-foreground mb-4">
              Honest hardware badges. TESTED badges are restricted strictly to measured physical benchmarks.
            </p>
            <HardwareSnapshotList snapshots={hardware_badges} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-lg border bg-card">
              <span className="text-xs font-semibold text-muted-foreground block mb-1">Minimum RAM</span>
              <span className="text-lg font-bold font-mono text-foreground">
                {(model_version.min_ram_mb / 1024).toFixed(1)} GB
              </span>
              <span className="text-xs text-muted-foreground block mt-1">
                Estimated minimum system RAM required for reliable inference.
              </span>
            </div>

            <div className="p-4 rounded-lg border bg-card">
              <span className="text-xs font-semibold text-muted-foreground block mb-1">Minimum VRAM</span>
              <span className="text-lg font-bold font-mono text-foreground">
                {(model_version.min_vram_mb / 1024).toFixed(1)} GB
              </span>
              <span className="text-xs text-muted-foreground block mt-1">
                Required dedicated GPU memory for accelerated inference.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: Downloadable Artifacts */}
      {activeTab === "ARTIFACTS" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Cryptographically verified artifact packages registered in Milestone 11.
            </p>
          </div>

          {downloadError && (
            <div className="p-3 rounded-md bg-destructive/10 text-destructive text-xs flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 shrink-0" />
              <span>{downloadError}</span>
            </div>
          )}

          <div className="border rounded-lg overflow-hidden bg-card">
            <table className="w-full text-xs text-left">
              <thead className="bg-muted/50 border-b">
                <tr>
                  <th className="p-3 font-semibold">Artifact Type</th>
                  <th className="p-3 font-semibold">Format</th>
                  <th className="p-3 font-semibold">Size</th>
                  <th className="p-3 font-semibold">SHA-256 Digest</th>
                  <th className="p-3 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {artifacts.map((art) => (
                  <tr key={art.id} className="hover:bg-muted/30">
                    <td className="p-3 font-semibold text-foreground">
                      {art.artifact_type}
                      {art.is_primary_weights && (
                        <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] bg-primary/10 text-primary">
                          Primary
                        </span>
                      )}
                    </td>
                    <td className="p-3 font-mono">{art.format}</td>
                    <td className="p-3 font-mono">{(art.file_size_bytes / 1024 / 1024).toFixed(1)} MB</td>
                    <td className="p-3 font-mono text-muted-foreground truncate max-w-[200px]" title={art.sha256}>
                      {art.sha256}
                    </td>
                    <td className="p-3 text-right">
                      {isDownloadable ? (
                        <button
                          type="button"
                          onClick={() => handleDownload(art.id)}
                          disabled={isAuthorizing}
                          className="px-2.5 py-1 text-xs font-semibold rounded border bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                        >
                          Authorize Download
                        </button>
                      ) : (
                        <span className="text-muted-foreground italic">Restricted</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Download Token Modal */}
          {downloadModalData && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
              <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-lg space-y-4">
                <div className="flex items-center gap-2 text-emerald-600">
                  <CheckCircle2 className="w-5 h-5" />
                  <h3 className="text-base font-semibold text-foreground">Download Authorized</h3>
                </div>
                <p className="text-xs text-muted-foreground">
                  Your tenant-governed download authorization has been cryptographically confirmed.
                </p>

                <div className="p-3 rounded bg-muted/40 space-y-2 text-xs font-mono">
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Storage Reference</span>
                    <span className="text-foreground">{downloadModalData.storage_reference}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">SHA-256</span>
                    <span className="text-foreground truncate block">{downloadModalData.sha256}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Authorized URL</span>
                    <a
                      href={downloadModalData.download_url}
                      className="text-primary hover:underline break-all block"
                    >
                      {downloadModalData.download_url}
                    </a>
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="button"
                    onClick={() => setDownloadModalData(null)}
                    className="px-4 py-1.5 text-xs font-semibold rounded bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: Installation Guides */}
      {activeTab === "INSTALL" && (
        <div className="space-y-4">
          <InstallationSnippetViewer snippets={installation_snippets} />
        </div>
      )}

      {/* TAB CONTENT: Audit Provenance */}
      {activeTab === "AUDIT" && (
        <div className="space-y-4">
          <div className="p-4 rounded-lg border bg-card space-y-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              <h3 className="text-sm font-semibold text-foreground">Gate 3 Release Verification</h3>
            </div>
            <div className="space-y-2 text-xs font-mono">
              <div>
                <span className="text-muted-foreground block text-[10px] uppercase font-sans">
                  Release Manifest Digest (SHA-256)
                </span>
                <span className="p-2 rounded bg-muted/40 block text-foreground truncate select-all">
                  {model_version.release_manifest_digest}
                </span>
              </div>
              {listing.publication_digest && (
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase font-sans">
                    Public Catalog Digest (SHA-256)
                  </span>
                  <span className="p-2 rounded bg-muted/40 block text-foreground truncate select-all">
                    {listing.publication_digest}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
