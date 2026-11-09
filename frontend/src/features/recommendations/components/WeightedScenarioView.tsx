import React from "react";
import { Sliders, Activity, Info, AlertCircle, CheckCircle } from "lucide-react";
import type { RecommendationScenarioResponse, RecommendationCandidateResponse } from "../types";

interface SensitivityCandidateSummary {
  candidate_id: string;
  baseline_rank?: number | null;
  min_rank?: number | null;
  max_rank?: number | null;
  rank_variance: number;
  is_rank_stable: boolean;
  scenario_ranks: Record<string, number | null>;
}

interface SensitivityReportData {
  baseline_scenario?: string;
  evaluated_scenarios?: string[];
  ranking_flips_detected?: boolean;
  candidate_summaries?: SensitivityCandidateSummary[];
}

interface WeightedScenarioViewProps {
  scenarios: RecommendationScenarioResponse[];
  candidates: RecommendationCandidateResponse[];
}

export const WeightedScenarioView: React.FC<WeightedScenarioViewProps> = ({
  scenarios,
  candidates,
}) => {
  const primaryScenario = scenarios.find((s) => s.scenario_name !== "Preference Sensitivity Analysis") || scenarios[0];
  const sensitivityScenario = scenarios.find((s) => s.scenario_name === "Preference Sensitivity Analysis");

  let sensitivityReport: SensitivityReportData | null = null;
  if (sensitivityScenario?.ranking_snapshot) {
    sensitivityReport = sensitivityScenario.ranking_snapshot as unknown as SensitivityReportData;
  }

  // Sorted candidates by weighted score
  const scoredCandidates = [...candidates]
    .filter((c) => c.weighted_score !== null && c.weighted_score !== undefined)
    .sort((a, b) => (b.weighted_score ?? 0) - (a.weighted_score ?? 0));

  return (
    <div className="space-y-6">
      {/* Notice Banner */}
      <div className="p-4 bg-neutral-950/60 border border-neutral-800 rounded-xl flex items-start gap-3 text-xs text-neutral-300">
        <Info className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-neutral-100 block mb-0.5">
            User Preference Scoring (Non-Universal Truth)
          </span>
          Scores represent candidate alignment with your explicitly configured preference weights. They do NOT represent universal model superiority. Pareto frontier membership is independent of preference weighting.
        </div>
      </div>

      {/* Primary Weights Breakdown */}
      {primaryScenario && (
        <div className="border border-neutral-800 rounded-xl bg-neutral-950/40 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-emerald-500" />
              <h3 className="text-sm font-semibold text-neutral-100">
                Active Weights Scenario: {primaryScenario.scenario_name}
              </h3>
            </div>
            {primaryScenario.explanation && (
              <span className="text-xs text-neutral-400 font-mono">
                {primaryScenario.explanation}
              </span>
            )}
          </div>

          {/* Weight distribution badges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(primaryScenario.weight_snapshot).map(([key, weight]) => (
              <div
                key={key}
                className="p-3 bg-neutral-900 border border-neutral-800 rounded-lg space-y-1"
              >
                <span className="text-[11px] text-neutral-400 block truncate">
                  {key.replace(/_/g, " ")}
                </span>
                <div className="flex items-baseline justify-between">
                  <span className="text-base font-bold text-neutral-100">
                    {(Number(weight) * 100).toFixed(0)}%
                  </span>
                  <span className="text-[10px] text-neutral-500 font-mono">w = {weight}</span>
                </div>
                <div className="w-full bg-neutral-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-emerald-500 h-full rounded-full"
                    style={{ width: `${Number(weight) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Ranked Candidates Table */}
          <div className="border border-neutral-800 rounded-lg overflow-x-auto bg-neutral-950/60 mt-4">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-neutral-800 bg-neutral-900/60 text-neutral-400 font-medium">
                  <th className="py-2.5 px-3 w-16">Rank</th>
                  <th className="py-2.5 px-3">Candidate Configuration</th>
                  <th className="py-2.5 px-3">Pareto Status</th>
                  <th className="py-2.5 px-3">Alignment Score</th>
                  <th className="py-2.5 px-3">Component Breakdown</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800/50">
                {scoredCandidates.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-neutral-500">
                      No scored candidates for this scenario.
                    </td>
                  </tr>
                ) : (
                  scoredCandidates.map((cand, idx) => (
                    <tr key={cand.id} className="hover:bg-neutral-900/30">
                      <td className="py-2.5 px-3 font-mono font-bold text-neutral-300">
                        #{idx + 1}
                      </td>
                      <td className="py-2.5 px-3 font-medium text-neutral-200">
                        {cand.candidate_label}
                      </td>
                      <td className="py-2.5 px-3">
                        {cand.pareto_frontier_member ? (
                          <span className="text-emerald-400 font-medium">Frontier Optimal</span>
                        ) : (
                          <span className="text-neutral-500">Dominated</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="font-mono font-bold text-emerald-400 text-sm">
                          {((cand.weighted_score ?? 0) * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-[11px] text-neutral-400 font-mono">
                        {Object.entries(cand.normalized_objective_values)
                          .map(([k, v]) => `${k.split("_")[0]}: ${((v ?? 0) * 100).toFixed(0)}%`)
                          .join(" | ")}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sensitivity Analysis Section */}
      {sensitivityReport && sensitivityReport.candidate_summaries && (
        <div className="border border-neutral-800 rounded-xl bg-neutral-950/40 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-500" />
              <h3 className="text-sm font-semibold text-neutral-100">
                Preference Sensitivity &amp; Ranking Stability Analysis
              </h3>
            </div>
            <div className="flex items-center gap-2 text-xs">
              {sensitivityReport.ranking_flips_detected ? (
                <span className="inline-flex items-center gap-1 text-amber-400 px-2 py-0.5 bg-amber-950/50 border border-amber-800/60 rounded">
                  <AlertCircle className="w-3.5 h-3.5" /> Ranking Shifts Detected Under Preference Changes
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-emerald-400 px-2 py-0.5 bg-emerald-950/50 border border-emerald-800/60 rounded">
                  <CheckCircle className="w-3.5 h-3.5" /> High Ranking Stability Across Scenarios
                </span>
              )}
            </div>
          </div>

          <p className="text-xs text-neutral-400">
            Tests whether the top candidates remain competitive when individual objective weights are shifted by +/-25%.
            Demonstrates preference sensitivity without making false statistical claims.
          </p>

          {/* Sensitivity Table */}
          <div className="border border-neutral-800 rounded-lg overflow-x-auto bg-neutral-950/60">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-neutral-800 bg-neutral-900/60 text-neutral-400 font-medium">
                  <th className="py-2.5 px-3">Candidate</th>
                  <th className="py-2.5 px-3 text-center">Baseline Rank</th>
                  <th className="py-2.5 px-3 text-center">Rank Range</th>
                  <th className="py-2.5 px-3 text-center">Shift Variance</th>
                  <th className="py-2.5 px-3">Stability Assessment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800/50">
                {sensitivityReport.candidate_summaries.map((sum) => {
                  const candObj = candidates.find((c) => c.id === sum.candidate_id);
                  const label = candObj?.candidate_label || sum.candidate_id;

                  return (
                    <tr key={sum.candidate_id} className="hover:bg-neutral-900/30">
                      <td className="py-2.5 px-3 font-medium text-neutral-200">{label}</td>
                      <td className="py-2.5 px-3 text-center font-mono font-bold text-neutral-300">
                        #{sum.baseline_rank ?? "-"}
                      </td>
                      <td className="py-2.5 px-3 text-center font-mono text-neutral-400">
                        #{sum.min_rank ?? "-"} - #{sum.max_rank ?? "-"}
                      </td>
                      <td className="py-2.5 px-3 text-center font-mono text-neutral-400">
                        +/- {sum.rank_variance.toFixed(0)} pos
                      </td>
                      <td className="py-2.5 px-3">
                        {sum.is_rank_stable ? (
                          <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-950/50 text-emerald-400 border border-emerald-800/50">
                            Robust / Stable
                          </span>
                        ) : (
                          <span className="text-[11px] px-2 py-0.5 rounded bg-amber-950/50 text-amber-400 border border-amber-800/50">
                            Preference-Sensitive
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
