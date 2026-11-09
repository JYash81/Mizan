import React from "react";
import { Star, XCircle, Info } from "lucide-react";
import type { RecommendationCandidateResponse } from "../types";

interface CandidateExplanationCardProps {
  candidate: RecommendationCandidateResponse;
  onSelectForDecision?: (candidate: RecommendationCandidateResponse) => void;
}

export const CandidateExplanationCard: React.FC<CandidateExplanationCardProps> = ({
  candidate,
  onSelectForDecision,
}) => {
  const isFrontier = candidate.pareto_frontier_member;
  const isEligible = candidate.eligibility_status === "ELIGIBLE";
  const raw = candidate.objective_values;
  const ev = candidate.evidence_summary;

  return (
    <div
      className={`border rounded-xl p-5 space-y-4 transition-all ${
        isFrontier
          ? "border-emerald-800/80 bg-emerald-950/10 shadow-sm"
          : "border-neutral-800 bg-neutral-950/40"
      }`}
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-neutral-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="text-base font-semibold text-neutral-100">
              {candidate.candidate_label}
            </h4>
            {isFrontier && (
              <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-medium">
                <Star className="w-3 h-3 fill-emerald-400" /> Optimal Frontier Member
              </span>
            )}
            {!isEligible && (
              <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-red-950 text-red-400 border border-red-800 font-medium">
                <XCircle className="w-3 h-3" /> {candidate.eligibility_status}
              </span>
            )}
          </div>
          <p className="text-[11px] text-neutral-500 font-mono mt-0.5">
            Digest: {candidate.configuration_digest}
          </p>
        </div>

        {onSelectForDecision && (
          <button
            type="button"
            onClick={() => onSelectForDecision(candidate)}
            className="px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-medium rounded-lg border border-neutral-700 transition-colors shrink-0"
          >
            Record Decision for Candidate
          </button>
        )}
      </div>

      {/* Explanation Text */}
      <div className="p-3.5 bg-neutral-900/80 border border-neutral-800 rounded-lg space-y-1">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-neutral-300">
          <Info className="w-3.5 h-3.5 text-emerald-500" />
          <span>Deterministic Trade-Off Analysis</span>
        </div>
        <p className="text-xs text-neutral-200 leading-relaxed">
          {candidate.explanation_text || "No explanation synthesized."}
        </p>
        {candidate.exclusion_reasons.length > 0 && (
          <div className="pt-2 border-t border-neutral-800">
            <span className="text-xs font-medium text-red-400 block mb-1">
              Constraint Exclusions:
            </span>
            <ul className="list-disc list-inside text-xs text-red-300 space-y-0.5">
              {candidate.exclusion_reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Metric Breakdown with Provenance Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="p-3 bg-neutral-900/50 border border-neutral-800/80 rounded-lg space-y-1">
          <div className="flex items-center justify-between text-neutral-400">
            <span>Quality Score</span>
            <span className="text-[9px] px-1 bg-neutral-800 text-neutral-400 rounded">
              {ev.aggregate_score || "MEASURED"}
            </span>
          </div>
          <span className="text-base font-bold text-neutral-100 font-mono block">
            {raw.aggregate_score !== undefined ? `${Number(raw.aggregate_score).toFixed(1)} pts` : "-"}
          </span>
        </div>

        <div className="p-3 bg-neutral-900/50 border border-neutral-800/80 rounded-lg space-y-1">
          <div className="flex items-center justify-between text-neutral-400">
            <span>P95 Latency</span>
            <span className="text-[9px] px-1 bg-neutral-800 text-neutral-400 rounded">
              {ev.latency_p95_ms || "MEASURED"}
            </span>
          </div>
          <span className="text-base font-bold text-neutral-100 font-mono block">
            {raw.latency_p95_ms !== undefined ? `${Number(raw.latency_p95_ms).toFixed(1)} ms` : "-"}
          </span>
        </div>

        <div className="p-3 bg-neutral-900/50 border border-neutral-800/80 rounded-lg space-y-1">
          <div className="flex items-center justify-between text-neutral-400">
            <span>Peak RAM</span>
            <span className="text-[9px] px-1 bg-neutral-800 text-neutral-400 rounded">
              {ev.required_ram_mb || "ESTIMATED"}
            </span>
          </div>
          <span className="text-base font-bold text-neutral-100 font-mono block">
            {raw.required_ram_mb !== undefined ? `${Number(raw.required_ram_mb).toFixed(0)} MB` : "-"}
          </span>
        </div>

        <div className="p-3 bg-neutral-900/50 border border-neutral-800/80 rounded-lg space-y-1">
          <div className="flex items-center justify-between text-neutral-400">
            <span>Estimated Cost</span>
            <span className="text-[9px] px-1 bg-neutral-800 text-neutral-400 rounded">
              {ev.estimated_cost_usd || "UNKNOWN"}
            </span>
          </div>
          <span className="text-base font-bold text-neutral-100 font-mono block">
            {raw.estimated_cost_usd === "UNKNOWN"
              ? "UNKNOWN"
              : raw.estimated_cost_usd !== undefined
              ? `$${Number(raw.estimated_cost_usd).toFixed(2)}`
              : "-"}
          </span>
        </div>
      </div>

      {/* Scientific Provenance Links */}
      <div className="p-3 bg-neutral-950 border border-neutral-800/80 rounded-lg space-y-1.5 text-[11px] text-neutral-400">
        <span className="font-semibold text-neutral-300 block">Experimental Provenance Trace</span>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 font-mono">
          <div>Experiment ID: {candidate.experiment_id}</div>
          <div>Trial ID: {candidate.experiment_trial_id}</div>
          <div>Eval Run ID: {candidate.evaluation_run_id || "None"}</div>
          <div>Dataset Version: {candidate.dataset_version_id || "None"}</div>
          <div>Suite Version: {candidate.evaluation_suite_version_id || "None"}</div>
          <div>Evaluation Split: {candidate.evaluation_split || "None"}</div>
        </div>
      </div>
    </div>
  );
};
