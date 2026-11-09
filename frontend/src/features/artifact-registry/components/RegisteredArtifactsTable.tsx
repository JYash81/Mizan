import { useState } from "react";
import { Package, CheckCircle2, Star, Copy, Check, FileArchive, Plus } from "lucide-react";
import type { RegisteredArtifact } from "../types";

interface RegisteredArtifactsTableProps {
  artifacts: RegisteredArtifact[];
  isDraft?: boolean;
  onRegisterArtifact?: () => void;
}

export function RegisteredArtifactsTable({
  artifacts,
  isDraft,
  onRegisterArtifact,
}: RegisteredArtifactsTableProps) {
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const handleCopy = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const formatSize = (bytes: number) => {
    if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${bytes} B`;
  };

  return (
    <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden space-y-4 p-6">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <h3 className="text-lg font-semibold tracking-tight text-foreground flex items-center gap-2">
            <Package className="w-5 h-5 text-primary" />
            Registered Model Artifacts ({artifacts.length})
          </h3>
          <p className="text-sm text-muted-foreground mt-0.5">
            Immutable binaries, LoRA adapters, quantized GGUF/AWQ packages, and tokenizers.
          </p>
        </div>
        {isDraft && onRegisterArtifact && (
          <button
            onClick={onRegisterArtifact}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            Register Staged Artifact
          </button>
        )}
      </div>

      {artifacts.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-border rounded-lg">
          <FileArchive className="w-10 h-10 mx-auto text-muted-foreground/60 mb-2" />
          <h4 className="text-sm font-semibold text-foreground">No Registered Artifacts</h4>
          <p className="text-xs text-muted-foreground mt-1">
            Promote an M10 staged artifact or register model weights to populate this version.
          </p>
          {isDraft && onRegisterArtifact && (
            <button
              onClick={onRegisterArtifact}
              className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              Register First Artifact
            </button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto border border-border rounded-lg">
          <table className="w-full text-left text-sm">
            <thead className="bg-secondary/50 text-xs font-semibold text-muted-foreground uppercase border-b border-border">
              <tr>
                <th className="py-3 px-4">Artifact Type</th>
                <th className="py-3 px-4">Format</th>
                <th className="py-3 px-4">Size</th>
                <th className="py-3 px-4">SHA-256 Checksum</th>
                <th className="py-3 px-4">Integrity</th>
                <th className="py-3 px-4">Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {artifacts.map((art) => (
                <tr key={art.id} className="hover:bg-secondary/20 transition-colors">
                  <td className="py-3 px-4">
                    <div className="font-medium text-foreground">{art.artifact_type}</div>
                    {art.quantization_type && (
                      <span className="text-xs text-muted-foreground">Quant: {art.quantization_type}</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-secondary text-foreground">
                      {art.format}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono text-xs text-muted-foreground">
                    {formatSize(art.file_size_bytes)}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-1.5">
                      <code className="text-xs font-mono text-foreground" title={art.sha256}>
                        {art.sha256.slice(0, 12)}...{art.sha256.slice(-8)}
                      </code>
                      <button
                        onClick={() => handleCopy(art.sha256)}
                        className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                        title="Copy SHA-256"
                      >
                        {copiedHash === art.sha256 ? (
                          <Check className="w-3.5 h-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Verified
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    {art.is_primary_weights ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                        <Star className="w-3 h-3 fill-amber-500" />
                        Primary Weights
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">Secondary</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
