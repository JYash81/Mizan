import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X, Check, ShieldCheck, AlertCircle } from "lucide-react";
import { recordDecision } from "../api";
import type {
  RecommendationCandidateResponse,
  RecommendationDecisionType,
  RecordDecisionRequest,
} from "../types";

interface HumanDecisionModalProps {
  workspaceId: string;
  runId: string;
  candidates: RecommendationCandidateResponse[];
  selectedCandidate?: RecommendationCandidateResponse | null;
  isOpen: boolean;
  onClose: () => void;
}

export const HumanDecisionModal: React.FC<HumanDecisionModalProps> = ({
  workspaceId,
  runId,
  candidates,
  selectedCandidate,
  isOpen,
  onClose,
}) => {
  const queryClient = useQueryClient();
  const [targetCandidateId, setTargetCandidateId] = useState<string>(
    selectedCandidate?.id || ""
  );
  const [decision, setDecision] = useState<RecommendationDecisionType>(
    "ACCEPTED_FOR_FURTHER_REVIEW"
  );
  const [reason, setReason] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const decisionMutation = useMutation({
    mutationFn: (req: RecordDecisionRequest) => recordDecision(workspaceId, runId, req),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recommendation-run", workspaceId, runId] });
      queryClient.invalidateQueries({ queryKey: ["recommendation-runs", workspaceId] });
      setReason("");
      setErrorMsg(null);
      onClose();
    },
    onError: (err: Error) => {
      setErrorMsg(err.message || "Failed to record human review decision.");
    },
  });

  if (!isOpen) return null;

  const decisionOptions: {
    type: RecommendationDecisionType;
    label: string;
    desc: string;
  }[] = [
    {
      type: "ACCEPTED_FOR_FURTHER_REVIEW",
      label: "Accept for Further Review",
      desc: "Candidate configuration qualifies for offline architecture review. Does not trigger model build or cloud spend.",
    },
    {
      type: "REJECTED",
      label: "Reject Configuration",
      desc: "Candidate fails operational trade-off thresholds or business suitability guidelines.",
    },
    {
      type: "DEFERRED",
      label: "Defer Decision",
      desc: "Postpone decision pending roadmap alignment or stakeholder evaluation.",
    },
    {
      type: "NEEDS_MORE_EVIDENCE",
      label: "Request More Evidence",
      desc: "Candidate requires higher case counts, real hardware benchmarking, or verified cloud pricing.",
    },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim() || reason.trim().length < 5) {
      setErrorMsg("A detailed decision rationale of at least 5 characters is required.");
      return;
    }
    decisionMutation.mutate({
      selected_candidate_id: targetCandidateId || null,
      decision,
      decision_reason: reason.trim(),
    });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl w-full max-w-lg overflow-hidden shadow-2xl my-8">
        <div className="flex items-center justify-between p-6 border-b border-neutral-800">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-500" />
            <h3 className="text-base font-semibold text-neutral-100">
              Record Human Review Decision
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {errorMsg && (
            <div className="p-3 bg-red-950/50 border border-red-800 rounded-lg text-xs text-red-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Candidate Selection */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-neutral-300">
              Target Candidate Configuration (Optional)
            </label>
            <select
              value={targetCandidateId}
              onChange={(e) => setTargetCandidateId(e.target.value)}
              className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-xs text-neutral-100 focus:outline-none focus:border-emerald-500"
            >
              <option value="">Entire Recommendation Run (General Decision)</option>
              {candidates.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.candidate_label} {c.pareto_frontier_member ? "★ [Frontier Optimal]" : ""}
                </option>
              ))}
            </select>
          </div>

          {/* Decision Type Radios */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-neutral-300">Decision Outcome *</label>
            <div className="space-y-2">
              {decisionOptions.map((opt) => (
                <label
                  key={opt.type}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    decision === opt.type
                      ? "border-emerald-700 bg-emerald-950/20"
                      : "border-neutral-800 bg-neutral-950/40 hover:bg-neutral-900/60"
                  }`}
                >
                  <input
                    type="radio"
                    name="decision_type"
                    value={opt.type}
                    checked={decision === opt.type}
                    onChange={() => setDecision(opt.type)}
                    className="mt-0.5 text-emerald-600 focus:ring-emerald-500 border-neutral-700 bg-neutral-900"
                  />
                  <div className="space-y-0.5">
                    <span className="text-xs font-semibold text-neutral-200 block">
                      {opt.label}
                    </span>
                    <span className="text-[11px] text-neutral-400 block">{opt.desc}</span>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Reason / Rationale */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-neutral-300">
              Decision Rationale &amp; Audit Notes *
            </label>
            <textarea
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="State the engineering and business justification for this recommendation decision..."
              className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-xs text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-emerald-500"
              required
            />
          </div>

          {/* Free-Only Policy notice */}
          <div className="p-3 bg-neutral-950/80 border border-neutral-800/80 rounded-lg text-[11px] text-neutral-400">
            <strong>Governance Notice:</strong> Recording acceptance merely updates the evaluation record. It does not provision hardware, deploy models, or trigger billable cloud resources.
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-neutral-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs text-neutral-400 hover:text-neutral-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={decisionMutation.isPending}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors"
            >
              <Check className="w-3.5 h-3.5" />
              {decisionMutation.isPending ? "Recording..." : "Record Decision"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
