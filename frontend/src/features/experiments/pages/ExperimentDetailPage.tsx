import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  BarChart2,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Play,
  XCircle,
  ShieldCheck,
  Cpu,
  Layers,
  RefreshCw,
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import {
  fetchExperiment,
  executeExperiment,
  cancelExperiment,
  exportReport,
} from "../api";
import type { Experiment, ExperimentTrial, TrialStatus } from "../types";

function getTrialBadge(status: TrialStatus) {
  switch (status) {
    case "COMPLETED":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
          <CheckCircle2 className="w-3 h-3" /> Done
        </span>
      );
    case "FAILED":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-rose-500/10 text-rose-500 border border-rose-500/20">
          <AlertTriangle className="w-3 h-3" /> Failed
        </span>
      );
    case "RUNNING":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-500/10 text-blue-500 border border-blue-500/20 animate-pulse">
          <RefreshCw className="w-3 h-3 animate-spin" /> Running
        </span>
      );
    case "CANCELLED":
    case "SKIPPED":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-neutral-500/10 text-neutral-400 border border-neutral-500/20">
          <Clock className="w-3 h-3" /> Cancelled
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-secondary text-muted-foreground border border-border">
          {status}
        </span>
      );
  }
}

interface ParsedTrialConfig {
  chunk_size_chars?: number;
  chunk_size?: number;
  chunk_overlap_chars?: number;
  chunk_overlap?: number;
  top_k?: number;
  model_name?: string;
  provider_name?: string;
  [key: string]: unknown;
}

