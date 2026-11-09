import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  X,
  ArrowRight,
  ArrowLeft,
  Hammer,
  Database,
  Sliders,
  CheckCircle2,
} from "lucide-react";
import type {
  ModelSource,
  ModelBuildRecipe,
  BuildPreflightResponse,
  ExecutionMode,
  ExternalAuthorization,
} from "../types";
import {
  fetchModelSources,
  fetchBuildRecipes,
  runBuildPreflight,
  createBuildRun,
  fetchExternalAuthorizations,
} from "../api";
import { ResourcePreflightCard } from "./ResourcePreflightCard";
import { ExternalProcessingModal } from "./ExternalProcessingModal";

interface ModelBuildWizardModalProps {
  workspaceId: string;
  isOpen: boolean;
  onClose: () => void;
  onRunCreated: (runId: string) => void;
}

export const ModelBuildWizardModal: React.FC<ModelBuildWizardModalProps> = ({
  workspaceId,
  isOpen,
  onClose,
  onRunCreated,
}) => {
  const [step, setStep] = useState<number>(1);
  const [models, setModels] = useState<ModelSource[]>([]);
  const [recipes, setRecipes] = useState<ModelBuildRecipe[]>([]);
  const [authorizations, setAuthorizations] = useState<ExternalAuthorization[]>([]);

  // Wizard state
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  const [selectedRecipeId, setSelectedRecipeId] = useState<string>("");
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("LOCAL_SMOKE_TEST");
  const [runName, setRunName] = useState<string>("");
  const [runDescription, setRunDescription] = useState<string>("");
  const [datasetId, setDatasetId] = useState<string>("");
  const [datasetVersionId, setDatasetVersionId] = useState<string>("");
  const [externalAuthId, setExternalAuthId] = useState<string>("");
  const [trainingConfig, setTrainingConfig] = useState<Record<string, unknown>>({});

  // Preflight state
  const [preflight, setPreflight] = useState<BuildPreflightResponse | null>(null);
  const [isPreflightLoading, setIsPreflightLoading] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // External Auth Modal state
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);

  const loadInitialData = useCallback(async () => {
    try {
      const [mList, rList, aList] = await Promise.all([
        fetchModelSources(workspaceId),
        fetchBuildRecipes(workspaceId),
        fetchExternalAuthorizations(workspaceId),
      ]);
      setModels(mList);
      setRecipes(rList);
      setAuthorizations(aList);

      if (mList.length > 0) {
        setSelectedModelId((current) => current || mList[0].id);
      }
      if (rList.length > 0) {
        setSelectedRecipeId((current) => current || rList[0].id);
        setTrainingConfig((current) =>
          Object.keys(current).length > 0 ? current : rList[0].default_config || {}
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setErrorMessage("Failed to load catalog or recipes: " + msg);
    }
  }, [workspaceId]);

  useEffect(() => {
    if (isOpen) {
      void loadInitialData();
    }
  }, [isOpen, loadInitialData]);

  const selectedModel = useMemo(
    () => models.find((model) => model.id === selectedModelId),
    [models, selectedModelId]
  );
  const selectedRecipe = useMemo(
    () => recipes.find((recipe) => recipe.id === selectedRecipeId),
    [recipes, selectedRecipeId]
  );

  useEffect(() => {
    if (selectedRecipe) {
      if (selectedRecipe.is_executable_locally) {
        setExecutionMode("LOCAL_SMOKE_TEST");
      } else {
        setExecutionMode("MANUAL_COLAB_NOTEBOOK");
      }
      setTrainingConfig(selectedRecipe.default_config || {});
    }
  }, [selectedRecipe]);

  const handleCalculatePreflight = useCallback(async () => {
    if (!selectedModelId || !selectedRecipeId) return;
    setIsPreflightLoading(true);
    setErrorMessage(null);
    try {
      const res = await runBuildPreflight(workspaceId, {
        model_id: selectedModelId,
        recipe_id: selectedRecipeId,
        execution_mode: executionMode,
      });
      setPreflight(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Preflight failed";
      setErrorMessage("Preflight check failed: " + msg);
    } finally {
      setIsPreflightLoading(false);
    }
  }, [executionMode, selectedModelId, selectedRecipeId, workspaceId]);

  useEffect(() => {
    if (step === 4 && selectedModelId && selectedRecipeId) {
      void handleCalculatePreflight();
    }
  }, [step, selectedModelId, selectedRecipeId, handleCalculatePreflight]);

  const handleNextStep = () => {
    if (step === 1 && !runName.trim()) {
      setRunName(`${selectedModel?.name || "Model"} - ${selectedRecipe?.name || "Build"}`);
    }
    setStep((prev) => Math.min(prev + 1, 5));
  };

  const handlePrevStep = () => {
    setStep((prev) => Math.max(prev - 1, 1));
  };

  const handleSubmitBuildRun = async () => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const run = await createBuildRun(workspaceId, {
        name: runName || `${selectedModel?.name} Build`,
        description: runDescription,
        source_model_id: selectedModelId,
        recipe_id: selectedRecipeId,
        execution_mode: executionMode,
        dataset_id: datasetId || undefined,
        dataset_version_id: datasetVersionId || undefined,
        external_authorization_id: externalAuthId || undefined,
        training_config: trainingConfig,
      });
      onRunCreated(run.id);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create model build run";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-3xl bg-slate-900 border border-slate-700 rounded-xl shadow-2xl flex flex-col max-h-[90vh]">
        {/* Wizard Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Hammer className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">
                New Model Build & Adaptation Run
              </h2>
              <p className="text-xs text-slate-400">
                Step {step} of 5 · Reproducible recipes with $0.00 additional spend
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Wizard Progress Tabs */}
        <div className="grid grid-cols-5 border-b border-slate-800 text-xs font-medium text-slate-400">
          <div className={`py-2.5 px-3 text-center border-b-2 ${step === 1 ? "border-indigo-500 text-indigo-300 font-semibold" : "border-transparent"}`}>
            1. Model & Source
          </div>
          <div className={`py-2.5 px-3 text-center border-b-2 ${step === 2 ? "border-indigo-500 text-indigo-300 font-semibold" : "border-transparent"}`}>
            2. Build Recipe
          </div>
          <div className={`py-2.5 px-3 text-center border-b-2 ${step === 3 ? "border-indigo-500 text-indigo-300 font-semibold" : "border-transparent"}`}>
            3. Training Config
          </div>
          <div className={`py-2.5 px-3 text-center border-b-2 ${step === 4 ? "border-indigo-500 text-indigo-300 font-semibold" : "border-transparent"}`}>
            4. Preflight
          </div>
          <div className={`py-2.5 px-3 text-center border-b-2 ${step === 5 ? "border-indigo-500 text-indigo-300 font-semibold" : "border-transparent"}`}>
            5. Review & Launch
          </div>
        </div>

        {/* Wizard Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {errorMessage && (
            <div className="rounded-md bg-rose-950/40 border border-rose-500/40 p-3 text-xs text-rose-300">
              {errorMessage}
            </div>
          )}

          {/* STEP 1: Model Selection */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Build Run Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. SmolLM2 135M Fine-Tuned Support Adapter"
                  value={runName}
                  onChange={(e) => setRunName(e.target.value)}
                  className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Description (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Fine-tuned with LoRA r=16 on masked dataset"
                  value={runDescription}
                  onChange={(e) => setRunDescription(e.target.value)}
                  className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2">
                  Select Base Model from Curated Open Catalog
                </label>
                <div className="grid gap-2.5">
                  {models.map((m) => (
                    <label
                      key={m.id}
                      className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                        selectedModelId === m.id
                          ? "border-indigo-500 bg-indigo-950/20"
                          : "border-slate-800 bg-slate-800/40 hover:border-slate-700"
                      }`}
                    >
                      <input
                        type="radio"
                        name="modelSelection"
                        checked={selectedModelId === m.id}
                        onChange={() => setSelectedModelId(m.id)}
                        className="mt-1 text-indigo-600 focus:ring-indigo-500"
                      />
                      <div className="flex-1 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-200">{m.name}</span>
                          <span className="font-mono text-[11px] text-slate-400">
                            {m.parameter_count_millions}M params
                          </span>
                        </div>
                        <p className="text-slate-400 mt-0.5">{m.description}</p>
                        <div className="flex flex-wrap items-center gap-2 mt-2">
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                            License: {m.license_id}
                          </span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                            Arch: {m.architecture}
                          </span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Status: {m.license_status}
                          </span>
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: Recipe Selection */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2">
                  Select Build Recipe & Target Execution Runtime
                </label>
                <div className="grid gap-2.5">
                  {recipes.map((r) => (
                    <label
                      key={r.id}
                      className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                        selectedRecipeId === r.id
                          ? "border-indigo-500 bg-indigo-950/20"
                          : "border-slate-800 bg-slate-800/40 hover:border-slate-700"
                      }`}
                    >
                      <input
                        type="radio"
                        name="recipeSelection"
                        checked={selectedRecipeId === r.id}
                        onChange={() => setSelectedRecipeId(r.id)}
                        className="mt-1 text-indigo-600 focus:ring-indigo-500"
                      />
                      <div className="flex-1 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-200">{r.name}</span>
                          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                            {r.recipe_type}
                          </span>
                        </div>
                        <p className="text-slate-400 mt-1">{r.description}</p>
                        <div className="flex items-center gap-2 mt-2">
                          {r.is_executable_locally ? (
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              Local Host Execution ($0 spend)
                            </span>
                          ) : (
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-400 border border-blue-500/20">
                              Google Colab Free (T4 GPU · $0 spend)
                            </span>
                          )}
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700">
                            v{r.recipe_version}
                          </span>
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: Training & Hyperparameter Configuration */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="rounded-lg border border-slate-800 bg-slate-800/40 p-4 space-y-3">
                <h4 className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                  <Sliders className="h-4 w-4 text-indigo-400" />
                  Hyperparameters for {selectedRecipe?.name}
                </h4>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="block text-slate-400 mb-1">Learning Rate</label>
                    <input
                      type="number"
                      step="0.00001"
                      value={Number(trainingConfig.learning_rate ?? 0.0002)}
                      onChange={(e) =>
                        setTrainingConfig({ ...trainingConfig, learning_rate: parseFloat(e.target.value) })
                      }
                      className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-slate-200"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1">Max Steps</label>
                    <input
                      type="number"
                      value={Number(trainingConfig.max_steps ?? 100)}
                      onChange={(e) =>
                        setTrainingConfig({ ...trainingConfig, max_steps: parseInt(e.target.value, 10) })
                      }
                      className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-slate-200"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1">Batch Size</label>
                    <input
                      type="number"
                      value={Number(trainingConfig.batch_size ?? 2)}
                      onChange={(e) =>
                        setTrainingConfig({ ...trainingConfig, batch_size: parseInt(e.target.value, 10) })
                      }
                      className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-slate-200"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1">LoRA Rank (r)</label>
                    <input
                      type="number"
                      value={Number(trainingConfig.lora_rank ?? 16)}
                      onChange={(e) =>
                        setTrainingConfig({ ...trainingConfig, lora_rank: parseInt(e.target.value, 10) })
                      }
                      className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-slate-200"
                    />
                  </div>
                </div>
              </div>

              {/* Sensitive Data Notice */}
              <div className="rounded-lg border border-slate-800 bg-slate-800/40 p-4 space-y-2">
                <h4 className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                  <Database className="h-4 w-4 text-emerald-400" />
                  Dataset & Gate 1 Attestation (Optional for Smoke Tests)
                </h4>
                <p className="text-xs text-slate-400">
                  Model training strictly requires Gate 1 approved masked datasets. Never use raw or unmasked data.
                </p>

                <div className="grid grid-cols-2 gap-3 text-xs pt-1">
                  <div>
                    <label className="block text-slate-400 mb-1">Dataset ID</label>
                    <input
                      type="text"
                      placeholder="Optional dataset ID"
                      value={datasetId}
                      onChange={(e) => setDatasetId(e.target.value)}
                      className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-slate-200"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1">Dataset Version ID</label>
                    <input
                      type="text"
                      placeholder="Optional version ID"
                      value={datasetVersionId}
                      onChange={(e) => setDatasetVersionId(e.target.value)}
                      className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-slate-200"
                    />
                  </div>
                </div>

                {executionMode === "MANUAL_COLAB_NOTEBOOK" && (
                  <div className="pt-2">
                    {authorizations.length > 0 && (
                      <div className="mb-2">
                        <label className="block text-[11px] text-slate-400 mb-1">Select Active Authorization</label>
                        <select
                          value={externalAuthId}
                          onChange={(e) => setExternalAuthId(e.target.value)}
                          className="w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200"
                        >
                          <option value="">-- Choose Existing Authorization --</option>
                          {authorizations.map((a) => (
                            <option key={a.id} value={a.id}>
                              {a.purpose} (Expires: {new Date(a.expires_at).toLocaleDateString()})
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={() => setShowAuthModal(true)}
                      className="text-xs px-3 py-1.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 hover:bg-amber-500/20 transition-colors"
                    >
                      Authorize New Colab Dataset Export
                    </button>
                    {externalAuthId && (
                      <span className="ml-2 text-xs text-emerald-400 font-medium">
                        ✓ Authorization Linked
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* STEP 4: Preflight Check */}
          {step === 4 && (
            <div className="space-y-4">
              <ResourcePreflightCard preflight={preflight} isLoading={isPreflightLoading} />
            </div>
          )}

          {/* STEP 5: Review & Launch */}
          {step === 5 && (
            <div className="space-y-4 text-xs">
              <div className="rounded-lg border border-slate-800 bg-slate-800/60 p-4 space-y-2">
                <h4 className="font-semibold text-slate-200">Build Run Summary</h4>
                <div className="grid grid-cols-2 gap-2 text-slate-300 pt-1">
                  <div>Model: <span className="font-semibold text-slate-100">{selectedModel?.name}</span></div>
                  <div>Recipe: <span className="font-semibold text-slate-100">{selectedRecipe?.name}</span></div>
                  <div>Runtime: <span className="font-mono text-slate-100">{executionMode}</span></div>
                  <div>Estimated RAM: <span className="text-slate-100">{preflight?.peak_memory_mb} MB</span></div>
                </div>
              </div>

              <div className="rounded-md border border-emerald-500/30 bg-emerald-950/20 p-3 flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 mt-0.5 shrink-0" />
                <span className="text-emerald-200">
                  Ready to construct canonical build manifest (RFC 8785). Checkpoints and outputs will be cryptographically hashed.
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Wizard Footer */}
        <div className="border-t border-slate-800 px-6 py-4 flex items-center justify-between">
          <button
            type="button"
            onClick={step === 1 ? onClose : handlePrevStep}
            className="flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            {step === 1 ? "Cancel" : "Back"}
          </button>

          {step < 5 ? (
            <button
              type="button"
              onClick={handleNextStep}
              className="flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
            >
              Next
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmitBuildRun}
              disabled={Boolean(isSubmitting || (preflight && !preflight.is_feasible))}
              data-testid="create-build-run-btn"
              className="flex items-center gap-1.5 px-5 py-2 rounded-md text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors disabled:opacity-50"
            >
              <Hammer className="h-3.5 w-3.5" />
              {isSubmitting ? "Generating Manifest..." : "Create Build Run"}
            </button>
          )}
        </div>
      </div>

      {showAuthModal && (
        <ExternalProcessingModal
          workspaceId={workspaceId}
          datasetId={datasetId || "ds-default"}
          datasetVersionId={datasetVersionId || "dsv-default"}
          isOpen={showAuthModal}
          onClose={() => setShowAuthModal(false)}
          onAuthorized={(auth) => {
            setExternalAuthId(auth.id);
            setShowAuthModal(false);
          }}
        />
      )}
    </div>
  );
};
