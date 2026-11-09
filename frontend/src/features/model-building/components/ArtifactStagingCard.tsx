import React from "react";
import {
  FileCheck2,
  FileWarning,
  Copy,
  Check,
  ShieldAlert,
  Package,
} from "lucide-react";
import type { StagedArtifact } from "../types";

interface ArtifactStagingCardProps {
  artifacts: StagedArtifact[];
}

export const ArtifactStagingCard: React.FC<ArtifactStagingCardProps> = ({ artifacts }) => {
  const [copiedHash, setCopiedHash] = React.useState<string | null>(null);

  const handleCopy = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  if (!artifacts || artifacts.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/30 p-8 text-center text-slate-400">
        <Package className="mx-auto h-8 w-8 text-slate-500 mb-2" />
        <p className="text-sm font-medium">No staged model artifacts yet</p>
        <p className="text-xs text-slate-500 mt-1">
          Complete a local smoke test or import Colab notebook artifacts to stage models for evaluation.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-amber-500/30 bg-amber-950/20 p-3 text-xs text-amber-200/90 flex items-start gap-2">
        <ShieldAlert className="h-4 w-4 text-amber-400 mt-0.5 shrink-0" />
        <div>
          <span className="font-semibold text-amber-300">Milestone Boundary Notice:</span> Staged
          artifacts are validated build outputs stored for internal testing and M6 evaluation. They
          are <span className="underline">NOT</span> release artifacts and do not constitute Gate 3
          release authorization (owned by Milestone 11).
        </div>
      </div>

      <div className="grid gap-3">
        {artifacts.map((art) => {
          const isVerified = art.verification_status === "VERIFIED";
          const formattedSize =
            art.file_size_bytes < 1024 * 1024
              ? `${(art.file_size_bytes / 1024).toFixed(1)} KB`
              : `${(art.file_size_bytes / (1024 * 1024)).toFixed(1)} MB`;

          return (
            <div
              key={art.id}
              data-testid="staged-artifact-card"
              className="rounded-lg border border-slate-700 bg-slate-800/80 p-4 hover:border-slate-600 transition-colors"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700/80 pb-3 mb-3">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    {art.artifact_type}
                  </span>
                  <span className="px-2 py-0.5 rounded text-xs font-mono bg-slate-900 text-slate-300 border border-slate-700">
                    {art.format}
                    {art.quantization_type ? ` · ${art.quantization_type}` : ""}
                  </span>
                  <span className="text-xs text-slate-400 font-medium">
                    {formattedSize}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {isVerified ? (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      <FileCheck2 className="h-3.5 w-3.5" />
                      Verified
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                      <FileWarning className="h-3.5 w-3.5" />
                      {art.verification_status}
                    </span>
                  )}
                  <span className="text-xs px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20">
                    Staged for M11
                  </span>
                </div>
              </div>

              {/* Provenance Details */}
              <div className="space-y-1.5 text-xs">
                <div className="flex items-center justify-between text-slate-400">
                  <span>Source Model:</span>
                  <span className="font-mono text-slate-200">
                    {art.source_model_key} (@{art.source_model_revision.slice(0, 8)})
                  </span>
                </div>

                <div className="flex items-center justify-between text-slate-400">
                  <span>Storage Reference:</span>
                  <span className="font-mono text-slate-300 truncate max-w-md">
                    {art.storage_reference}
                  </span>
                </div>

                <div className="flex items-center justify-between text-slate-400 pt-1">
                  <span>SHA-256 Checksum:</span>
                  <div className="flex items-center gap-1 font-mono text-slate-300">
                    <span>{art.sha256.slice(0, 16)}...{art.sha256.slice(-8)}</span>
                    <button
                      onClick={() => handleCopy(art.sha256)}
                      className="p-1 hover:text-slate-100 transition-colors text-slate-500"
                      title="Copy full SHA-256"
                    >
                      {copiedHash === art.sha256 ? (
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between text-slate-400">
                  <span>Manifest Digest:</span>
                  <span className="font-mono text-slate-400">{art.manifest_digest.slice(0, 16)}...</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
