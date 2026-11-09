import React from "react";
import { CheckCircle2, XCircle, ShieldCheck, Clock, Layers } from "lucide-react";
import type { GoldenTestRun } from "../types";

interface GoldenTestResultsCardProps {
  run: GoldenTestRun | null;
  isLoading?: boolean;
}

const CATEGORY_LABELS: Record<string, string> = {
  startup: "Process Startup & Live Probes",
  model_loading: "Model Weights & Tensors Integrity",
  inference_smoke: "Deterministic Inference Smoke Test",
  output_schema: "OpenAI Output Schema Compliance",
  rag_retrieval_citations: "Local Grounded RAG Citations",
  safety_abstention: "Safety Policy & Guardrail Abstention",
  offline_path: "Zero External Network / Offline Isolation",
  resource_limits: "Peak Memory Within Slot Budget",
};

export const GoldenTestResultsCard: React.FC<GoldenTestResultsCardProps> = ({ run, isLoading = false }) => {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-border p-6 bg-card animate-pulse">
        <div className="h-6 w-48 bg-muted rounded mb-4" />
        <div className="space-y-3">
          <div className="h-10 bg-muted/60 rounded" />
          <div className="h-10 bg-muted/60 rounded" />
          <div className="h-10 bg-muted/60 rounded" />
        </div>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="rounded-xl border border-dashed border-border p-8 text-center bg-card/50">
        <Layers className="w-10 h-10 mx-auto text-muted-foreground/60 mb-3" />
        <h4 className="text-sm font-semibold text-foreground">No Golden Tests Executed Yet</h4>
        <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1">
          Candidate runtime slots must execute and pass all mandatory Golden Tests before traffic activation can be authorized.
        </p>
      </div>
    );
  }

  const isPassed = run.outcome === "PASSED";
  const cases = run.results_summary?.cases || [];

  return (
    <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
      <div className="p-5 border-b border-border flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${isPassed ? "bg-emerald-500/10 text-emerald-600" : "bg-red-500/10 text-red-600"}`}>
            {isPassed ? <CheckCircle2 className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-foreground">Golden Acceptance Test Suite</h3>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${isPassed ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300" : "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300"}`}>
                {run.outcome}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Suite Digest: <span className="font-mono">{run.suite_digest.slice(0, 16)}...</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-muted-foreground" />
            <span>{run.duration_ms} ms</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-medium text-foreground">{run.passed_cases}</span> / {run.total_cases} passed
          </div>
        </div>
      </div>

      <div className="bg-muted/30 px-5 py-2.5 border-b border-border/50 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 text-muted-foreground">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Privacy Guaranteed: Customer prompt text and internal corporate context are strictly excluded from logs.</span>
        </div>
      </div>

      <div className="divide-y divide-border/60">
        {cases.map((c) => (
          <div key={c.case_id} className="p-3.5 px-5 flex items-center justify-between hover:bg-muted/20 transition-colors">
            <div className="flex items-center gap-3">
              {c.passed ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
              ) : (
                <XCircle className="w-4 h-4 text-red-500 shrink-0" />
              )}
              <div>
                <p className="text-sm font-medium text-foreground">
                  {CATEGORY_LABELS[c.category] || c.category}
                </p>
                <p className="text-xs font-mono text-muted-foreground">{c.case_id}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {c.mandatory && (
                <span className="text-[10px] font-semibold tracking-wider uppercase px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                  Mandatory
                </span>
              )}
              <span
                className={`text-xs font-medium ${
                  c.passed ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
                }`}
              >
                {c.passed ? "PASSED" : c.error_code || "FAILED"}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
