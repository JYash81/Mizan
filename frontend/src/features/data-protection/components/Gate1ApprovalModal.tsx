import { useState, type FormEvent } from "react";
import { AlertTriangle, CheckCircle, Fingerprint, Key, ShieldCheck, X } from "lucide-react";

import type { MaskingRun } from "../types";

interface Gate1ApprovalModalProps {
  run: MaskingRun;
  isOpen: boolean;
  onClose: () => void;
  onApprove: (data: { decision_reason: string; override_coverage_reason?: string }) => Promise<void>;
  onReject: (data: { decision_reason: string }) => Promise<void>;
  isSubmitting: boolean;
}

export function Gate1ApprovalModal({
  run,
  isOpen,
  onClose,
  onApprove,
  onReject,
  isSubmitting,
}: Gate1ApprovalModalProps) {
  const [reason, setReason] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [confirmedReview, setConfirmedReview] = useState(false);
  const [actionType, setActionType] = useState<"approve" | "reject">("approve");
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const needsOcrOverride =
    run.extraction_coverage === "OCR_REQUIRED" ||
    run.extraction_coverage === "EXTRACTION_FAILED";

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      if (actionType === "approve") {
        if (!confirmedReview) {
          setError("You must confirm that you have reviewed the detected sensitive entities.");
          return;
        }
        if (needsOcrOverride && !overrideReason.trim()) {
          setError(
            "Extraction coverage requires OCR or manual verification. Please provide an explicit override justification."
          );
          return;
        }
        await onApprove({
          decision_reason: reason.trim() || "Approved by authorized human reviewer.",
          override_coverage_reason: needsOcrOverride ? overrideReason.trim() : undefined,
        });
      } else {
        if (!reason.trim()) {
          setError("A rejection reason is required.");
          return;
        }
        await onReject({ decision_reason: reason.trim() });
      }
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to process Gate 1 decision.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-2xl w-full shadow-2xl overflow-hidden text-slate-100 flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold tracking-tight text-white">
                Gate 1 — Human Data Protection Approval
              </h2>
              <p className="text-xs text-slate-400">
                Step 3 Checkpoint: Authorize masked dataset for AI experimentation
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors p-1 rounded-md"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-5">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-sm flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Cryptographic Attestation Notice */}
          <div className="p-4 bg-sky-950/30 border border-sky-800/40 rounded-lg text-xs space-y-2 text-sky-200">
            <div className="flex items-center gap-2 font-medium text-sky-300">
              <Fingerprint className="w-4 h-4" />
              <span>Immutable Ed25519 Platform Attestation</span>
            </div>
            <p className="text-slate-300 leading-relaxed">
              In accordance with the Mizan Data Protection Invariant, raw business data never leaves the Workshop Data Plane.
              Executing approval generates a canonical, platform-signed cryptographic attestation linking this exact dataset version,
              its findings, and its masked digest. External AI models cannot be called without this signature.
            </p>
          </div>

          {/* Digest Matrix */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div className="bg-slate-950/40 border border-slate-800 rounded-lg p-3">
              <div className="text-slate-400 font-mono mb-1 flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-slate-500" />
                Source Dataset Digest
              </div>
              <div className="font-mono text-slate-300 truncate" title={run.source_dataset_digest}>
                {run.source_dataset_digest || "Pending computation"}
              </div>
            </div>

            <div className="bg-slate-950/40 border border-slate-800 rounded-lg p-3">
              <div className="text-slate-400 font-mono mb-1 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                Masked Output Digest
              </div>
              <div className="font-mono text-emerald-300 truncate" title={run.masked_output_digest || ""}>
                {run.masked_output_digest || "Pending generation"}
              </div>
            </div>
          </div>

          {/* OCR & Coverage Guard */}
          {needsOcrOverride && (
            <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg space-y-2">
              <div className="flex items-center gap-2 text-amber-300 font-medium text-xs">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>Coverage Warning: {run.extraction_coverage}</span>
              </div>
              <p className="text-xs text-amber-200/80 leading-relaxed">
                One or more documents require OCR or could not be fully extracted. Per Mizan safety policy,
                an explicit justification is required to confirm that unextracted documents contain no personal data.
              </p>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Exclusion Justification <span className="text-rose-400">*</span>
                </label>
                <textarea
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="e.g. Scanned document visually inspected and verified to contain only blank boilerplate text."
                  className="w-full bg-slate-950/60 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 h-20"
                />
              </div>
            </div>
          )}

          {/* Reason Field */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Reviewer Notes / Decision Reason
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. All UAE Emirates IDs, IBANs, and employee contacts verified and masked."
              className="w-full bg-slate-950/60 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 h-20"
            />
          </div>

          {/* Confirmation Checkbox */}
          <label className="flex items-start gap-3 p-3 bg-slate-950/30 border border-slate-800 rounded-lg cursor-pointer hover:bg-slate-950/50 transition-colors">
            <input
              type="checkbox"
              checked={confirmedReview}
              onChange={(e) => setConfirmedReview(e.target.checked)}
              className="mt-0.5 rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-emerald-500 h-4 w-4"
            />
            <span className="text-xs text-slate-300 leading-relaxed">
              I certify as an authorized human reviewer that I have inspected the detections,
              reviewed the masked preview, and authorize this dataset version to proceed to Gate 1 approved status.
            </span>
          </label>

          {/* Modal Actions */}
          <div className="flex items-center justify-between pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={() => {
                setActionType("reject");
                handleSubmit({ preventDefault: () => {} } as FormEvent);
              }}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg text-xs font-medium bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 transition-colors disabled:opacity-50"
            >
              Reject Dataset
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                onClick={() => setActionType("approve")}
                disabled={isSubmitting || !confirmedReview}
                className="px-4 py-2 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center gap-1.5 disabled:opacity-50 shadow-lg shadow-emerald-950/50"
              >
                <CheckCircle className="w-4 h-4" />
                {isSubmitting ? "Signing Attestation..." : "Sign & Approve Gate 1"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
