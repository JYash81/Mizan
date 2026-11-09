import React, { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Hammer,
  ArrowLeft,
  FileCode,
  Layers,
  Cpu,
  Scale,
  Play,
  FileText,
} from "lucide-react";
import { fetchBuildRun, executeLocalSmokeTest } from "../api";
import type { ModelBuildRun, BuildPreflightResponse } from "../types";
import { ResourcePreflightCard } from "../components/ResourcePreflightCard";
import { ArtifactStagingCard } from "../components/ArtifactStagingCard";
import { EvaluationComparisonCard } from "../components/EvaluationComparisonCard";
import { ColabExportDrawer } from "../components/ColabExportDrawer";

export const ModelBuildingDetailPage: React.FC = () => {
  const { workspaceId = "default-ws", runId = "" } = useParams<{
    workspaceId: string;
    runId: string;
  }>();

  const [run, setRun] = useState<ModelBuildRun | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<string>("artifacts");
  const [isColabDrawerOpen, setIsColabDrawerOpen] = useState<boolean>(false);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);

  const loadRun = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await fetchBuildRun(workspaceId, runId);
      setRun(data);
    } catch (err) {
      console.error("Failed to fetch build run", err);
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId, runId]);

  useEffect(() => {
    void loadRun();
  }, [loadRun]);

  const handleRunSmokeTest = async () => {
    setIsExecuting(true);
    try {
      await executeLocalSmokeTest(workspaceId, runId);
      await loadRun();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Execution error";
      alert(`Smoke test failed: ${msg}`);
    } finally {
      setIsExecuting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto p-12 my-6 bg-slate-900 text-slate-200 rounded-2xl border border-slate-800 shadow-xl text-center space-y-3">
        <Cpu className="h-6 w-6 animate-spin mx-auto text-indigo-400" />
        <p className="text-sm font-medium">Loading model build run details...</p>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="max-w-7xl mx-auto p-12 my-6 bg-slate-900 text-slate-200 rounded-2xl border border-slate-800 shadow-xl text-center space-y-3">
        <p className="text-base font-semibold text-slate-100">Build run not found</p>
        <Link
          to={`/workspaces/${workspaceId}/model-building`}
          className="text-xs text-indigo-400 hover:underline"
        >
          Return to Model Building Overview
        </Link>
      </div>
    );
  }

  const isCompleted = run.status === "COMPLETED";
  const isReady = run.status === "READY";
  const isSmokeTest = run.execution_mode === "LOCAL_SMOKE_TEST";
  const isColabMode = run.execution_mode === "MANUAL_COLAB_NOTEBOOK";

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6 sm:p-8 my-6 bg-slate-900 text-slate-100 rounded-2xl border border-slate-800 shadow-xl">
      {/* Back Link & Header */}
      <div>
        <Link
          to={`/workspaces/${workspaceId}/model-building`}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 mb-3 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Model Building Runs
        </Link>

        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Hammer className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-bold text-slate-100">{run.name}</h1>
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                    isCompleted
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                      : isReady
                      ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                      : run.status === "BLOCKED_BY_RESOURCES"
                      ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                      : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {run.status}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Recipe: <span className="font-mono text-slate-200">{run.recipe_key}</span> · Runtime:{" "}
                <span className="font-mono text-slate-200">{run.execution_mode}</span> · Created:{" "}
                {new Date(run.created_at).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            {isSmokeTest && isReady && (
              <button
                onClick={handleRunSmokeTest}
                disabled={isExecuting}
                data-testid="detail-run-smoke-test-btn"
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-50"
              >
                <Play className="h-3.5 w-3.5" />
                {isExecuting ? "Executing..." : "Execute Local Smoke Test"}
              </button>
            )}

            {isColabMode && (
              <button
                onClick={() => setIsColabDrawerOpen(true)}
                data-testid="open-colab-drawer-btn"
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors shadow-lg shadow-blue-950/30"
              >
                <FileCode className="h-3.5 w-3.5" />
                Google Colab Lab & Staging
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-800 text-xs font-medium">
        <button
          onClick={() => setActiveTab("artifacts")}
          data-testid="tab-staged-artifacts"
          className={`flex items-center gap-1.5 px-4 py-2.5 border-b-2 transition-colors ${
            activeTab === "artifacts"
              ? "border-indigo-500 text-indigo-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Cpu className="h-4 w-4" />
          Staged Artifacts ({run.staged_artifacts?.length || 0})
        </button>

        <button
          onClick={() => setActiveTab("evaluations")}
          data-testid="tab-evaluations"
          className={`flex items-center gap-1.5 px-4 py-2.5 border-b-2 transition-colors ${
            activeTab === "evaluations"
              ? "border-indigo-500 text-indigo-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Scale className="h-4 w-4" />
          Evaluation & Regression ({run.evaluation_links?.length || 0})
        </button>

        <button
          onClick={() => setActiveTab("checkpoints")}
          data-testid="tab-checkpoints"
          className={`flex items-center gap-1.5 px-4 py-2.5 border-b-2 transition-colors ${
            activeTab === "checkpoints"
              ? "border-indigo-500 text-indigo-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Layers className="h-4 w-4" />
          Checkpoints ({run.checkpoints?.length || 0})
        </button>

        <button
          onClick={() => setActiveTab("manifest")}
          data-testid="tab-manifest"
          className={`flex items-center gap-1.5 px-4 py-2.5 border-b-2 transition-colors ${
            activeTab === "manifest"
              ? "border-indigo-500 text-indigo-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <FileText className="h-4 w-4" />
          Manifest & Preflight
        </button>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {/* Tab: Staged Artifacts */}
        {activeTab === "artifacts" && (
          <div className="space-y-4">
            <ArtifactStagingCard artifacts={run.staged_artifacts || []} />
          </div>
        )}

        {/* Tab: Evaluation & Regression */}
        {activeTab === "evaluations" && (
          <div className="space-y-4">
            <EvaluationComparisonCard links={run.evaluation_links || []} />
          </div>
        )}

        {/* Tab: Checkpoints */}
        {activeTab === "checkpoints" && (
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Checkpoint History
            </h3>
            {(!run.checkpoints || run.checkpoints.length === 0) ? (
              <p className="text-xs text-slate-500">No checkpoints recorded for this build run.</p>
            ) : (
              <div className="space-y-2">
                {run.checkpoints.map((c) => (
                  <div
                    key={c.id}
                    className="flex items-center justify-between p-3 rounded bg-slate-800/60 border border-slate-700/60 text-xs"
                  >
                    <div>
                      <span className="font-semibold text-slate-200">
                        Checkpoint #{c.checkpoint_number} (Step {c.step_number}, Epoch {c.epoch})
                      </span>
                      <p className="text-[11px] font-mono text-slate-400 mt-0.5">
                        SHA-256: {c.sha256.slice(0, 16)}...
                      </p>
                    </div>
                    <span className="text-[11px] text-slate-400">
                      {new Date(c.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab: Manifest & Preflight */}
        {activeTab === "manifest" && (
          <div className="space-y-6">
            {/* Preflight Card */}
            <ResourcePreflightCard
              preflight={
                run.preflight_snapshot
                  ? (run.preflight_snapshot as unknown as BuildPreflightResponse)
                  : null
              }
            />

            {/* Canonical Manifest JSON Viewer */}
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-slate-200">
                  Canonical Build Manifest (RFC 8785)
                </h4>
                <span className="font-mono text-xs text-indigo-400">
                  Digest: {run.manifest_digest}
                </span>
              </div>
              <pre className="rounded bg-slate-950 p-4 font-mono text-[11px] text-slate-300 overflow-x-auto border border-slate-800">
                {JSON.stringify(run.build_manifest, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>

      {/* Colab Export Drawer */}
      <ColabExportDrawer
        run={run}
        isOpen={isColabDrawerOpen}
        onClose={() => setIsColabDrawerOpen(false)}
        onImportSuccess={() => loadRun()}
      />
    </div>
  );
};
