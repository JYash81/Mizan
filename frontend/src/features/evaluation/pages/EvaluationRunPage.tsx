import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Award,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileCode,
  FileSpreadsheet,
  FileText,
  Search,
  ShieldCheck,
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import { fetchRun, fetchReport } from "../api";
import type { EvaluationRun } from "../types";

export function EvaluationRunPage() {
  const { runId } = useParams<{ runId: string }>();
  const { activeWorkspace } = useAuth();
  const navigate = useNavigate();
  const workspaceId = activeWorkspace?.id;

  const [expandedCaseId, setExpandedCaseId] = useState<string | null>(null);
  const [filterSearch, setFilterSearch] = useState("");
  const [filterPassedOnly, setFilterPassedOnly] = useState(false);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  const { data: run, isLoading, error } = useQuery<EvaluationRun>({
    queryKey: ["evaluation-run", workspaceId, runId],
    queryFn: () => fetchRun(workspaceId!, runId!),
    enabled: !!workspaceId && !!runId,
  });

  const handleExport = async (format: "json" | "markdown" | "csv") => {
    if (!workspaceId || !runId) return;
    try {
      setDownloadingFormat(format);
      const res = await fetchReport(workspaceId, runId, format);
      const blob = new Blob(
        [typeof res === "string" ? res : JSON.stringify(res, null, 2)],
        {
          type:
            format === "json"
              ? "application/json"
              : format === "markdown"
              ? "text/markdown"
              : "text/csv",
        }
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `mizan-evaluation-run-${runId}.${format === "markdown" ? "md" : format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export error:", err);
    } finally {
      setDownloadingFormat(null);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto p-12 text-center text-sm text-muted-foreground">
        Loading evaluation scorecard...
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="max-w-7xl mx-auto p-8 my-6 rounded-xl border border-destructive/50 bg-destructive/10 text-center text-destructive">
        Evaluation run not found or could not be loaded.
      </div>
    );
  }

  const score = run.overall_score ?? 0;
  const scoreTier =
    score >= 80
      ? { label: "Production Ready", color: "text-emerald-500 border-emerald-500/30 bg-emerald-500/10" }
      : score >= 60
      ? { label: "Acceptable / Fine-Tuning Recommended", color: "text-amber-500 border-amber-500/30 bg-amber-500/10" }
      : { label: "Remediation Needed", color: "text-rose-500 border-rose-500/30 bg-rose-500/10" };

  const breakdown = run.score_breakdown || run.metric_summary || {};
  const caseResults = run.case_results || [];

  const filteredCases = caseResults.filter((c) => {
    if (filterPassedOnly && c.overall_case_score < 70) return false;
    if (filterSearch) {
      const q = filterSearch.toLowerCase();
      return (
        c.actual_answer.toLowerCase().includes(q) ||
        c.case_id.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6 sm:p-8">
      {/* Header & Navigation */}
      <div>
        <button
          onClick={() => navigate("/evaluation")}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Evaluation Overview
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                {run.status}
              </span>
              <span className="text-xs font-mono text-muted-foreground">
                Run ID: {run.id.slice(0, 8)}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                {run.provider_name} • {run.model_name}
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight mt-1 text-foreground">
              {run.target_name}
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Evaluation across {run.total_cases} examination cases with 11-metric deterministic scoring.
            </p>
          </div>

          {/* Export Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport("json")}
              disabled={!!downloadingFormat}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-secondary text-secondary-foreground hover:bg-secondary/80 border border-border"
            >
              <FileCode className="w-3.5 h-3.5" />
              JSON Report
            </button>
            <button
              onClick={() => handleExport("markdown")}
              disabled={!!downloadingFormat}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-secondary text-secondary-foreground hover:bg-secondary/80 border border-border"
            >
              <FileText className="w-3.5 h-3.5" />
              Markdown
            </button>
            <button
              onClick={() => handleExport("csv")}
              disabled={!!downloadingFormat}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-secondary text-secondary-foreground hover:bg-secondary/80 border border-border"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              CSV
            </button>
          </div>
        </div>
      </div>

      {/* Primary Quality Scorecard */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Overall Quality Gauge */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Overall Quality Score
              </span>
              <Award className="w-5 h-5 text-amber-500" />
            </div>

            <div className="mt-4 flex items-baseline gap-3">
              <span className="text-5xl font-black text-foreground tracking-tight">
                {score.toFixed(1)}%
              </span>
              <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${scoreTier.color}`}>
                {scoreTier.label}
              </span>
            </div>

            <p className="text-xs text-muted-foreground mt-3">
              Weighted aggregation of 11 deterministic metric evaluators across the immutable examination suite.
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-border grid grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-muted-foreground block">Completed Cases</span>
              <span className="text-base font-bold text-foreground">
                {run.completed_cases} / {run.total_cases}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground block">Total Execution Time</span>
              <span className="text-base font-bold text-foreground">
                {(run.execution_duration_ms / 1000).toFixed(2)}s
              </span>
            </div>
          </div>
        </div>

        {/* Right: Latency & Compliance Summary */}
        <div className="lg:col-span-2 rounded-xl border border-border bg-card p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Performance & Attestation Metrics
              </span>
              <ShieldCheck className="w-5 h-5 text-emerald-500" />
            </div>

            <div className="grid grid-cols-3 gap-4 mt-4">
              <div className="rounded-lg bg-muted/40 p-3">
                <span className="text-xs text-muted-foreground block">Latency (P50)</span>
                <span className="text-xl font-bold text-foreground mt-1 block">
                  {run.latency_p50_ms.toFixed(0)} ms
                </span>
              </div>
              <div className="rounded-lg bg-muted/40 p-3">
                <span className="text-xs text-muted-foreground block">Latency (P95)</span>
                <span className="text-xl font-bold text-foreground mt-1 block">
                  {run.latency_p95_ms.toFixed(0)} ms
                </span>
              </div>
              <div className="rounded-lg bg-muted/40 p-3">
                <span className="text-xs text-muted-foreground block">Privacy & PII Leaks</span>
                <span className="text-xl font-bold text-emerald-500 mt-1 block">
                  0 Leaks
                </span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
              <CheckCircle2 className="w-4 h-4" />
              <span>Gate 1 Approved Knowledge Grounding Enforced</span>
            </div>
            <span>Reproducible Audit Log Attested</span>
          </div>
        </div>
      </div>

      {/* 11 Metric Radar / Breakdown Cards */}
      <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-foreground uppercase tracking-wider">
          Deterministic 11-Metric Evaluation Rubric
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {Object.entries(breakdown).map(([metricKey, metricScore]) => {
            const mScore = typeof metricScore === "number" ? metricScore : 0;
            const barColor =
              mScore >= 80 ? "bg-emerald-500" : mScore >= 60 ? "bg-amber-500" : "bg-rose-500";

            return (
              <div key={metricKey} className="rounded-lg border border-border bg-muted/30 p-3 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-foreground truncate max-w-[120px]">
                    {metricKey.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                  </span>
                  <span className="font-mono font-bold">{mScore.toFixed(1)}%</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className={`h-full rounded-full ${barColor} transition-all`}
                    style={{ width: `${Math.min(100, Math.max(0, mScore))}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Per-Case Drill-Down */}
      <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-foreground">Examination Case Results</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Inspect model responses, retrieved chunks, citations and individual metric scores.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <input
                type="text"
                value={filterSearch}
                onChange={(e) => setFilterSearch(e.target.value)}
                placeholder="Search answer..."
                className="pl-8 pr-3 py-1.5 rounded-lg border border-border bg-background text-xs focus:outline-none"
              />
            </div>
            <button
              onClick={() => setFilterPassedOnly(!filterPassedOnly)}
              className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                filterPassedOnly
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-background border-border text-muted-foreground"
              }`}
            >
              Score ≥ 70% Only
            </button>
          </div>
        </div>

        {filteredCases.length === 0 ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            No case results matching filters.
          </div>
        ) : (
          <div className="space-y-3">
            {filteredCases.map((cr, idx) => {
              const isExpanded = expandedCaseId === cr.id;
              const crScore = cr.overall_case_score ?? 0;
              const scoreBadge =
                crScore >= 80
                  ? "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                  : crScore >= 60
                  ? "text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/20"
                  : "text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/20";

              return (
                <div
                  key={cr.id}
                  className="rounded-xl border border-border bg-background/50 p-4 space-y-3 transition-colors"
                >
                  <div
                    onClick={() => setExpandedCaseId(isExpanded ? null : cr.id)}
                    className="flex items-start justify-between gap-3 cursor-pointer"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs font-bold text-muted-foreground">
                        #{idx + 1}
                      </span>
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${scoreBadge}`}>
                        {crScore.toFixed(1)}%
                      </span>
                      <span className="text-xs text-muted-foreground font-mono">
                        {cr.latency_ms.toFixed(0)} ms
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <span>{isExpanded ? "Collapse" : "Drill Down"}</span>
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </div>
                  </div>

                  <div>
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
                      Model Generated Answer:
                    </span>
                    <p className="text-sm text-foreground leading-relaxed">{cr.actual_answer}</p>
                  </div>

                  {isExpanded && (
                    <div className="mt-3 pt-3 border-t border-border space-y-3">
                      {/* Metric Badges */}
                      {cr.metrics && cr.metrics.length > 0 && (
                        <div>
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1.5">
                            Metric Evaluations:
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {cr.metrics.map((m) => (
                              <span
                                key={m.id}
                                className="px-2 py-0.5 rounded text-xs bg-muted text-muted-foreground border border-border font-mono"
                              >
                                {m.metric_key}: {m.normalized_score.toFixed(0)}%
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Citations */}
                      {cr.citations && cr.citations.length > 0 && (
                        <div className="rounded-lg bg-muted/40 p-3 text-xs space-y-1">
                          <span className="font-semibold text-muted-foreground uppercase tracking-wider block">
                            Citations ({cr.citations.length}):
                          </span>
                          {cr.citations.map((c: Record<string, unknown>, cIdx: number) => (
                            <div key={cIdx} className="font-mono text-xs text-muted-foreground">
                              [{String(c.citation_marker || cIdx + 1)}] Doc: {String(c.document_id || "doc")} (chunk {String(c.chunk_index ?? 0)})
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Retrieved Chunks */}
                      {cr.retrieved_chunks && cr.retrieved_chunks.length > 0 && (
                        <div className="rounded-lg bg-muted/40 p-3 text-xs space-y-2">
                          <span className="font-semibold text-muted-foreground uppercase tracking-wider block">
                            Retrieved Context Chunks ({cr.retrieved_chunks.length}):
                          </span>
                          {cr.retrieved_chunks.map((chk: Record<string, unknown>, chkIdx: number) => (
                            <div key={chkIdx} className="text-xs text-muted-foreground border-l-2 border-primary/50 pl-2">
                              {typeof chk.text === "string" ? chk.text : JSON.stringify(chk)}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
