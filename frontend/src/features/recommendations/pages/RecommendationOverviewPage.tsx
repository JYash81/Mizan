import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Sparkles,
  Plus,
  Sliders,
  Archive,
  Download,
  AlertTriangle,
  RefreshCw,
  Star,
  ChevronRight,
} from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import {
  fetchRecommendationRuns,
  archiveRecommendationRun,
  exportRecommendationReport,
  fetchOptimizationProfiles,
} from "../api";
import { RecommendationWizardModal } from "../components/RecommendationWizardModal";
import { OptimizationProfilesManager } from "../components/OptimizationProfilesManager";

export const RecommendationOverviewPage: React.FC = () => {
  const { activeWorkspace } = useAuth();
  const workspaceId = activeWorkspace?.id;
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [showWizard, setShowWizard] = useState(false);
  const [showProfiles, setShowProfiles] = useState(false);
  const [exportingRunId, setExportingRunId] = useState<string | null>(null);

  const { data: runsData, isLoading, error, refetch } = useQuery({
    queryKey: ["recommendation-runs", workspaceId],
    queryFn: () => fetchRecommendationRuns(workspaceId!),
    enabled: Boolean(workspaceId),
  });

  const { data: profiles = [] } = useQuery({
    queryKey: ["optimization-profiles", workspaceId],
    queryFn: () => fetchOptimizationProfiles(workspaceId!),
    enabled: Boolean(workspaceId),
  });

  const archiveMutation = useMutation({
    mutationFn: (runId: string) => archiveRecommendationRun(workspaceId!, runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recommendation-runs", workspaceId] });
    },
  });

  const handleExport = async (runId: string, format: "json" | "markdown" | "csv") => {
    if (!workspaceId) return;
    try {
      setExportingRunId(runId);
      const text = await exportRecommendationReport(workspaceId, runId, format);
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
      a.download = `mizan-recommendation-${runId.slice(0, 8)}.${format === "markdown" ? "md" : format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setExportingRunId(null);
    }
  };

  if (!workspaceId) {
    return (
      <div className="max-w-7xl mx-auto p-12 my-6 bg-slate-900 text-slate-200 rounded-2xl border border-slate-800 shadow-xl text-center space-y-3">
        <Sparkles className="w-10 h-10 mx-auto text-emerald-400" />
        <h2 className="text-lg font-semibold text-slate-100">No Workspace Selected</h2>
        <p className="text-xs text-slate-400">Please select an active workspace to view the Recommendation Centre.</p>
      </div>
    );
  }

  const runs = runsData?.items || [];
  const totalEvaluatedCandidates = runs.reduce((acc, r) => acc + r.total_candidates, 0);
  const totalFrontierCandidates = runs.reduce((acc, r) => acc + r.frontier_candidates, 0);

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6 bg-slate-900 text-slate-100 rounded-2xl border border-slate-800 shadow-xl my-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-neutral-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-100 flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-emerald-500" />
            Recommendation Engine &amp; Explainable Optimization Matrix
          </h1>
          <p className="text-sm text-neutral-400 mt-1">
            Deterministic multi-objective Pareto analysis, preference-weighted trade-offs, and auditable configuration recommendations.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => setShowProfiles(true)}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-medium rounded-lg border border-neutral-700 transition-colors"
          >
            <Sliders className="w-4 h-4 text-emerald-500" />
            Preference Profiles ({profiles.length})
          </button>
          <button
            type="button"
            onClick={() => setShowWizard(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition-colors shadow-lg shadow-emerald-950/40"
          >
            <Plus className="w-4 h-4" />
            New Recommendation Run
          </button>
        </div>
      </div>

      {/* Free-Only Policy Banner */}
      <div className="p-3 bg-neutral-900/60 border border-neutral-800 rounded-lg flex items-center justify-between text-xs text-neutral-400">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span>
            <strong>Free-Only Policy:</strong> All optimizations run deterministically on local CPU. Zero cloud spend ($0.00).
          </span>
        </div>
        <span className="text-[11px] font-mono text-neutral-500">
          Algorithm: Deterministic Pareto v1.0.0
        </span>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 bg-neutral-900 border border-neutral-800 rounded-xl space-y-1">
          <span className="text-xs text-neutral-400 font-medium">Recommendation Runs</span>
          <div className="text-2xl font-bold text-neutral-100 font-mono">{runs.length}</div>
        </div>

        <div className="p-4 bg-neutral-900 border border-neutral-800 rounded-xl space-y-1">
          <span className="text-xs text-neutral-400 font-medium">Candidates Evaluated</span>
          <div className="text-2xl font-bold text-neutral-100 font-mono">
            {totalEvaluatedCandidates}
          </div>
        </div>

        <div className="p-4 bg-neutral-900 border border-neutral-800 rounded-xl space-y-1">
          <span className="text-xs text-neutral-400 font-medium">Frontier Optimal Solutions</span>
          <div className="text-2xl font-bold text-emerald-400 font-mono flex items-center gap-1">
            <Star className="w-4 h-4 fill-emerald-400 inline" />
            {totalFrontierCandidates}
          </div>
        </div>

        <div className="p-4 bg-neutral-900 border border-neutral-800 rounded-xl space-y-1">
          <span className="text-xs text-neutral-400 font-medium">Optimization Profiles</span>
          <div className="text-2xl font-bold text-neutral-100 font-mono">{profiles.length}</div>
        </div>
      </div>

      {/* Runs List Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-neutral-200">
            Recommendation History &amp; Decision Records
          </h2>
          <button
            onClick={() => refetch()}
            className="p-1 text-neutral-400 hover:text-neutral-200 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-sm text-neutral-500 animate-pulse">
            Loading recommendation runs...
          </div>
        ) : error ? (
          <div className="p-8 border border-neutral-800 rounded-xl bg-neutral-950/40 text-center space-y-2">
            <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto" />
            <p className="text-sm font-semibold text-neutral-200">Could not load recommendations</p>
            <p className="text-xs text-neutral-400">{(error as Error)?.message}</p>
          </div>
        ) : runs.length === 0 ? (
          <div className="p-12 border border-neutral-800 rounded-xl bg-neutral-950/40 text-center space-y-3">
            <Sparkles className="w-10 h-10 text-neutral-600 mx-auto" />
            <h3 className="text-sm font-semibold text-neutral-200">No Recommendation Runs Yet</h3>
            <p className="text-xs text-neutral-400 max-w-md mx-auto">
              Synthesize experimental evidence from Milestone 6 evaluations and Milestone 7 experiment trials to calculate Pareto optimal configurations.
            </p>
            <button
              onClick={() => setShowWizard(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition-colors mt-2"
            >
              <Plus className="w-4 h-4" />
              Launch First Recommendation Run
            </button>
          </div>
        ) : (
          <div className="border border-neutral-800 rounded-xl overflow-x-auto bg-neutral-950/40 shadow-sm">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-neutral-800 bg-neutral-900/60 text-neutral-400 font-medium">
                  <th className="py-3 px-4">Run Name &amp; Input Digest</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Candidates</th>
                  <th className="py-3 px-3">Frontier Members</th>
                  <th className="py-3 px-3">Created</th>
                  <th className="py-3 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800/50">
                {runs.map((r) => {
                  const isArchived = r.status === "ARCHIVED";
                  return (
                    <tr
                      key={r.id}
                      className="hover:bg-neutral-900/40 transition-colors cursor-pointer"
                      onClick={() => navigate(`/recommendations/${r.id}`)}
                    >
                      <td className="py-3 px-4">
                        <div className="space-y-0.5">
                          <span className="font-semibold text-neutral-100 text-sm block">
                            {r.name}
                          </span>
                          <span className="text-[10px] text-neutral-500 font-mono block">
                            digest: {r.input_digest.slice(0, 16)}...
                          </span>
                        </div>
                      </td>

                      <td className="py-3 px-3">
                        <span
                          className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                            r.status === "COMPLETED"
                              ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/50"
                              : r.status === "COMPLETED_WITH_WARNINGS"
                              ? "bg-amber-950/60 text-amber-400 border border-amber-800/50"
                              : isArchived
                              ? "bg-neutral-800 text-neutral-400 border border-neutral-700"
                              : "bg-blue-950/60 text-blue-400 border border-blue-800/50"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>

                      <td className="py-3 px-3 font-mono text-neutral-300">
                        {r.eligible_candidates} / {r.total_candidates}
                      </td>

                      <td className="py-3 px-3">
                        <span className="inline-flex items-center gap-1 font-mono font-bold text-emerald-400">
                          <Star className="w-3.5 h-3.5 fill-emerald-400" />
                          {r.frontier_candidates}
                        </span>
                      </td>

                      <td className="py-3 px-3 text-neutral-400">
                        {new Date(r.created_at).toLocaleDateString()}
                      </td>

                      <td className="py-3 px-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleExport(r.id, "json")}
                            disabled={exportingRunId === r.id}
                            className="p-1.5 text-neutral-400 hover:text-neutral-200 transition-colors"
                            title="Export JSON"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                          {!isArchived && (
                            <button
                              onClick={() => archiveMutation.mutate(r.id)}
                              className="p-1.5 text-neutral-400 hover:text-amber-400 transition-colors"
                              title="Archive Run"
                            >
                              <Archive className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => navigate(`/recommendations/${r.id}`)}
                            className="p-1.5 text-emerald-500 hover:text-emerald-400 transition-colors"
                            title="View Matrix & Details"
                          >
                            <ChevronRight className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recommendation Wizard Modal */}
      <RecommendationWizardModal
        workspaceId={workspaceId}
        isOpen={showWizard}
        onClose={() => setShowWizard(false)}
        onRunCreated={(runId) => navigate(`/recommendations/${runId}`)}
      />

      {/* Optimization Profiles Manager Modal */}
      <OptimizationProfilesManager
        workspaceId={workspaceId}
        isOpen={showProfiles}
        onClose={() => setShowProfiles(false)}
      />
    </div>
  );
};
