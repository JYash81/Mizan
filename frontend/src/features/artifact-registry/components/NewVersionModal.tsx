import { useState, useEffect } from "react";
import { X, GitBranch, Sparkles, Cpu, ShieldCheck } from "lucide-react";
import { createModelVersion } from "../api";
import { fetchBuildRuns } from "../../model-building/api";
import type { ModelFamily, ModelVersion, CreateModelVersionRequest } from "../types";
import type { ModelBuildRun } from "../../model-building/types";

interface NewVersionModalProps {
  workspaceId: string;
  family: ModelFamily;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (version: ModelVersion) => void;
}

export function NewVersionModal({
  workspaceId,
  family,
  isOpen,
  onClose,
  onSuccess,
}: NewVersionModalProps) {
  const [versionTag, setVersionTag] = useState("v1.0.0");
  const [description, setDescription] = useState("");
  const [sourceModelKey, setSourceModelKey] = useState("meta-llama/Llama-3-8B-Instruct");
  const [sourceModelRevision, setSourceModelRevision] = useState("main");
  const [recipeKey, setRecipeKey] = useState("LORA_FINETUNE_SFT_V1");
  const [buildRunId, setBuildRunId] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [datasetVersionId, setDatasetVersionId] = useState("");
  const [datasetVersionDigest, setDatasetVersionDigest] = useState("");
  const [gate1ApprovalId, setGate1ApprovalId] = useState("");
  const [baseScore, setBaseScore] = useState<number | undefined>(0.75);
  const [finalScore, setFinalScore] = useState<number | undefined>(0.84);
  const [minRamMb, setMinRamMb] = useState<number>(16384);
  const [minVramMb, setMinVramMb] = useState<number>(8192);
  const [targetHardwareKey, setTargetHardwareKey] = useState("NVIDIA_T4_16GB");

  const [buildRuns, setBuildRuns] = useState<ModelBuildRun[]>([]);
  const [isLoadingRuns, setIsLoadingRuns] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    let mounted = true;
    setIsLoadingRuns(true);
    fetchBuildRuns(workspaceId)
      .then((runs) => {
        if (mounted) {
          // Filter to completed runs or show all
          setBuildRuns(runs);
        }
      })
      .catch(() => {
        // Soft fail if build runs not accessible
      })
      .finally(() => {
        if (mounted) setIsLoadingRuns(false);
      });
    return () => {
      mounted = false;
    };
  }, [isOpen, workspaceId]);

  if (!isOpen) return null;

  const handleSelectBuildRun = (runId: string) => {
    setBuildRunId(runId);
    const selected = buildRuns.find((r) => r.id === runId);
    if (selected) {
      if (selected.recipe_key) setRecipeKey(selected.recipe_key);
      if (selected.dataset_id) setDatasetId(selected.dataset_id);
      if (selected.dataset_version_id) setDatasetVersionId(selected.dataset_version_id);
      const possibleDigest = (selected as unknown as Record<string, unknown>).dataset_version_digest;
      if (typeof possibleDigest === "string") setDatasetVersionDigest(possibleDigest);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!versionTag || !sourceModelKey || !recipeKey) {
      setError("Version tag, source model key, and recipe key are required.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    const payload: CreateModelVersionRequest = {
      version_tag: versionTag.trim(),
      description: description.trim() || undefined,
      source_model_key: sourceModelKey.trim(),
      source_model_revision: sourceModelRevision.trim() || "main",
      recipe_key: recipeKey.trim(),
      build_run_id: buildRunId.trim() || undefined,
      dataset_id: datasetId.trim() || undefined,
      dataset_version_id: datasetVersionId.trim() || undefined,
      dataset_version_digest: datasetVersionDigest.trim() || undefined,
      gate1_approval_id: gate1ApprovalId.trim() || undefined,
      base_evaluation_score: baseScore !== undefined ? Number(baseScore) : undefined,
      final_evaluation_score: finalScore !== undefined ? Number(finalScore) : undefined,
      min_ram_mb: minRamMb ? Number(minRamMb) : undefined,
      min_vram_mb: minVramMb ? Number(minVramMb) : undefined,
      target_hardware_key: targetHardwareKey.trim() || undefined,
    };

    try {
      const version = await createModelVersion(workspaceId, family.id, payload);
      onSuccess(version);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create model version";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-card border border-border rounded-xl shadow-xl w-full max-w-2xl my-8 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between p-5 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <GitBranch className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-foreground">Create Model Version</h3>
              <p className="text-xs text-muted-foreground">
                Family: <span className="font-semibold text-foreground">{family.name}</span> ({family.slug})
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-muted-foreground hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          {/* Quick populate from M10 build run */}
          {buildRuns.length > 0 && (
            <div className="p-3.5 rounded-lg bg-muted/40 border border-border space-y-2">
              <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-primary" />
                Populate from M10 Model Build Run (Optional)
              </label>
              <select
                value={buildRunId}
                onChange={(e) => handleSelectBuildRun(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-xs text-foreground outline-none"
              >
                <option value="">-- Manual Configuration or Select a Build Run --</option>
                {buildRuns.map((r) => (
                  <option key={r.id} value={r.id}>
                    Run {r.id.slice(0, 8)}... | Status: {r.status} | Mode: {r.execution_mode}
                  </option>
                ))}
              </select>
              {isLoadingRuns && <p className="text-[11px] text-muted-foreground">Loading runs...</p>}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">Version Tag *</label>
              <input
                type="text"
                required
                value={versionTag}
                onChange={(e) => setVersionTag(e.target.value)}
                placeholder="v1.0.0"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground focus:ring-1 focus:ring-primary outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">Recipe Key *</label>
              <input
                type="text"
                required
                value={recipeKey}
                onChange={(e) => setRecipeKey(e.target.value)}
                placeholder="LORA_FINETUNE_SFT_V1"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground focus:ring-1 focus:ring-primary outline-none"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Fine-tuned on support tickets with LoRA r=16 alpha=32"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground focus:ring-1 focus:ring-primary outline-none"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">Source Base Model Key *</label>
              <input
                type="text"
                required
                value={sourceModelKey}
                onChange={(e) => setSourceModelKey(e.target.value)}
                placeholder="meta-llama/Llama-3-8B-Instruct"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground focus:ring-1 focus:ring-primary outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">Source Model Revision</label>
              <input
                type="text"
                value={sourceModelRevision}
                onChange={(e) => setSourceModelRevision(e.target.value)}
                placeholder="main or commit sha"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground focus:ring-1 focus:ring-primary outline-none"
              />
            </div>
          </div>

          {/* Dataset & Gate 1 Information */}
          <div className="p-3.5 rounded-lg border border-border space-y-3 bg-muted/20">
            <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-blue-500" />
              Dataset & Provenance Information
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-[11px] text-muted-foreground">Dataset ID</label>
                <input
                  type="text"
                  value={datasetId}
                  onChange={(e) => setDatasetId(e.target.value)}
                  placeholder="Optional dataset ID"
                  className="w-full px-2.5 py-1.5 rounded-md border border-border bg-background text-xs outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[11px] text-muted-foreground">Gate 1 Approval ID</label>
                <input
                  type="text"
                  value={gate1ApprovalId}
                  onChange={(e) => setGate1ApprovalId(e.target.value)}
                  placeholder="Attestation / Approval ID"
                  className="w-full px-2.5 py-1.5 rounded-md border border-border bg-background text-xs outline-none"
                />
              </div>
            </div>
          </div>

          {/* Evaluation & Hardware Specs */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3.5 rounded-lg border border-border space-y-2 bg-muted/20">
              <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                Evaluation Baseline & Target
              </h4>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] text-muted-foreground">Base Score</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    value={baseScore ?? ""}
                    onChange={(e) => setBaseScore(e.target.value ? parseFloat(e.target.value) : undefined)}
                    className="w-full px-2.5 py-1.5 rounded-md border border-border bg-background text-xs outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-muted-foreground">Final Score</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    value={finalScore ?? ""}
                    onChange={(e) => setFinalScore(e.target.value ? parseFloat(e.target.value) : undefined)}
                    className="w-full px-2.5 py-1.5 rounded-md border border-border bg-background text-xs outline-none"
                  />
                </div>
              </div>
            </div>

            <div className="p-3.5 rounded-lg border border-border space-y-2 bg-muted/20">
              <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-emerald-500" />
                Hardware Requirements
              </h4>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] text-muted-foreground">Min RAM (MB)</label>
                  <input
                    type="number"
                    value={minRamMb}
                    onChange={(e) => setMinRamMb(parseInt(e.target.value) || 0)}
                    className="w-full px-2.5 py-1.5 rounded-md border border-border bg-background text-xs outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-muted-foreground">Min VRAM (MB)</label>
                  <input
                    type="number"
                    value={minVramMb}
                    onChange={(e) => setMinVramMb(parseInt(e.target.value) || 0)}
                    className="w-full px-2.5 py-1.5 rounded-md border border-border bg-background text-xs outline-none"
                  />
                </div>
                <div className="col-span-2">
                  <label className="text-[11px] text-muted-foreground">Target Hardware Profile</label>
                  <input
                    type="text"
                    value={targetHardwareKey}
                    onChange={(e) => setTargetHardwareKey(e.target.value)}
                    placeholder="e.g. NVIDIA_T4_16GB"
                    className="w-full px-2.5 py-1.5 rounded-md border border-border bg-background text-xs outline-none"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
            >
              {isSubmitting ? "Creating..." : "Create Draft Version"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
