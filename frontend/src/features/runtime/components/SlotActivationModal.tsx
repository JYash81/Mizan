import React, { useState } from "react";
import { ArrowUpRight, AlertTriangle } from "lucide-react";
import type { RuntimeSlot } from "../types";

interface SlotActivationModalProps {
  slot: RuntimeSlot | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (slot: RuntimeSlot, reason: string) => Promise<void>;
}

export const SlotActivationModal: React.FC<SlotActivationModalProps> = ({
  slot,
  isOpen,
  onClose,
  onConfirm,
}) => {
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !slot) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError("Please provide a reason for promoting this slot.");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await onConfirm(slot, reason);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to promote slot.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-card border border-border rounded-xl shadow-xl w-full max-w-md p-6 overflow-hidden">
        <div className="flex items-center justify-between pb-3 border-b border-border">
          <div className="flex items-center gap-2 text-foreground font-semibold">
            <ArrowUpRight className="w-5 h-5 text-primary" />
            <span>Promote Slot to Active Traffic</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground text-sm font-medium"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="py-4 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="text-xs text-muted-foreground space-y-1">
            <p>
              Target Slot: <span className="font-semibold text-foreground">{slot.slot_name}</span>
            </p>
            <p>
              Model Version: <span className="font-mono text-foreground">{slot.model_version_id}</span>
            </p>
            <p>
              Golden Tests Status:{" "}
              <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                {slot.golden_test_status}
              </span>
            </p>
          </div>

          <div>
            <label className="text-xs font-medium text-foreground block mb-1">
              Promotion Reason & Authorization Notes <span className="text-red-500">*</span>
            </label>
            <textarea
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Passed all acceptance tests; rolling out v1.1.0 update to support staff."
              required
              className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="pt-3 border-t border-border flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-medium rounded-lg border border-input bg-background hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !reason.trim()}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {isSubmitting ? "Promoting Slot..." : "Confirm & Promote"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
