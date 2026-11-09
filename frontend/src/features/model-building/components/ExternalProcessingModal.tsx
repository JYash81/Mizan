import React, { useState } from "react";
import { ShieldCheck, Lock, X } from "lucide-react";
import { createExternalAuthorization } from "../api";
import type { ExternalAuthorization } from "../types";

interface ExternalProcessingModalProps {
  workspaceId: string;
  datasetId: string;
  datasetVersionId: string;
  isOpen: boolean;
  onClose: () => void;
  onAuthorized: (auth: ExternalAuthorization) => void;
}

export const ExternalProcessingModal: React.FC<ExternalProcessingModalProps> = ({
  workspaceId,
  datasetId,
  datasetVersionId,
  isOpen,
  onClose,
  onAuthorized,
}) => {
  const [purpose, setPurpose] = useState(
    "LoRA / QLoRA adapter training in Google Colab Free ephemeral runtime"
  );
  const [validHours, setValidHours] = useState(24);
  const [confirmed, setConfirmed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!confirmed) return;
    setError(null);
    setIsLoading(true);

    try {
      const auth = await createExternalAuthorization(workspaceId, {
        dataset_id: datasetId,
        dataset_version_id: datasetVersionId,
        purpose,
        valid_hours: validHours,
      });
      onAuthorized(auth);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create external processing authorization";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-xl p-6 shadow-2xl space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-amber-400" />
            <h3 className="text-base font-bold text-slate-100">
              External Processing Authorization
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="rounded-md border border-amber-500/30 bg-amber-950/20 p-3.5 text-xs text-amber-200/90 space-y-1.5">
          <div className="flex items-center gap-1.5 font-semibold text-amber-300">
            <Lock className="h-4 w-4" />
            Strict Sensitive Data Boundary
          </div>
          <p>
            Exporting training data to external Colab runtimes requires explicit human authorization.
            Only <strong>Gate 1 approved, masked documents</strong> may be exported. Unmasked or
            raw documents are strictly forbidden and blocked server-side.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded bg-rose-950/30 border border-rose-500/30 p-2.5 text-xs text-rose-300">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Processing Purpose
            </label>
            <input
              type="text"
              required
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-100"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Authorization Validity Window
            </label>
            <select
              value={validHours}
              onChange={(e) => setValidHours(Number(e.target.value))}
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-100"
            >
              <option value={12}>12 Hours</option>
              <option value={24}>24 Hours (Standard)</option>
              <option value={48}>48 Hours</option>
              <option value={72}>72 Hours (Extended)</option>
            </select>
          </div>

          <div className="rounded-md border border-slate-800 bg-slate-950 p-3 space-y-2">
            <div className="text-[11px] text-slate-400">
              Target Runtime:{" "}
              <span className="font-mono text-slate-200">GOOGLE_COLAB_EPHEMERAL_RUNTIME</span>
            </div>
            <div className="text-[11px] text-slate-400">
              Dataset Version: <span className="font-mono text-slate-200">{datasetVersionId}</span>
            </div>
          </div>

          <label className="flex items-start gap-2 text-xs text-slate-300 cursor-pointer pt-1">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
              className="mt-0.5 rounded border-slate-700 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
            />
            <span>
              I authorize the export of this Gate 1 approved masked dataset strictly for external
              model fine-tuning.
            </span>
          </label>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded-md text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!confirmed || isLoading}
              data-testid="confirm-external-auth-btn"
              className="px-4 py-1.5 rounded-md text-xs font-semibold bg-amber-600 hover:bg-amber-500 text-white transition-colors disabled:opacity-50"
            >
              {isLoading ? "Authorizing..." : "Authorize External Export"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
