import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  BarChart2,
  AlertTriangle,
  Download,
  ShieldCheck,
  Zap,
  Info,
  RefreshCw,
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import { fetchComparison, exportReport } from "../api";
import type { ExperimentComparisonResponse } from "../types";

export function ExperimentComparisonPage() {
  const { experimentId } = useParams<{ experimentId: string }>();
  const { activeWorkspace } = useAuth();
  const navigate = useNavigate();
  const workspaceId = activeWorkspace?.id;

  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  const { data: comparison, isLoading, error } = useQuery<ExperimentComparisonResponse>({
    queryKey: ["experiment-comparison", workspaceId, experimentId],
    queryFn: () => fetchComparison(workspaceId!, experimentId!),
    enabled: Boolean(workspaceId && experimentId),
  });

  const handleDownload = async (format: "json" | "markdown" | "csv") => {
    if (!workspaceId || !experimentId) return;
    try {
      setDownloadingFormat(format);
      const text = await exportReport(workspaceId, experimentId, format);
      const blob = new Blob([text], {
        type:
          format === "json"
            ? "application/json"
            : format === "markdown"
            ? "text/markdown"
            : "text/csv",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `experiment-comparison-${experimentId}.${format === "markdown" ? "md" : format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setDownloadingFormat(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px] text-muted-foreground text-sm">
        <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Loading comparison matrix...
      </div>
    );
  }

  if (error || !comparison) {
    return (
      <div className="p-8 text-center max-w-lg mx-auto space-y-3">
        <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto" />
        <h3 className="font-semibold text-base">Comparison Not Available</h3>
        <p className="text-sm text-muted-foreground">
          {(error as Error)?.message || "At least one completed trial is required to generate comparison matrix."}
        </p>
        <button
          onClick={() => navigate(`/experiments/${experimentId}`)}
          className="px-4 py-2 bg-primary text-primary-foreground text-xs font-medium rounded-md mt-2"
        >
          Back to Experiment
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6">
      {/* Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <button
            onClick={() => navigate(`/experiments/${experimentId}`)}
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-1.5 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Experiment Details
          </button>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BarChart2 className="w-6 h-6 text-primary" />
            Factual Trial Comparison Matrix
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Experiment: <strong className="text-foreground">{comparison.experiment_name}</strong> • Split:{" "}
            <strong className="text-foreground">{comparison.evaluation_split}</strong>
          </p>
        </div>

        {/* Export Buttons */}
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-secondary border border-border rounded-md overflow-hidden text-xs">
            <button
              onClick={() => handleDownload("json")}
              disabled={Boolean(downloadingFormat)}
              className="px-3 py-1.5 hover:bg-secondary/80 border-r border-border transition-colors flex items-center gap-1"
            >
              <Download className="w-3.5 h-3.5" /> JSON
            </button>
            <button
              onClick={() => handleDownload("markdown")}
              disabled={Boolean(downloadingFormat)}
              className="px-3 py-1.5 hover:bg-secondary/80 border-r border-border transition-colors flex items-center gap-1"
            >
              <Download className="w-3.5 h-3.5" /> Markdown
            </button>
            <button
              onClick={() => handleDownload("csv")}
              disabled={Boolean(downloadingFormat)}
              className="px-3 py-1.5 hover:bg-secondary/80 transition-colors flex items-center gap-1"
            >
              <Download className="w-3.5 h-3.5" /> CSV
            </button>
          </div>
        </div>
      </div>

      {/* Provenance Consistency Attestation */}
      <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 rounded-lg flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 shrink-0" />
          <span>
            <strong>Provenance Consistency Attested:</strong> All compared trials ran against identical approved dataset snapshot (<code>{comparison.dataset_version_id.slice(0, 8)}...</code>) and frozen evaluation suite snapshot (<code>{comparison.evaluation_suite_version_id.slice(0, 8)}...</code>).
          </span>
        </div>
        <span className="font-semibold px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/30">
          Verified
        </span>
      </div>

      {/* Trial Configurations & Aggregate Measurements Table */}
      <div className="bg-card border border-border rounded-lg overflow-hidden shadow-sm">
        <div className="px-5 py-3 border-b border-border bg-secondary/30">
          <h3 className="font-semibold text-sm">Trial Configurations & Aggregate Scores</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-secondary/20 text-muted-foreground border-b border-border font-medium">
              <tr>
                <th className="px-4 py-2.5">Trial #</th>
                <th className="px-4 py-2.5">Status</th>
                <th className="px-4 py-2.5">Model</th>
                <th className="px-4 py-2.5">Chunk Size</th>
                <th className="px-4 py-2.5">Overlap</th>
                <th className="px-4 py-2.5">Top-K</th>
                <th className="px-4 py-2.5">Aggregate Score</th>
                <th className="px-4 py-2.5">p50 Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {comparison.trials.map((t) => {
                const c = t.configuration;
                return (
                  <tr key={t.trial_id} className="hover:bg-secondary/30 transition-colors">
                    <td className="px-4 py-3 font-semibold">Trial {t.trial_number}</td>
                    <td className="px-4 py-3">{t.status}</td>
                    <td className="px-4 py-3 font-mono text-muted-foreground">
                      {(c.model_name as string) || (c.provider_name as string) || "—"}
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {(c.chunk_size_chars as number) || (c.chunk_size as number) || "—"}
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {(c.chunk_overlap_chars as number) || (c.chunk_overlap as number) || "—"}
                    </td>
                    <td className="px-4 py-3 font-mono">{(c.top_k as number) || "—"}</td>
                    <td className="px-4 py-3 font-bold text-foreground">
                      {t.aggregate_score !== null ? `${t.aggregate_score.toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 font-mono text-muted-foreground">
                      {t.latency_p50_ms !== null ? `${t.latency_p50_ms.toFixed(1)} ms` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Aligned Rubric Metric Matrix */}
      {comparison.metric_keys.length > 0 && (
        <div className="bg-card border border-border rounded-lg overflow-hidden shadow-sm">
          <div className="px-5 py-3 border-b border-border bg-secondary/30 flex items-center justify-between">
            <h3 className="font-semibold text-sm">Aligned Rubric Metric Comparison</h3>
            <span className="text-[11px] text-muted-foreground">
              Values in percent. Missing metrics preserved as — (never 0.0%)
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-secondary/20 text-muted-foreground border-b border-border font-medium">
                <tr>
                  <th className="px-4 py-2.5">Rubric Metric</th>
                  {comparison.trials.map((t) => (
                    <th key={t.trial_id} className="px-4 py-2.5 font-semibold">
                      Trial {t.trial_number}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {comparison.metric_keys.map((mKey) => {
                  const obs = comparison.metric_observations.find((o) => o.metric_key === mKey);
                  const highestScore = obs?.highest_observed_score;

                  return (
                    <tr key={mKey} className="hover:bg-secondary/30 transition-colors">
                      <td className="px-4 py-3 font-medium capitalize text-foreground">
                        {mKey.replace(/_/g, " ")}
                      </td>
                      {comparison.trials.map((t) => {
                        const val = t.metric_scores[mKey];
                        const isHighest =
                          val !== null &&
                          val !== undefined &&
                          highestScore !== null &&
                          highestScore !== undefined &&
                          val === highestScore;

                        return (
                          <td
                            key={t.trial_id}
                            className={`px-4 py-3 font-mono ${
                              isHighest ? "text-emerald-500 font-bold" : "text-muted-foreground"
                            }`}
                          >
                            {val !== null && val !== undefined ? `${val.toFixed(1)}%` : "—"}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Factual Metric Observations Card */}
      <div className="bg-card border border-border rounded-lg p-5 space-y-4 shadow-sm">
        <h3 className="font-semibold text-sm flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-500" />
          Empirical Factual Observations (Milestone 7 Scope)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          {comparison.metric_observations.map((obs) => {
            if (obs.highest_observed_score === null || obs.highest_observed_score === undefined) {
              return null;
            }
            return (
              <div
                key={obs.metric_key}
                className="p-3 bg-secondary/40 border border-border rounded-md space-y-1"
              >
                <div className="font-medium text-foreground capitalize">
                  {obs.metric_key.replace(/_/g, " ")}
                </div>
                <div className="text-muted-foreground">
                  Highest observed:{" "}
                  <strong className="text-emerald-500">
                    {obs.highest_observed_score.toFixed(1)}%
                  </strong>{" "}
                  (Trial {obs.highest_scoring_trials.join(", ")}) • Lowest:{" "}
                  {obs.lowest_observed_score?.toFixed(1)}% • Mean: {obs.mean_observed_score?.toFixed(1)}%
                </div>
              </div>
            );
          })}

          {comparison.lowest_observed_latency_ms !== null && (
            <div className="p-3 bg-secondary/40 border border-border rounded-md space-y-1">
              <div className="font-medium text-foreground">Execution Latency (p50)</div>
              <div className="text-muted-foreground">
                Lowest observed p50 latency:{" "}
                <strong className="text-emerald-500">
                  {comparison.lowest_observed_latency_ms.toFixed(1)} ms
                </strong>{" "}
                (Trial {comparison.lowest_latency_trials.join(", ")})
              </div>
            </div>
          )}
        </div>

        {/* Milestone Boundary Disclaimer */}
        <div className="p-3 bg-primary/5 border border-primary/20 text-muted-foreground text-[11px] rounded-md flex items-start gap-2">
          <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
          <span>
            <strong>Evaluation Boundary Policy:</strong> These observations report empirical observations without subjective weighting. Automated recommendations, Pareto-frontier analysis, and optimal configuration selection are performed strictly in downstream Milestone 9.
          </span>
        </div>
      </div>
    </div>
  );
}
