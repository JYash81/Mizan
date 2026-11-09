import React, { useState } from "react";
import { CheckCircle2, XCircle, Star, ChevronDown, ChevronUp, Info } from "lucide-react";
import type { RecommendationCandidateResponse } from "../types";

interface RecommendationMatrixProps {
  candidates: RecommendationCandidateResponse[];
  onSelectCandidate?: (candidate: RecommendationCandidateResponse) => void;
}

export const RecommendationMatrix: React.FC<RecommendationMatrixProps> = ({
  candidates,
  onSelectCandidate,
}) => {
  const [filterFrontierOnly, setFilterFrontierOnly] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filtered = candidates.filter((c) => {
    if (filterFrontierOnly && !c.pareto_frontier_member) return false;
    return true;
  });

  const formatNumber = (val: unknown, decimals = 1, suffix = "") => {
    if (val === null || val === undefined) return "-";
    const num = Number(val);
    if (isNaN(num)) return String(val);
    return `${num.toFixed(decimals)}${suffix}`;
  };

  const renderEvidenceTag = (type: string | undefined) => {
    if (!type) return null;
    const upper = type.toUpperCase();
    if (upper === "MEASURED") {
      return (
        <span className="text-[9px] px-1 py-0.2 bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 rounded font-mono ml-1">
          MEASURED
        </span>
      );
    }
    if (upper === "ESTIMATED") {
      return (
        <span className="text-[9px] px-1 py-0.2 bg-blue-950/80 text-blue-400 border border-blue-800/60 rounded font-mono ml-1">
          ESTIMATED
        </span>
      );
    }
    if (upper === "UNKNOWN" || upper === "UNAVAILABLE") {
      return (
        <span className="text-[9px] px-1 py-0.2 bg-amber-950/80 text-amber-400 border border-amber-800/60 rounded font-mono ml-1">
          UNKNOWN
        </span>
      );
    }
    return null;
  };

  return (
    <div className="space-y-4">
      {/* Table controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-neutral-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={filterFrontierOnly}
              onChange={(e) => setFilterFrontierOnly(e.target.checked)}
              className="rounded border-neutral-700 bg-neutral-900 text-emerald-500 focus:ring-emerald-500"
            />
            <span>Show Pareto Frontier Only</span>
          </label>
          <span className="text-xs text-neutral-500">
            ({filtered.length} of {candidates.length} candidates)
          </span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-neutral-400">
          <span className="inline-flex items-center gap-1">
            <Star className="w-3 h-3 text-emerald-400 fill-emerald-400" /> Frontier Optimal
          </span>
          <span className="inline-flex items-center gap-1 ml-2">
            <span className="w-2 h-2 rounded-full bg-neutral-500" /> Dominated
          </span>
          <span className="inline-flex items-center gap-1 ml-2">
            <span className="w-2 h-2 rounded-full bg-red-400" /> Ineligible
          </span>
        </div>
      </div>

      {/* Comparison Table */}
      <div className="border border-neutral-800 rounded-xl overflow-x-auto bg-neutral-950/50 shadow-sm">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-neutral-800 bg-neutral-900/60 text-neutral-400 font-medium">
              <th className="py-3 px-4">Candidate Configuration</th>
              <th className="py-3 px-3">Status</th>
              <th className="py-3 px-3">Pareto Status</th>
              <th className="py-3 px-3">Quality Score</th>
              <th className="py-3 px-3">P95 Latency</th>
              <th className="py-3 px-3">Peak RAM</th>
              <th className="py-3 px-3">Cost ($)</th>
              <th className="py-3 px-3">Weighted Score</th>
              <th className="py-3 px-3 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-800/60">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={9} className="py-8 text-center text-neutral-500">
                  No candidates match the selected criteria.
                </td>
              </tr>
            ) : (
              filtered.map((cand) => {
                const isExpanded = expandedId === cand.id;
                const raw = cand.objective_values;
                const isFrontier = cand.pareto_frontier_member;
                const isEligible = cand.eligibility_status === "ELIGIBLE";
                const ev = cand.evidence_summary;

                return (
                  <React.Fragment key={cand.id}>
                    <tr
                      className={`hover:bg-neutral-900/40 transition-colors cursor-pointer ${
                        isFrontier ? "bg-emerald-950/10" : ""
                      }`}
                      onClick={() => setExpandedId(isExpanded ? null : cand.id)}
                    >
                      {/* Candidate Name & Digest */}
                      <td className="py-3 px-4">
                        <div className="space-y-0.5">
                          <span className="font-semibold text-neutral-200 block truncate max-w-[240px]">
                            {cand.candidate_label}
                          </span>
                          <span className="text-[10px] text-neutral-500 font-mono block">
                            digest: {cand.configuration_digest.slice(0, 16)}...
                          </span>
                        </div>
                      </td>

                      {/* Eligibility Status */}
                      <td className="py-3 px-3">
                        {isEligible ? (
                          <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-emerald-950/60 text-emerald-400 border border-emerald-800/50">
                            <CheckCircle2 className="w-3 h-3" /> Eligible
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-red-950/60 text-red-400 border border-red-800/50">
                            <XCircle className="w-3 h-3" /> {cand.eligibility_status}
                          </span>
                        )}
                      </td>

                      {/* Pareto Status */}
                      <td className="py-3 px-3">
                        {isFrontier ? (
                          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
                            <Star className="w-3.5 h-3.5 fill-emerald-400" /> Frontier Member
                          </span>
                        ) : !isEligible ? (
                          <span className="text-neutral-500 text-xs">Excluded</span>
                        ) : (
                          <span className="text-neutral-400 text-xs">
                            Dominated ({cand.dominated_by.length})
                          </span>
                        )}
                      </td>

                      {/* Quality Score */}
                      <td className="py-3 px-3">
                        <div className="flex items-center">
                          <span className="font-mono text-neutral-200">
                            {formatNumber(raw.aggregate_score, 1, " pts")}
                          </span>
                          {renderEvidenceTag(ev.aggregate_score)}
                        </div>
                      </td>

                      {/* P95 Latency */}
                      <td className="py-3 px-3">
                        <div className="flex items-center">
                          <span className="font-mono text-neutral-200">
                            {formatNumber(raw.latency_p95_ms, 1, " ms")}
                          </span>
                          {renderEvidenceTag(ev.latency_p95_ms)}
                        </div>
                      </td>

                      {/* Peak RAM */}
                      <td className="py-3 px-3">
                        <div className="flex items-center">
                          <span className="font-mono text-neutral-200">
                            {formatNumber(raw.required_ram_mb, 0, " MB")}
                          </span>
                          {renderEvidenceTag(ev.required_ram_mb)}
                        </div>
                      </td>

                      {/* Cost */}
                      <td className="py-3 px-3">
                        <div className="flex items-center">
                          {raw.estimated_cost_usd === "UNKNOWN" ? (
                            <span className="text-amber-400 font-mono text-[11px]">UNKNOWN</span>
                          ) : (
                            <span className="font-mono text-neutral-200">
                              ${formatNumber(raw.estimated_cost_usd, 2)}
                            </span>
                          )}
                          {renderEvidenceTag(ev.estimated_cost_usd)}
                        </div>
                      </td>

                      {/* Weighted Score */}
                      <td className="py-3 px-3">
                        {cand.weighted_score !== null && cand.weighted_score !== undefined ? (
                          <span className="font-mono font-medium text-emerald-400">
                            {(cand.weighted_score * 100).toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-neutral-500 text-xs">-</span>
                        )}
                      </td>

                      {/* Expand / Details */}
                      <td className="py-3 px-3 text-right">
                        <button
                          type="button"
                          className="text-neutral-400 hover:text-neutral-200 p-1"
                        >
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4" />
                          ) : (
                            <ChevronDown className="w-4 h-4" />
                          )}
                        </button>
                      </td>
                    </tr>

                    {/* Expandable Explanation & Constraints Detail */}
                    {isExpanded && (
                      <tr className="bg-neutral-900/80 border-b border-neutral-800">
                        <td colSpan={9} className="p-4 space-y-3">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Explanation */}
                            <div className="space-y-1.5 bg-neutral-950/60 p-3 rounded-lg border border-neutral-800">
                              <div className="flex items-center gap-1.5 text-xs font-semibold text-neutral-300">
                                <Info className="w-3.5 h-3.5 text-emerald-500" />
                                <span>Deterministic Explanation &amp; Trade-Off Analysis</span>
                              </div>
                              <p className="text-xs text-neutral-300 leading-relaxed">
                                {cand.explanation_text || "No explanation recorded."}
                              </p>
                              {cand.exclusion_reasons.length > 0 && (
                                <div className="mt-2 pt-2 border-t border-neutral-800/80">
                                  <span className="text-[11px] font-medium text-red-400 block mb-1">
                                    Exclusion Reasons:
                                  </span>
                                  <ul className="list-disc list-inside text-[11px] text-red-300 space-y-0.5">
                                    {cand.exclusion_reasons.map((r, i) => (
                                      <li key={i}>{r}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>

                            {/* Constraints Detail */}
                            <div className="space-y-1.5 bg-neutral-950/60 p-3 rounded-lg border border-neutral-800">
                              <span className="text-xs font-semibold text-neutral-300 block mb-1">
                                Hard Constraint Evaluation Details
                              </span>
                              {Object.keys(cand.constraint_results).length === 0 ? (
                                <p className="text-xs text-neutral-500">
                                  No specific constraint thresholds configured.
                                </p>
                              ) : (
                                <div className="space-y-1">
                                  {Object.entries(cand.constraint_results).map(([cKey, detail]) => (
                                    <div
                                      key={cKey}
                                      className="flex items-center justify-between text-[11px] py-0.5"
                                    >
                                      <span className="text-neutral-400">
                                        {cKey.replace(/_/g, " ")}:
                                      </span>
                                      <div className="flex items-center gap-1.5">
                                        <span className="text-neutral-300 font-mono">
                                          {String(detail.actual_value ?? "-")} vs limit{" "}
                                          {String(detail.threshold ?? "-")}
                                        </span>
                                        {detail.passed ? (
                                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                                        ) : (
                                          <XCircle className="w-3 h-3 text-red-400" />
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>

                          {onSelectCandidate && (
                            <div className="flex justify-end pt-1">
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onSelectCandidate(cand);
                                }}
                                className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded transition-colors"
                              >
                                Select for Human Review Decision
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
