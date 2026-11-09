import React, { useState } from "react";
import {
  Download,
  Upload,
  FileCode,
  ShieldCheck,
  CheckCircle2,
  ExternalLink,
  Info,
  X,
} from "lucide-react";
import type { ModelBuildRun, ColabResultImportRequest, ArtifactType } from "../types";
import { downloadColabNotebook, importColabResult } from "../api";

interface ColabExportDrawerProps {
  run: ModelBuildRun;
  isOpen: boolean;
  onClose: () => void;
  onImportSuccess: () => void;
}

export const ColabExportDrawer: React.FC<ColabExportDrawerProps> = ({
  run,
  isOpen,
  onClose,
  onImportSuccess,
}) => {
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState(false);

  // Import Form State
  const [outputFormat, setOutputFormat] = useState("SAFETENSORS");
  const [artifactType, setArtifactType] = useState<ArtifactType>("LORA_ADAPTER");
  const [sha256, setSha256] = useState("");
  const [fileSizeBytes, setFileSizeBytes] = useState<number>(1048576);
  const [quantizationType, setQuantizationType] = useState("Q4_K_M");

  if (!isOpen) return null;

  const handleDownloadNotebook = async () => {
    setIsExporting(true);
    try {
      const nb = await downloadColabNotebook(run.workspace_id, run.id);
      const blob = new Blob([JSON.stringify(nb, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `mizan_${run.recipe_key.toLowerCase()}_${run.id.slice(0, 8)}.ipynb`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Network error";
      alert(`Export failed: ${msg}`);
    } finally {
      setIsExporting(false);
    }
  };

  const handleDownloadManifest = () => {
    const blob = new Blob([JSON.stringify(run.build_manifest, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `manifest_${run.manifest_digest.slice(0, 12)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleImportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setImportError(null);
    setIsImporting(true);

    if (!sha256 || sha256.length !== 64) {
      setImportError("Valid 64-character SHA-256 hash is required.");
      setIsImporting(false);
      return;
    }

    try {
      const payload: ColabResultImportRequest = {
        manifest_digest: run.manifest_digest,
        output_format: outputFormat,
        artifact_type: artifactType,
        file_size_bytes: fileSizeBytes,
        sha256: sha256.trim().toLowerCase(),
        quantization_type: outputFormat === "GGUF" ? quantizationType : undefined,
        execution_report: {
          imported_at: new Date().toISOString(),
          runtime_environment: "GOOGLE_COLAB_FREE_T4",
        },
      };

      await importColabResult(run.workspace_id, run.id, payload);
      setImportSuccess(true);
      setTimeout(() => {
        onImportSuccess();
        onClose();
      }, 1500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to import result artifact";
      setImportError(msg);
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/70 backdrop-blur-sm flex justify-end">
      <div className="w-full max-w-2xl bg-slate-900 border-l border-slate-700 h-full overflow-y-auto p-6 flex flex-col justify-between shadow-2xl">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-700 pb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <FileCode className="h-5 w-5 text-indigo-400" />
                Google Colab Free Lab
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Run reproducible fine-tuning or quantization in Colab Free with $0.00 spend.
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Infrastructure Notice */}
          <div className="rounded-md border border-emerald-500/30 bg-emerald-950/20 p-3.5 text-xs text-emerald-200/90 flex items-start gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400 mt-0.5 shrink-0" />
            <div>
              <span className="font-semibold text-emerald-300">Free-Only Infrastructure Model:</span>{" "}
              Mizan exports self-contained Jupyter notebooks with locked dependencies and integrity
              verification. Run directly in Google Colab's free T4 GPU tier without adding cloud credentials.
            </div>
          </div>

          {/* Downloads Card */}
          <div className="rounded-lg border border-slate-700 bg-slate-800/80 p-4 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              1. Download Artifacts for Colab
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                onClick={handleDownloadNotebook}
                disabled={isExporting}
                data-testid="download-colab-notebook-btn"
                className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-md text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-50"
              >
                <Download className="h-4 w-4" />
                {isExporting ? "Exporting..." : "Download .ipynb Notebook"}
              </button>

              <button
                onClick={handleDownloadManifest}
                data-testid="download-manifest-btn"
                className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-md text-xs font-medium bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors"
              >
                <Download className="h-4 w-4" />
                Download build_manifest.json
              </button>
            </div>

            <div className="text-[11px] text-slate-400 flex items-center gap-1.5 pt-1">
              <Info className="h-3.5 w-3.5 text-slate-400" />
              <span>
                Manifest Digest: <code className="font-mono text-slate-300">{run.manifest_digest.slice(0, 16)}...</code>
              </span>
            </div>
          </div>

          {/* Execution Steps */}
          <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 space-y-2.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              2. Manual Execution Instructions
            </h3>
            <ol className="list-decimal list-inside space-y-1.5 text-xs text-slate-300">
              <li>Open <a href="https://colab.research.google.com" target="_blank" rel="noreferrer" className="text-blue-400 hover:underline inline-flex items-center gap-0.5">Google Colab <ExternalLink className="h-3 w-3" /></a> in your browser.</li>
              <li>Upload the downloaded <code className="font-mono text-indigo-300">.ipynb</code> notebook.</li>
              <li>Select <strong>Runtime → Change runtime type → T4 GPU</strong>.</li>
              <li>Run the cells sequentially. The notebook will automatically verify the manifest digest and generate checkpoints.</li>
              <li>At completion, download the output artifact and note its SHA-256 checksum.</li>
            </ol>
          </div>

          {/* Result Import Form */}
          <div className="rounded-lg border border-slate-700 bg-slate-800/80 p-4 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
              <Upload className="h-3.5 w-3.5 text-blue-400" />
              3. Import Staged Artifact
            </h3>

            {importSuccess ? (
              <div className="rounded bg-emerald-950/40 border border-emerald-500/40 p-3 text-center text-xs text-emerald-300 flex items-center justify-center gap-2">
                <CheckCircle2 className="h-4 w-4" />
                Artifact staged successfully! Refreshing...
              </div>
            ) : (
              <form onSubmit={handleImportSubmit} className="space-y-3">
                {importError && (
                  <div className="rounded bg-rose-950/30 border border-rose-500/30 p-2.5 text-xs text-rose-300">
                    {importError}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-medium text-slate-400 mb-1">
                      Artifact Type
                    </label>
                    <select
                      value={artifactType}
                      onChange={(e) => setArtifactType(e.target.value as ArtifactType)}
                      className="w-full rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-200"
                    >
                      <option value="LORA_ADAPTER">LoRA Adapter</option>
                      <option value="MERGED_MODEL">Merged Model</option>
                      <option value="GGUF_QUANTIZED">GGUF Quantized</option>
                      <option value="AWQ_QUANTIZED">AWQ Quantized</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-slate-400 mb-1">
                      Format
                    </label>
                    <select
                      value={outputFormat}
                      onChange={(e) => setOutputFormat(e.target.value)}
                      className="w-full rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-200"
                    >
                      <option value="SAFETENSORS">safetensors</option>
                      <option value="GGUF">GGUF</option>
                      <option value="AWQ">AWQ</option>
                    </select>
                  </div>
                </div>

                {outputFormat === "GGUF" && (
                  <div>
                    <label className="block text-[11px] font-medium text-slate-400 mb-1">
                      Quantization Tier
                    </label>
                    <select
                      value={quantizationType}
                      onChange={(e) => setQuantizationType(e.target.value)}
                      className="w-full rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-200"
                    >
                      <option value="Q4_K_M">Q4_K_M (Balanced 4-bit)</option>
                      <option value="Q8_0">Q8_0 (High Quality 8-bit)</option>
                      <option value="FP16">FP16 (Half Precision)</option>
                    </select>
                  </div>
                )}

                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">
                    SHA-256 Checksum (64 Hex Characters)
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
                    value={sha256}
                    onChange={(e) => setSha256(e.target.value)}
                    className="w-full rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-200 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">
                    File Size (Bytes)
                  </label>
                  <input
                    type="number"
                    required
                    min={1}
                    value={fileSizeBytes}
                    onChange={(e) => setFileSizeBytes(Number(e.target.value))}
                    className="w-full rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-200"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isImporting}
                  data-testid="submit-colab-import-btn"
                  className="w-full py-2 px-4 rounded-md text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors disabled:opacity-50 mt-2"
                >
                  {isImporting ? "Staging Artifact..." : "Stage Artifact for Review"}
                </button>
              </form>
            )}
          </div>
        </div>

        <div className="border-t border-slate-800 pt-4 mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-md text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
