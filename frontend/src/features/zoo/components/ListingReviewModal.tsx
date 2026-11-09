import { useState } from "react";
import { AlertCircle, CheckCircle, ShieldCheck, X, XCircle } from "lucide-react";
import { reviewAppListing, reviewModelListing } from "../api";

interface ListingReviewModalProps {
  workspaceId: string;
  listingId: string;
  listingType: "MODEL" | "APP";
  listingTitle: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function ListingReviewModal({
  workspaceId,
  listingId,
  listingType,
  listingTitle,
  isOpen,
  onClose,
  onSuccess,
}: ListingReviewModalProps) {
  const [decision, setDecision] = useState<"APPROVED" | "REJECTED">("APPROVED");
  const [rationale, setRationale] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rationale.trim() || rationale.trim().length < 5) {
      setError("Please provide a meaningful review rationale (minimum 5 characters).");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      if (listingType === "MODEL") {
        await reviewModelListing(workspaceId, listingId, {
          decision,
          rationale: rationale.trim(),
        });
      } else {
        await reviewAppListing(workspaceId, listingId, {
          decision,
          rationale: rationale.trim(),
        });
      }

      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Review submission failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-md rounded-lg border bg-card text-card-foreground shadow-lg my-8 p-6">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 text-muted-foreground hover:text-foreground"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 mb-1">
          <ShieldCheck className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold tracking-tight">Catalog Moderation Review</h2>
        </div>
        <p className="text-xs text-muted-foreground mb-4">
          Review and decide publication for <strong className="text-foreground">{listingTitle}</strong>.
        </p>

        {error && (
          <div className="p-3 mb-4 rounded-md bg-destructive/10 text-destructive text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-foreground block mb-2">Review Decision</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setDecision("APPROVED")}
                className={`p-3 rounded-md border text-xs font-medium flex items-center justify-center gap-2 transition-all ${
                  decision === "APPROVED"
                    ? "bg-emerald-50 text-emerald-700 border-emerald-400 dark:bg-emerald-950/40 dark:text-emerald-300"
                    : "border-border hover:bg-muted"
                }`}
              >
                <CheckCircle className="w-4 h-4" />
                <span>Approve & Publish</span>
              </button>
              <button
                type="button"
                onClick={() => setDecision("REJECTED")}
                className={`p-3 rounded-md border text-xs font-medium flex items-center justify-center gap-2 transition-all ${
                  decision === "REJECTED"
                    ? "bg-rose-50 text-rose-700 border-rose-400 dark:bg-rose-950/40 dark:text-rose-300"
                    : "border-border hover:bg-muted"
                }`}
              >
                <XCircle className="w-4 h-4" />
                <span>Reject</span>
              </button>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">
              Review Rationale & Governance Notes *
            </label>
            <textarea
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              rows={3}
              placeholder="State reason for publication approval or remediation guidance for rejection..."
              className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
              required
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs font-medium rounded-md border hover:bg-muted"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-1.5 text-xs font-semibold rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {isSubmitting ? "Submitting..." : "Submit Review"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
