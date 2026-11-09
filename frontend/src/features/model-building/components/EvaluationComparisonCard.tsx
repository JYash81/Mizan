import React from "react";
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Scale,
  Award,
  Clock,
  Cpu,
} from "lucide-react";
import type { ModelEvaluationLink } from "../types";

interface EvaluationComparisonCardProps {
  links: ModelEvaluationLink[];
}

export const EvaluationComparisonCard: React.FC<EvaluationComparisonCardProps> = ({ links }) => {
  if (!links || links.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/30 p-8 text-center text-slate-400">
        <Scale className="mx-auto h-8 w-8 text-slate-500 mb-2" />
        <p className="text-sm font-medium">No evaluation runs linked yet</p>
        <p className="text-xs text-slate-500 mt-1">
          Link completed M6 evaluation runs to assess fine-tuning gains or quantization loss.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3">
        {links.map((link) => {
          const delta = link.quality_delta;
          const isRegression = delta < 0;
          const formattedDelta = delta > 0 ? `+${(delta * 100).toFixed(1)}%` : `${(delta * 100).toFixed(1)}%`;

          return (
            <div
              key={link.id}
              data-testid="evaluation-link-card"
              className={`rounded-lg border p-4 transition-all ${
                isRegression
                  ? "border-rose-500/30 bg-rose-950/10"
                  : "border-slate-700 bg-slate-800/80"
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-700/80 pb-3 mb-3">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                    {link.model_role}
                  </span>
                  <span className="text-xs text-slate-400">
                    Split: <span className="font-mono text-slate-200">{link.evaluation_split}</span>
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {isRegression ? (
                    <span
                      data-testid="evaluation-regression-badge"
                      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40"
                    >
                      <TrendingDown className="h-3.5 w-3.5 text-rose-400" />
                      Quality Regression ({formattedDelta})
                    </span>
                  ) : (
                    <span
                      data-testid="evaluation-gain-badge"
                      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                    >
                      <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
                      Quality Gain ({formattedDelta})
                    </span>
                  )}
                </div>
              </div>

              {/* Metric Breakdown */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs mb-2">
                <div className="rounded bg-slate-900/60 p-2 border border-slate-800">
                  <div className="flex items-center gap-1 text-slate-400 mb-0.5">
                    <Award className="h-3 w-3 text-amber-400" />
                    Overall Score
                  </div>
                  <div className="text-base font-bold text-slate-100">
                    {(link.overall_score * 100).toFixed(1)}%
                  </div>
                </div>

                <div className="rounded bg-slate-900/60 p-2 border border-slate-800">
                  <div className="flex items-center gap-1 text-slate-400 mb-0.5">
                    <Scale className="h-3 w-3 text-indigo-400" />
                    Quality Delta
                  </div>
                  <div
                    className={`text-base font-bold ${
                      isRegression ? "text-rose-400" : "text-emerald-400"
                    }`}
                  >
                    {formattedDelta}
                  </div>
                </div>

                {link.latency_delta_ms !== null && link.latency_delta_ms !== undefined && (
                  <div className="rounded bg-slate-900/60 p-2 border border-slate-800">
                    <div className="flex items-center gap-1 text-slate-400 mb-0.5">
                      <Clock className="h-3 w-3 text-cyan-400" />
                      Latency Delta
                    </div>
                    <div className="text-base font-bold text-slate-100">
                      {link.latency_delta_ms > 0 ? `+${link.latency_delta_ms} ms` : `${link.latency_delta_ms} ms`}
                    </div>
                  </div>
                )}

                {link.memory_delta_mb !== null && link.memory_delta_mb !== undefined && (
                  <div className="rounded bg-slate-900/60 p-2 border border-slate-800">
                    <div className="flex items-center gap-1 text-slate-400 mb-0.5">
                      <Cpu className="h-3 w-3 text-violet-400" />
                      Memory Delta
                    </div>
                    <div className="text-base font-bold text-slate-100">
                      {link.memory_delta_mb > 0 ? `+${link.memory_delta_mb} MB` : `${link.memory_delta_mb} MB`}
                    </div>
                  </div>
                )}
              </div>

              {isRegression && (
                <div className="mt-2 rounded bg-rose-950/20 border border-rose-500/20 p-2 text-[11px] text-rose-300 flex items-center gap-1.5">
                  <AlertTriangle className="h-3.5 w-3.5 text-rose-400 shrink-0" />
                  <span>
                    Quality loss observed post-quantization/adaptation. Ensure regression is documented before proceeding to Milestone 11 evaluation review.
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
