import { useState } from "react";
import { FileJson, Copy, Check, Lock, ShieldCheck } from "lucide-react";
import type { ModelVersion } from "../types";

interface ReleaseManifestCardProps {
  version: ModelVersion;
}

export function ReleaseManifestCard({ version }: ReleaseManifestCardProps) {
  const [copied, setCopied] = useState(false);

  const manifest = version.release_manifest || {};
  const digest = version.release_manifest_digest || "PENDING_FINALIZATION";

  const handleCopy = () => {
    navigator.clipboard.writeText(digest);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h3 className="text-lg font-semibold tracking-tight text-foreground flex items-center gap-2">
            <FileJson className="w-5 h-5 text-indigo-500" />
            Canonical Release Manifest & Cryptographic Digest
          </h3>
          <p className="text-sm text-muted-foreground mt-0.5">
            Deterministic, tamper-evident manifest capturing version topology, artifacts, and provenance signatures.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {version.is_immutable && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              <Lock className="w-3.5 h-3.5" />
              Manifest Immutable
            </span>
          )}
        </div>
      </div>

      {/* Manifest Digest Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-3.5 rounded-lg bg-secondary/50 border border-border gap-3">
        <div className="space-y-1">
          <div className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5 uppercase tracking-wider">
            <ShieldCheck className="w-3.5 h-3.5 text-primary" />
            SHA-256 Release Digest
          </div>
          <code className="text-xs font-mono font-bold text-foreground break-all">
            {digest}
          </code>
        </div>
        <button
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-background border border-border text-xs font-medium text-foreground hover:bg-secondary transition-colors shrink-0"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? "Copied" : "Copy Digest"}
        </button>
      </div>

      {/* Manifest JSON Display */}
      <div className="space-y-2">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Manifest JSON Payload
        </div>
        <pre className="p-4 rounded-lg bg-zinc-950 text-zinc-100 font-mono text-xs overflow-x-auto max-h-96 border border-zinc-800 leading-relaxed">
          {JSON.stringify(manifest, null, 2)}
        </pre>
      </div>
    </div>
  );
}
