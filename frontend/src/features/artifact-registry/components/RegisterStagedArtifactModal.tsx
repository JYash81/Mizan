import { useState, useEffect } from "react";
import { X, PackagePlus } from "lucide-react";
import { registerStagedArtifact } from "../api";
import { fetchBuildRuns } from "../../model-building/api";
import type { ModelVersion, RegisteredArtifact } from "../types";
import type { ModelBuildRun, StagedArtifact } from "../../model-building/types";

interface RegisterStagedArtifactModalProps {
  workspaceId: string;
  version: ModelVersion;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (artifact: RegisteredArtifact) => void;
}

export function RegisterStagedArtifactModal({
  workspaceId,
  version,
  isOpen,
  onClose,
  onSuccess,
}: RegisterStagedArtifactModalProps) {
  const [stagedArtifactId, setStagedArtifactId] = useState("");
  const [isPrimaryWeights, setIsPrimaryWeights] = useState(true);
  const [availableArtifacts, setAvailableArtifacts] = useState<
    Array<{ staged: StagedArtifact; runId: string }>
  >([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    let mounted = true;
    setIsLoading(true);
    fetchBuildRuns(workspaceId)
      .then((runs: ModelBuildRun[]) => {
        if (!mounted) return;
        const allStaged: Array<{ staged: StagedArtifact; runId: string }> = [];
        runs.forEach((run) => {
          if (run.staged_artifacts && run.staged_artifacts.length > 0) {
            run.staged_artifacts.forEach((sa) => {
              allStaged.push({ staged: sa, runId: run.id });
            });
          }
        });
        setAvailableArtifacts(allStaged);
        if (allStaged.length > 0 && !stagedArtifactId) {
          setStagedArtifactId(allStaged[0].staged.id);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (mounted) setIsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [isOpen, workspaceId, stagedArtifactId]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stagedArtifactId.trim()) {
      setError("Please select or enter a staged artifact ID.");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const registered = await registerStagedArtifact(workspaceId, version.id, {
        staged_artifact_id: stagedArtifactId.trim(),
        is_primary_weights: isPrimaryWeights,
      });
      onSuccess(registered);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to register artifact";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
      <div className="bg-card border border-border rounded-xl shadow-xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between p-5 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <PackagePlus className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-foreground">Register Staged Artifact</h3>
              <p className="text-xs text-muted-foreground">
                Attach M10 validated artifact to {version.version_tag}
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

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          {isLoading && (
            <p className="text-[11px] text-muted-foreground animate-pulse">Loading staged artifacts...</p>
          )}

          {availableArtifacts.length > 0 && (
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">
                Select from M10 Staged Artifacts
              </label>
              <select
                value={stagedArtifactId}
                onChange={(e) => setStagedArtifactId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-xs text-foreground outline-none"
              >
                {availableArtifacts.map(({ staged, runId }) => (
                  <option key={staged.id} value={staged.id}>
                    {staged.artifact_type} ({staged.format}) — Run {runId.slice(0, 8)}... | Status:{" "}
                    {staged.verification_status}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">Staged Artifact ID *</label>
            <input
              type="text"
              required
              value={stagedArtifactId}
              onChange={(e) => setStagedArtifactId(e.target.value)}
              placeholder="e.g. sta_12345678"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground focus:ring-1 focus:ring-primary outline-none"
            />
            <p className="text-[11px] text-muted-foreground">
              Must be a valid, verified StagedModelArtifact created during M10 build runs.
            </p>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="is_primary_weights"
              checked={isPrimaryWeights}
              onChange={(e) => setIsPrimaryWeights(e.target.checked)}
              className="rounded border-border text-primary focus:ring-primary h-4 w-4"
            />
            <label htmlFor="is_primary_weights" className="text-xs font-medium text-foreground cursor-pointer">
              Set as primary model weights (e.g., fine-tuned weights or primary adapter)
            </label>
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
              disabled={isSubmitting || !stagedArtifactId}
              className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 rounded-lg shadow-sm transition-colors"
            >
              {isSubmitting ? "Registering..." : "Register Artifact"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
