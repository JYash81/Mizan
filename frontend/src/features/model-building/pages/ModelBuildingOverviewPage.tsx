import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Hammer,
  Plus,
  Play,
  Layers,
  FileCheck2,
  ExternalLink,
  Cpu,
} from "lucide-react";
import { fetchBuildRuns, executeLocalSmokeTest } from "../api";
import type { ModelBuildRun } from "../types";
import { ModelBuildWizardModal } from "../components/ModelBuildWizardModal";

export const ModelBuildingOverviewPage: React.FC = () => {
  const { workspaceId = "default-ws" } = useParams<{ workspaceId: string }>();
  const [runs, setRuns] = useState<ModelBuildRun[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [isWizardOpen, setIsWizardOpen] = useState<boolean>(false);
  const [executingRunId, setExecutingRunId] = useState<string | null>(null);

  const loadRuns = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await fetchBuildRuns(
        workspaceId,
        statusFilter === "ALL" ? undefined : statusFilter
      );
      setRuns(data);
    } catch (err) {
      console.error("Failed to load build runs", err);
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId, statusFilter]);

  useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  const handleRunSmokeTest = async (runId: string) => {
    setExecutingRunId(runId);
    try {
      await executeLocalSmokeTest(workspaceId, runId);
      await loadRuns();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Execution error";
      alert(`Local execution failed: ${msg}`);
    } finally {
      setExecutingRunId(null);
    }
  };

  const totalRuns = runs.length;
  const completedRuns = runs.filter((r) => r.status === "COMPLETED").length;
  const stagedArtifactsCount = runs.reduce((acc, r) => acc + (r.staged_artifacts?.length || 0), 0);

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6 sm:p-8 my-6 bg-slate-900 text-slate-100 rounded-2xl border border-slate-800 shadow-xl">
      {/* Page Title & Top Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2.5">
            <Hammer className="h-6 w-6 text-indigo-400" />
            Model Building & Colab Lab
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Reproducible fine-tuning, GGUF/AWQ quantization, and Colab Free exports with $0.00 cloud spend.
          </p>
        </div>

        <button
          onClick={() => setIsWizardOpen(true)}
          data-testid="open-build-wizard-btn"
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors shadow-lg shadow-indigo-950/30"
        >
          <Plus className="h-4 w-4" />
          New Model Build
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Total Build Runs</span>
            <Layers className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100">{totalRuns}</div>
          <p className="text-[11px] text-slate-500 mt-1">Fine-tuning & quantization runs</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Completed Builds</span>
            <FileCheck2 className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100">{completedRuns}</div>
          <p className="text-[11px] text-slate-500 mt-1">Successfully trained / converted</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Staged Model Artifacts</span>
            <Cpu className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100">{stagedArtifactsCount}</div>
          <p className="text-[11px] text-slate-500 mt-1">Staged for M11 release review</p>
        </div>
      </div>

      {/* Status Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 text-xs">
        {["ALL", "COMPLETED", "READY", "RUNNING", "BLOCKED_BY_RESOURCES"].map((st) => (
          <button
            key={st}
            onClick={() => setStatusFilter(st)}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
              statusFilter === st
                ? "bg-indigo-600 text-white"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
            }`}
          >
            {st.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      {/* Runs Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-sm">
        {isLoading ? (
          <div className="p-12 text-center text-slate-500 text-sm">Loading model build runs...</div>
        ) : runs.length === 0 ? (
          <div className="p-12 text-center text-slate-400 space-y-3">
            <Hammer className="mx-auto h-10 w-10 text-slate-600" />
            <p className="text-base font-semibold text-slate-300">No model build runs found</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Launch a build run to fine-tune a parameter-efficient LoRA adapter or quantize a model to GGUF format.
            </p>
            <button
              onClick={() => setIsWizardOpen(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-500 transition-colors"
            >
              <Plus className="h-4 w-4" />
              Configure Build Run
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-950 text-slate-400 uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4 font-semibold">Build Run</th>
                  <th className="py-3 px-4 font-semibold">Recipe</th>
                  <th className="py-3 px-4 font-semibold">Runtime Mode</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Manifest Digest</th>
                  <th className="py-3 px-4 font-semibold">Created</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {runs.map((r) => {
                  const isCompleted = r.status === "COMPLETED";
                  const isReady = r.status === "READY";
                  const isSmokeTest = r.execution_mode === "LOCAL_SMOKE_TEST";

                  return (
                    <tr key={r.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4">
                        <Link
                          to={`/workspaces/${workspaceId}/model-building/${r.id}`}
                          className="font-semibold text-slate-100 hover:text-indigo-400 transition-colors"
                        >
                          {r.name}
                        </Link>
                        {r.description && (
                          <p className="text-[11px] text-slate-500 truncate max-w-xs">{r.description}</p>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-mono text-slate-300">{r.recipe_key}</span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                          {r.execution_mode}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                            isCompleted
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                              : isReady
                              ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                              : r.status === "BLOCKED_BY_RESOURCES"
                              ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                              : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400">
                        {r.manifest_digest.slice(0, 12)}...
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(r.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        {isSmokeTest && isReady && (
                          <button
                            onClick={() => handleRunSmokeTest(r.id)}
                            disabled={executingRunId === r.id}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-medium transition-colors disabled:opacity-50"
                          >
                            <Play className="h-3 w-3" />
                            {executingRunId === r.id ? "Running..." : "Run Smoke Test"}
                          </button>
                        )}

                        <Link
                          to={`/workspaces/${workspaceId}/model-building/${r.id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-slate-700 hover:bg-slate-800 text-slate-300 text-[11px] font-medium transition-colors"
                        >
                          Inspect
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Model Build Wizard Modal */}
      {isWizardOpen && (
        <ModelBuildWizardModal
          workspaceId={workspaceId}
          isOpen={isWizardOpen}
          onClose={() => setIsWizardOpen(false)}
          onRunCreated={() => {
            loadRuns();
          }}
        />
      )}
    </div>
  );
};
