import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  GitBranch,
  ArrowLeft,
  Lock,
  Clock,
  CheckCircle2,
  AlertTriangle,
  FileJson,
  Package,
  ShieldCheck,
  History,
  FileCheck,
  Cpu,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { fetchModelVersion, finalizeModelVersionManifest } from "../api";
import type { ModelVersion } from "../types";
import { ProvenancePillarsCard } from "../components/ProvenancePillarsCard";
import { ReleaseManifestCard } from "../components/ReleaseManifestCard";
import { RegisteredArtifactsTable } from "../components/RegisteredArtifactsTable";
import { Gate3ReviewCard } from "../components/Gate3ReviewCard";
import { RegisterStagedArtifactModal } from "../components/RegisterStagedArtifactModal";

type ActiveTab = "provenance" | "artifacts" | "manifest" | "gate3" | "audit";

export function ModelVersionDetailPage() {
  const { workspaceId: paramWsId, versionId = "" } = useParams<{
    workspaceId?: string;
    versionId: string;
  }>();
  const { activeWorkspace, user } = useAuth();
  const workspaceId = paramWsId || activeWorkspace?.id || "default-ws";
  const currentUserId = user?.id || "anonymous-user";

  const [version, setVersion] = useState<ModelVersion | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>("provenance");
  const [isLoading, setIsLoading] = useState(true);
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [isRegisterModalOpen, setIsRegisterModalOpen] = useState(false);

  const loadVersion = useCallback(async () => {
    if (!versionId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchModelVersion(workspaceId, versionId);
      setVersion(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load model version";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId, versionId]);

  useEffect(() => {
    loadVersion();
  }, [loadVersion]);

  const handleFinalizeManifest = async () => {
    if (!version) return;
    setIsFinalizing(true);
    setError(null);
    setActionSuccess(null);
    try {
      const res = await finalizeModelVersionManifest(workspaceId, version.id);
      setActionSuccess(`Release manifest successfully finalized! Digest: ${res.release_manifest_digest.slice(0, 16)}...`);
      await loadVersion();
      setActiveTab("gate3");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to finalize manifest";
      setError(msg);
    } finally {
      setIsFinalizing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-16 text-center">
        <GitBranch className="w-8 h-8 mx-auto text-muted-foreground/40 animate-pulse mb-3" />
        <p className="text-sm text-muted-foreground">Loading model version details...</p>
      </div>
    );
  }

  if (error || !version) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12 space-y-4">
        <Link
          to="/artifact-registry"
          className="inline-flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Artifact Registry
        </Link>
        <div className="p-6 rounded-xl bg-card border border-border shadow-sm text-center space-y-3">
          <AlertTriangle className="w-10 h-10 mx-auto text-red-500/80" />
          <h2 className="text-lg font-bold text-foreground">Model Version Not Found</h2>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            {error || "The requested model version could not be found or you lack permission to view it."}
          </p>
          <button
            onClick={loadVersion}
            className="px-4 py-2 rounded-lg bg-secondary text-foreground text-xs font-semibold hover:bg-secondary/80 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const isDraft = version.status === "DRAFT";
  const isApproved = version.status === "APPROVED";
  const isPending = version.status === "PENDING_REVIEW";
  const isRevoked = version.status === "REVOKED";

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 py-8">
      {/* Top Navigation & Status */}
      <div className="space-y-4 border-b border-border pb-6">
        <div className="flex items-center justify-between">
          <Link
            to="/artifact-registry"
            className="inline-flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Artifact Registry
          </Link>
          <div className="flex items-center gap-2">
            <button
              onClick={loadVersion}
              className="p-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
              title="Refresh version"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
              <GitBranch className="w-7 h-7" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight text-foreground">
                  {version.version_tag}
                </h1>
                {version.is_immutable && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                    <Lock className="w-3 h-3" />
                    Immutable
                  </span>
                )}
                <span
                  className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                    isApproved
                      ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                      : isPending
                      ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 animate-pulse"
                      : isRevoked
                      ? "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20"
                      : "bg-secondary text-secondary-foreground border-border"
                  }`}
                >
                  {isApproved && <CheckCircle2 className="w-3 h-3" />}
                  {isPending && <Clock className="w-3 h-3" />}
                  {isRevoked && <AlertTriangle className="w-3 h-3" />}
                  {version.status}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Base Model:{" "}
                <span className="font-mono font-semibold text-foreground">
                  {version.source_model_key}
                </span>{" "}
                ({version.source_model_revision}) · Recipe:{" "}
                <span className="font-medium text-foreground">{version.recipe_key}</span>
              </p>
            </div>
          </div>

          {/* Action Area */}
          <div className="flex items-center gap-3">
            {isDraft && (
              <>
                <button
                  onClick={() => setIsRegisterModalOpen(true)}
                  className="px-3.5 py-2 rounded-lg border border-border text-foreground hover:bg-secondary font-semibold text-xs transition-colors"
                >
                  Register Staged Artifact
                </button>
                <button
                  onClick={handleFinalizeManifest}
                  disabled={isFinalizing || (version.artifacts?.length ?? 0) === 0}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground font-semibold text-xs hover:bg-primary/90 disabled:opacity-50 transition-colors shadow-sm"
                  title={
                    (version.artifacts?.length ?? 0) === 0
                      ? "Register at least one artifact before finalizing"
                      : "Validate provenance, freeze manifest, and submit to Gate 3"
                  }
                >
                  <FileCheck className="w-4 h-4" />
                  {isFinalizing ? "Finalizing Manifest..." : "Finalize Release Manifest"}
                </button>
              </>
            )}
          </div>
        </div>

        {actionSuccess && (
          <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-600 dark:text-emerald-400 flex items-center justify-between">
            <span>{actionSuccess}</span>
            <button onClick={() => setActionSuccess(null)} className="underline text-[11px] ml-4">
              Dismiss
            </button>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-border overflow-x-auto pb-px">
        {[
          { id: "provenance", label: "Provenance & Overview", icon: ShieldCheck },
          {
            id: "artifacts",
            label: `Artifacts (${version.artifacts?.length ?? 0})`,
            icon: Package,
          },
          { id: "manifest", label: "Release Manifest & Digest", icon: FileJson },
          { id: "gate3", label: "Gate 3 Review Centre", icon: Lock },
          {
            id: "audit",
            label: `Audit History (${version.release_events?.length ?? 0})`,
            icon: History,
          },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id as ActiveTab)}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap ${
              activeTab === id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab Panels */}
      <div className="space-y-6">
        {activeTab === "provenance" && (
          <div className="space-y-6">
            <ProvenancePillarsCard version={version} />

            {/* Hardware & Evaluation Specification Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-6 rounded-xl bg-card border border-border shadow-sm space-y-4">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-amber-500" />
                  Evaluation & Quality Delta
                </h3>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border">
                    <p className="text-[11px] text-muted-foreground uppercase font-semibold">
                      Base Score
                    </p>
                    <p className="text-base font-bold text-foreground mt-0.5">
                      {version.base_evaluation_score !== null &&
                      version.base_evaluation_score !== undefined
                        ? version.base_evaluation_score.toFixed(3)
                        : "N/A"}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border">
                    <p className="text-[11px] text-muted-foreground uppercase font-semibold">
                      Final Score
                    </p>
                    <p className="text-base font-bold text-foreground mt-0.5">
                      {version.final_evaluation_score !== null &&
                      version.final_evaluation_score !== undefined
                        ? version.final_evaluation_score.toFixed(3)
                        : "N/A"}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border">
                    <p className="text-[11px] text-muted-foreground uppercase font-semibold">
                      Delta (Δ)
                    </p>
                    <p
                      className={`text-base font-bold mt-0.5 ${
                        (version.quality_delta ?? 0) >= 0
                          ? "text-emerald-600 dark:text-emerald-400"
                          : "text-red-500"
                      }`}
                    >
                      {version.quality_delta !== null && version.quality_delta !== undefined
                        ? `${version.quality_delta > 0 ? "+" : ""}${version.quality_delta.toFixed(3)}`
                        : "N/A"}
                    </p>
                  </div>
                </div>
              </div>

              <div className="p-6 rounded-xl bg-card border border-border shadow-sm space-y-4">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-emerald-500" />
                  Hardware Execution Guardrails
                </h3>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border">
                    <p className="text-[11px] text-muted-foreground uppercase font-semibold">
                      Min Host RAM
                    </p>
                    <p className="text-base font-bold text-foreground mt-0.5">
                      {(version.min_ram_mb / 1024).toFixed(1)} GB
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border">
                    <p className="text-[11px] text-muted-foreground uppercase font-semibold">
                      Min GPU VRAM
                    </p>
                    <p className="text-base font-bold text-foreground mt-0.5">
                      {(version.min_vram_mb / 1024).toFixed(1)} GB
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border">
                    <p className="text-[11px] text-muted-foreground uppercase font-semibold">
                      Target GPU
                    </p>
                    <p className="text-xs font-mono font-bold text-foreground mt-1 truncate">
                      {version.target_hardware_key || "ANY_COMPATIBLE"}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "artifacts" && (
          <div className="space-y-6">
            <RegisteredArtifactsTable
              artifacts={version.artifacts || []}
              isDraft={isDraft}
              onRegisterArtifact={() => setIsRegisterModalOpen(true)}
            />
          </div>
        )}

        {activeTab === "manifest" && (
          <div className="space-y-6">
            <ReleaseManifestCard version={version} />
          </div>
        )}

        {activeTab === "gate3" && (
          <div className="space-y-6">
            <Gate3ReviewCard
              version={version}
              workspaceId={workspaceId}
              currentUserId={currentUserId}
              onRefresh={loadVersion}
            />
          </div>
        )}

        {activeTab === "audit" && (
          <div className="p-6 rounded-xl bg-card border border-border shadow-sm space-y-4">
            <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
              <History className="w-5 h-5 text-primary" />
              Immutable Release Audit Log
            </h3>
            <p className="text-xs text-muted-foreground">
              Append-only tamper-evident record of all lifecycle events for this model version.
            </p>

            {(version.release_events?.length ?? 0) === 0 ? (
              <p className="text-xs text-muted-foreground italic py-6 text-center">
                No events recorded yet.
              </p>
            ) : (
              <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
                {version.release_events?.map((evt) => (
                  <div key={evt.id} className="relative group">
                    <div className="absolute -left-6 top-1.5 w-2.5 h-2.5 rounded-full bg-primary ring-4 ring-background" />
                    <div className="p-3.5 rounded-lg bg-secondary/40 border border-border space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-semibold text-foreground">
                          {evt.event_type}
                        </span>
                        <span className="text-[11px] text-muted-foreground">
                          {new Date(evt.created_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground">{evt.message}</p>
                      {evt.metadata_json && evt.metadata_json !== "{}" && (
                        <pre className="text-[10px] font-mono bg-background p-2 rounded border border-border overflow-x-auto text-muted-foreground mt-2">
                          {evt.metadata_json}
                        </pre>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Register Staged Artifact Modal */}
      <RegisterStagedArtifactModal
        workspaceId={workspaceId}
        version={version}
        isOpen={isRegisterModalOpen}
        onClose={() => setIsRegisterModalOpen(false)}
        onSuccess={() => {
          loadVersion();
          setActiveTab("artifacts");
        }}
      />
    </div>
  );
}
