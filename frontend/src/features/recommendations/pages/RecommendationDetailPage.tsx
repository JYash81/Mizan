import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Sparkles,
  Archive,
  Star,
  AlertTriangle,
  RefreshCw,
  Sliders,
  Layers,
  BarChart3,
  HelpCircle,
  ShieldCheck,
  Clock,
  User,
} from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import {
  fetchRecommendationRun,
  archiveRecommendationRun,
  exportRecommendationReport,
} from "../api";
import { RecommendationMatrix } from "../components/RecommendationMatrix";
import { ParetoFrontierChart } from "../components/ParetoFrontierChart";
import { WeightedScenarioView } from "../components/WeightedScenarioView";
import { CandidateExplanationCard } from "../components/CandidateExplanationCard";
import { HumanDecisionModal } from "../components/HumanDecisionModal";
import type { RecommendationCandidateResponse } from "../types";

type DetailTab = "MATRIX" | "PARETO" | "SCENARIOS" | "EXPLANATIONS" | "DECISIONS";

export const RecommendationDetailPage: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const { activeWorkspace } = useAuth();
  const workspaceId = activeWorkspace?.id;
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<DetailTab>("MATRIX");
  const [showDecisionModal, setShowDecisionModal] = useState(false);
  const [selectedCandidateForDecision, setSelectedCandidateForDecision] =
    useState<RecommendationCandidateResponse | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  const { data: run, isLoading, error } = useQuery({
    queryKey: ["recommendation-run", workspaceId, runId],
    queryFn: () => fetchRecommendationRun(workspaceId!, runId!),
    enabled: Boolean(workspaceId && runId),
  });

  const archiveMutation = useMutation({
    mutationFn: () => archiveRecommendationRun(workspaceId!, runId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recommendation-run", workspaceId, runId] });
      queryClient.invalidateQueries({ queryKey: ["recommendation-runs", workspaceId] });
    },
  });

  const handleDownload = async (format: "json" | "markdown" | "csv") => {
    if (!workspaceId || !runId) return;
    try {
      setDownloadingFormat(format);
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
      setDownloadingFormat(null);
    }
  };

  const openDecisionModalForCandidate = (cand: RecommendationCandidateResponse) => {
    setSelectedCandidateForDecision(cand);
    setShowDecisionModal(true);
  };

  if (!workspaceId || !runId) {
    return (
      <div className="p-8 text-center text-neutral-400">
        Please select a valid workspace and recommendation run.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-16 text-center text-sm text-neutral-500 flex items-center justify-center gap-2">
        <RefreshCw className="w-5 h-5 animate-spin text-emerald-500" />
        <span>Loading multi-objective recommendation run...</span>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="p-8 max-w-lg mx-auto text-center space-y-3">
        <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto" />
        <h3 className="font-semibold text-neutral-100">Recommendation Run Not Found</h3>
        <p className="text-xs text-neutral-400">
          {(error as Error)?.message || "The specified recommendation run does not exist or access is unauthorized."}
        </p>
        <button
          onClick={() => navigate("/recommendations")}
          className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-medium rounded-lg mt-2 transition-colors"
        >
          Back to Recommendations
        </button>
      </div>
    );
  }

  const isArchived = run.status === "ARCHIVED";

  const tabs: { key: DetailTab; label: string; icon: React.ReactNode; badge?: number }[] = [
    { key: "MATRIX", label: "Comparison Matrix", icon: <Layers className="w-4 h-4" /> },
    {
      key: "PARETO",
      label: "Pareto Trade-Offs",
      icon: <BarChart3 className="w-4 h-4" />,
      badge: run.frontier_candidates,
    },
    {
      key: "SCENARIOS",
      label: "Preferences & Sensitivity",
      icon: <Sliders className="w-4 h-4" />,
      badge: run.scenarios.length,
    },
    {
      key: "EXPLANATIONS",
      label: "Explanations & Evidence",
      icon: <HelpCircle className="w-4 h-4" />,
    },
    {
      key: "DECISIONS",
      label: "Human Decisions",
      icon: <ShieldCheck className="w-4 h-4" />,
      badge: run.decisions.length,
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6">
      {/* Top Bar Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-neutral-800 pb-4">
        <div>
          <button
            onClick={() => navigate("/recommendations")}
            className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-neutral-200 mb-2 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Recommendation Centre
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-neutral-100 flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-emerald-500" />
              {run.name}
            </h1>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                run.status === "COMPLETED"
                  ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/50"
                  : isArchived
                  ? "bg-neutral-800 text-neutral-400 border border-neutral-700"
                  : "bg-amber-950/60 text-amber-400 border border-amber-800/50"
              }`}
            >
              {run.status}
            </span>
          </div>
          {run.description && (
            <p className="text-xs text-neutral-400 mt-1 max-w-2xl">{run.description}</p>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => {
              setSelectedCandidateForDecision(null);
              setShowDecisionModal(true);
            }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition-colors shadow-lg shadow-emerald-950/40"
          >
            <ShieldCheck className="w-4 h-4" />
            Record Decision
          </button>

          {/* Export Dropdown / buttons */}
          <div className="flex items-center border border-neutral-700 rounded-lg overflow-hidden bg-neutral-900">
            <button
              onClick={() => handleDownload("json")}
              disabled={Boolean(downloadingFormat)}
              className="px-2.5 py-1.5 text-xs text-neutral-300 hover:bg-neutral-800 hover:text-white transition-colors border-r border-neutral-800"
              title="Export Full JSON Snapshot"
            >
              JSON
            </button>
            <button
              onClick={() => handleDownload("markdown")}
              disabled={Boolean(downloadingFormat)}
              className="px-2.5 py-1.5 text-xs text-neutral-300 hover:bg-neutral-800 hover:text-white transition-colors border-r border-neutral-800"
              title="Export Human-Readable Markdown Report"
            >
              MD
            </button>
            <button
              onClick={() => handleDownload("csv")}
              disabled={Boolean(downloadingFormat)}
              className="px-2.5 py-1.5 text-xs text-neutral-300 hover:bg-neutral-800 hover:text-white transition-colors"
              title="Export Tabular CSV Matrix"
            >
              CSV
            </button>
          </div>

          {!isArchived && (
            <button
              onClick={() => archiveMutation.mutate()}
              disabled={archiveMutation.isPending}
              className="p-2 text-neutral-400 hover:text-amber-400 bg-neutral-900 border border-neutral-800 rounded-lg transition-colors"
              title="Archive Run"
            >
              <Archive className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Provenance & Zero-Spend Notice Banner */}
      <div className="p-4 bg-neutral-950 border border-neutral-800/80 rounded-xl space-y-2 text-xs">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="font-semibold text-neutral-200">
              Deterministic Multi-Objective Provenance Attestation
            </span>
          </div>
          <span className="text-[11px] px-2 py-0.5 bg-neutral-900 text-neutral-400 border border-neutral-800 rounded font-mono">
            Free-Only Policy: $0.00 Spend Cap Enforced
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 text-[11px] text-neutral-400 font-mono pt-1">
          <div>Run ID: {run.id.slice(0, 16)}...</div>
          <div>Input Digest: {run.input_digest.slice(0, 16)}...</div>
          <div>Result Digest: {run.result_digest ? `${run.result_digest.slice(0, 16)}...` : "None"}</div>
          <div>Algorithm: v{run.algorithm_version}</div>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 bg-neutral-900 border border-neutral-800 rounded-xl space-y-1">
          <span className="text-xs text-neutral-400 font-medium">Evaluated Candidates</span>
          <div className="text-2xl font-bold text-neutral-100 font-mono">
            {run.total_candidates}
          </div>
        </div>

        <div className="p-4 bg-neutral-900 border border-neutral-800 rounded-xl space-y-1">
          <span className="text-xs text-neutral-400 font-medium">Eligible Candidates</span>
          <div className="text-2xl font-bold text-neutral-100 font-mono">
            {run.eligible_candidates}
          </div>
        </div>

        <div className="p-4 bg-neutral-900 border border-neutral-800 rounded-xl space-y-1">
          <span className="text-xs text-neutral-400 font-medium">Pareto Frontier Members</span>
          <div className="text-2xl font-bold text-emerald-400 font-mono flex items-center gap-1">
            <Star className="w-4 h-4 fill-emerald-400 inline" />
            {run.frontier_candidates}
          </div>
        </div>

        <div className="p-4 bg-neutral-900 border border-neutral-800 rounded-xl space-y-1">
          <span className="text-xs text-neutral-400 font-medium">Recorded Decisions</span>
          <div className="text-2xl font-bold text-neutral-100 font-mono">
            {run.decisions.length}
          </div>
        </div>
      </div>

      {/* Tabs Header */}
      <div className="flex gap-2 border-b border-neutral-800 pb-2 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setActiveTab(t.key)}
            className={`inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
              activeTab === t.key
                ? "bg-neutral-800 text-neutral-100 shadow-sm border border-neutral-700"
                : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900/60"
            }`}
          >
            {t.icon}
            <span>{t.label}</span>
            {t.badge !== undefined && (
              <span className="text-[10px] px-1.5 py-0.2 bg-neutral-900 border border-neutral-700 rounded-full font-mono">
                {t.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Panels */}
      <div className="pt-2">
        {activeTab === "MATRIX" && (
          <RecommendationMatrix
            candidates={run.candidates}
            onSelectCandidate={openDecisionModalForCandidate}
          />
        )}

        {activeTab === "PARETO" && (
          <ParetoFrontierChart candidates={run.candidates} />
        )}

        {activeTab === "SCENARIOS" && (
          <WeightedScenarioView
            scenarios={run.scenarios}
            candidates={run.candidates}
          />
        )}

        {activeTab === "EXPLANATIONS" && (
          <div className="space-y-4">
            <p className="text-xs text-neutral-400">
              Detailed breakdown of why each candidate configuration is included on the Pareto frontier, dominated by other solutions, or filtered out by hard constraints:
            </p>
            <div className="space-y-4">
              {run.candidates.map((c) => (
                <CandidateExplanationCard
                  key={c.id}
                  candidate={c}
                  onSelectForDecision={openDecisionModalForCandidate}
                />
              ))}
            </div>
          </div>
        )}

        {activeTab === "DECISIONS" && (
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-neutral-100">
                  Human Review Decisions &amp; Governance Audit Trail
                </h3>
                <p className="text-xs text-neutral-400 mt-0.5">
                  Record auditable decisions on evaluated configurations prior to downstream build or release milestones.
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setSelectedCandidateForDecision(null);
                  setShowDecisionModal(true);
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                Record New Decision
              </button>
            </div>

            {run.decisions.length === 0 ? (
              <div className="p-8 border border-neutral-800 rounded-xl bg-neutral-950/40 text-center space-y-2">
                <ShieldCheck className="w-8 h-8 text-neutral-600 mx-auto" />
                <p className="text-sm font-medium text-neutral-300">No Decisions Recorded Yet</p>
                <p className="text-xs text-neutral-500">
                  Stakeholders can accept, reject, defer, or request additional evidence for candidates.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {run.decisions.map((d) => (
                  <div
                    key={d.id}
                    className="p-4 bg-neutral-950/60 border border-neutral-800 rounded-xl space-y-2"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span
                        className={`font-semibold px-2 py-0.5 rounded text-[11px] ${
                          d.decision === "ACCEPTED_FOR_FURTHER_REVIEW"
                            ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                            : d.decision === "REJECTED"
                            ? "bg-red-950 text-red-300 border border-red-800"
                            : "bg-neutral-800 text-neutral-300"
                        }`}
                      >
                        {d.decision.replace(/_/g, " ")}
                      </span>
                      <div className="flex items-center gap-3 text-neutral-500 font-mono text-[11px]">
                        <span className="flex items-center gap-1">
                          <User className="w-3 h-3" /> Actor: {d.actor_id.slice(0, 8)}...
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" /> {new Date(d.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                    {d.selected_candidate_id && (
                      <div className="text-xs text-neutral-400">
                        Target Candidate ID:{" "}
                        <span className="font-mono text-neutral-200">
                          {d.selected_candidate_id}
                        </span>
                      </div>
                    )}
                    <p className="text-xs text-neutral-300 leading-relaxed bg-neutral-900/60 p-2.5 rounded border border-neutral-800/80">
                      {d.decision_reason}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Human Decision Modal */}
      <HumanDecisionModal
        workspaceId={workspaceId}
        runId={run.id}
        candidates={run.candidates}
        selectedCandidate={selectedCandidateForDecision}
        isOpen={showDecisionModal}
        onClose={() => {
          setShowDecisionModal(false);
          setSelectedCandidateForDecision(null);
        }}
      />
    </div>
  );
};