export function ExperimentDetailPage() {
  const { experimentId } = useParams<{ experimentId: string }>();
  const { activeWorkspace } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const workspaceId = activeWorkspace?.id;

  const [selectedTrial, setSelectedTrial] = useState<ExperimentTrial | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  const { data: experiment, isLoading, refetch } = useQuery<Experiment>({
    queryKey: ["experiment", workspaceId, experimentId],
    queryFn: () => fetchExperiment(workspaceId!, experimentId!),
    enabled: Boolean(workspaceId && experimentId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "RUNNING" || status === "QUEUED" ? 3000 : false;
    },
  });

  const executeMutation = useMutation({
    mutationFn: () => executeExperiment(workspaceId!, experimentId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["experiment", workspaceId, experimentId] });
      refetch();
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelExperiment(workspaceId!, experimentId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["experiment", workspaceId, experimentId] });
      refetch();
    },
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
      a.download = `experiment-${experiment?.slug || experimentId}.${
        format === "markdown" ? "md" : format
      }`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setDownloadingFormat(null);
    }
  };

  if (isLoading || !experiment) {
    return (
      <div className="flex items-center justify-center min-h-[400px] text-muted-foreground text-sm">
        <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Loading experiment details...
      </div>
    );
  }

  const isTerminal = ["COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED", "CANCELLED"].includes(
    experiment.status
  );
  const isRunning = experiment.status === "RUNNING";

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6">
      {/* Back button & top navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate("/experiments")}
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Experiments
        </button>

        <div className="flex items-center gap-2">
          {isTerminal && (
            <button
              onClick={() => navigate(`/experiments/${experiment.id}/comparison`)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 px-3.5 py-1.5 rounded-md transition-colors shadow-sm"
            >
              <BarChart2 className="w-4 h-4" />
              View Factual Comparison
            </button>
          )}

          {/* Export Dropdown */}
          {isTerminal && (
            <div className="flex items-center bg-secondary border border-border rounded-md overflow-hidden text-xs">
              <button
                onClick={() => handleDownload("json")}
                disabled={Boolean(downloadingFormat)}
                className="px-2.5 py-1.5 hover:bg-secondary/80 border-r border-border transition-colors"
              >
                JSON
              </button>
              <button
                onClick={() => handleDownload("markdown")}
                disabled={Boolean(downloadingFormat)}
                className="px-2.5 py-1.5 hover:bg-secondary/80 border-r border-border transition-colors"
              >
                Markdown
              </button>
              <button
                onClick={() => handleDownload("csv")}
                disabled={Boolean(downloadingFormat)}
                className="px-2.5 py-1.5 hover:bg-secondary/80 transition-colors"
              >
                CSV
              </button>
            </div>
          )}

          {isRunning && (
            <button
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending}
              className="inline-flex items-center gap-1.5 text-xs font-medium bg-rose-500/10 text-rose-500 hover:bg-rose-500/20 border border-rose-500/30 px-3 py-1.5 rounded-md transition-colors"
            >
              <XCircle className="w-4 h-4" />
              Cancel Execution
            </button>
          )}

          {experiment.status === "READY" && (
            <button
              onClick={() => executeMutation.mutate()}
              disabled={executeMutation.isPending}
              className="inline-flex items-center gap-1.5 text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 px-3.5 py-1.5 rounded-md transition-colors shadow-sm"
            >
              <Play className="w-4 h-4 fill-current" />
              Start Sequential Matrix
            </button>
          )}
        </div>
      </div>

      {/* Main Header Card */}
      <div className="bg-card border border-border rounded-lg p-6 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold">{experiment.name}</h1>
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-secondary text-muted-foreground border border-border">
                {experiment.slug}
              </span>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full border border-border bg-secondary">
                {experiment.status}
              </span>
            </div>
            {experiment.description && (
              <p className="text-sm text-muted-foreground mt-2 max-w-2xl">
                {experiment.description}
              </p>
            )}
          </div>

          <div className="text-right text-xs text-muted-foreground space-y-1 self-start md:self-auto">
            <div>
              Split: <strong className="text-foreground">{experiment.evaluation_split}</strong>
            </div>
            <div>
              Trials:{" "}
              <strong className="text-foreground">
                {experiment.completed_trials} / {experiment.total_trials}
              </strong>
            </div>
          </div>
        </div>

        {/* Progress bar */}
        {experiment.total_trials > 0 && (
          <div className="space-y-1">
            <div className="w-full bg-secondary/50 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  experiment.status === "COMPLETED"
                    ? "bg-emerald-500"
                    : experiment.status === "COMPLETED_WITH_ERRORS"
                    ? "bg-amber-500"
                    : "bg-primary"
                }`}
                style={{
                  width: `${Math.round(
                    ((experiment.completed_trials + experiment.failed_trials) /
                      experiment.total_trials) *
                      100
                  )}%`,
                }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-muted-foreground">
              <span>Concurrency: 1 (Local CPU sequential runner)</span>
              <span>
                {Math.round(
                  ((experiment.completed_trials + experiment.failed_trials) /
                    experiment.total_trials) *
                    100
                )}
                % Complete
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Provenance Attestation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card border border-border rounded-lg p-4 space-y-1.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Approved Dataset</span>
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="font-mono text-xs truncate font-medium text-foreground">
            {experiment.dataset_version_id}
          </div>
          <div className="text-[11px] text-muted-foreground truncate">
            Gate 1 ID: {experiment.gate1_approval_id || "Attested"}
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-4 space-y-1.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Frozen Exam Suite</span>
            <Layers className="w-4 h-4 text-primary" />
          </div>
          <div className="font-mono text-xs truncate font-medium text-foreground">
            {experiment.evaluation_suite_version_id}
          </div>
          <div className="text-[11px] text-muted-foreground truncate">
            Suite Digest: {experiment.canonical_suite_digest?.slice(0, 16)}...
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-4 space-y-1.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Matrix Execution State</span>
            <Cpu className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-xs font-medium text-foreground">
            Completed: {experiment.completed_trials} • Failed: {experiment.failed_trials}
          </div>
          <div className="text-[11px] text-muted-foreground truncate">
            Total Bounded Trials: {experiment.total_trials} (Max 9)
          </div>
        </div>
      </div>

      {/* Trials Table */}
      <div className="bg-card border border-border rounded-lg overflow-hidden shadow-sm">
        <div className="px-5 py-3 border-b border-border bg-secondary/30 flex items-center justify-between">
          <h3 className="font-semibold text-sm">Trial Matrix Configurations & Measurements</h3>
          <span className="text-xs text-muted-foreground">
            Click a trial to view its parameter details
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-secondary/20 text-muted-foreground border-b border-border font-medium">
              <tr>
                <th className="px-4 py-2.5">#</th>
                <th className="px-4 py-2.5">Trial Name</th>
                <th className="px-4 py-2.5">Status</th>
                <th className="px-4 py-2.5">Chunk (Size / Overlap)</th>
                <th className="px-4 py-2.5">Top-K</th>
                <th className="px-4 py-2.5">Model</th>
                <th className="px-4 py-2.5">Score</th>
                <th className="px-4 py-2.5">p50 Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {experiment.trials.map((t) => {
                let conf: ParsedTrialConfig = {};
                try {
                  conf = JSON.parse(t.configuration_json) as ParsedTrialConfig;
                } catch {
                  // ignore
                }

                return (
                  <tr
                    key={t.id}
                    onClick={() => setSelectedTrial(t)}
                    className="hover:bg-secondary/40 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 font-semibold">{t.trial_number}</td>
                    <td className="px-4 py-3 font-medium text-foreground">{t.name}</td>
                    <td className="px-4 py-3">{getTrialBadge(t.status)}</td>
                    <td className="px-4 py-3 text-muted-foreground font-mono">
                      {conf.chunk_size_chars ?? conf.chunk_size ?? "—"} /{" "}
                      {conf.chunk_overlap_chars ?? conf.chunk_overlap ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground font-mono">
                      {conf.top_k ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground font-mono truncate max-w-[120px]">
                      {conf.model_name ?? conf.provider_name ?? "—"}
                    </td>
                    <td className="px-4 py-3 font-semibold text-foreground">
                      {t.aggregate_score !== null ? `${t.aggregate_score.toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground font-mono">
                      {t.latency_p50_ms !== null ? `${t.latency_p50_ms.toFixed(1)} ms` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Trial Detail Modal */}
      {selectedTrial && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-lg max-w-lg w-full p-6 space-y-4 max-h-[85vh] overflow-y-auto shadow-xl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h4 className="font-bold text-base">
                  Trial {selectedTrial.trial_number}: {selectedTrial.name}
                </h4>
                <span className="text-xs text-muted-foreground font-mono">
                  Digest: {selectedTrial.configuration_digest.slice(0, 16)}...
                </span>
              </div>
              <button
                onClick={() => setSelectedTrial(null)}
                className="text-muted-foreground hover:text-foreground text-sm font-semibold p-1"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="font-semibold text-muted-foreground block mb-1">
                  Full Trial Configuration:
                </span>
                <pre className="p-3 bg-secondary rounded-md overflow-x-auto text-[11px] font-mono border border-border">
                  {JSON.stringify(JSON.parse(selectedTrial.configuration_json || "{}"), null, 2)}
                </pre>
              </div>

              {selectedTrial.score_breakdown && Object.keys(selectedTrial.score_breakdown).length > 0 && (
                <div>
                  <span className="font-semibold text-muted-foreground block mb-1">
                    Evaluated Rubric Breakdown:
                  </span>
                  <div className="space-y-1.5 p-3 bg-secondary/50 rounded-md border border-border">
                    {Object.entries(selectedTrial.score_breakdown).map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="capitalize">{k.replace(/_/g, " ")}:</span>
                        <strong className="text-foreground">{v.toFixed(1)}%</strong>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedTrial.error_summary && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-500 rounded-md">
                  <strong>Error Summary:</strong> {selectedTrial.error_summary}
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedTrial(null)}
                className="px-4 py-1.5 bg-secondary hover:bg-secondary/80 text-foreground text-xs font-medium rounded-md transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
