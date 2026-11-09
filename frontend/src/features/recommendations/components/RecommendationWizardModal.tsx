import React, { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  X,
  ChevronRight,
  ChevronLeft,
  Check,
  AlertCircle,
  Sparkles,
  Database,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import {
  fetchObjectives,
  fetchPresets,
  fetchOptimizationProfiles,
  fetchWorkspaceExperiments,
  fetchExperimentDetail,
  validateCandidates,
  createRecommendationRun,
} from "../api";
import type {
  CandidateValidationResult,
  CreateRecommendationRunRequest,
} from "../types";

interface RecommendationWizardModalProps {
  workspaceId: string;
  isOpen: boolean;
  onClose: () => void;
  onRunCreated?: (runId: string) => void;
}

export const RecommendationWizardModal: React.FC<RecommendationWizardModalProps> = ({
  workspaceId,
  isOpen,
  onClose,
  onRunCreated,
}) => {
  const queryClient = useQueryClient();
  const [step, setStep] = useState<number>(1);
  const totalSteps = 8;

  // Step 1: Decision Identity
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedProfileId, setSelectedProfileId] = useState<string>("");

  // Step 2 & 3: Experiments & Candidate Trials
  const [selectedExperimentIds, setSelectedExperimentIds] = useState<string[]>([]);
  const [selectedTrialIds, setSelectedTrialIds] = useState<string[]>([]);
  const [validationResults, setValidationResults] = useState<CandidateValidationResult[]>([]);

  // Step 4: Hard Constraints
  const [constraints, setConstraints] = useState<{
    min_quality_score?: number;
    max_p95_latency_ms?: number;
    max_ram_mb?: number;
    max_budget_usd?: number;
    min_safety_score?: number;
    min_citation_score?: number;
    require_gate1_approval: boolean;
  }>({
    min_quality_score: 75.0,
    max_p95_latency_ms: 3000,
    max_ram_mb: 8192,
    min_safety_score: 80.0,
    require_gate1_approval: true,
  });

  // Step 5: Objectives
  const [selectedObjectives, setSelectedObjectives] = useState<string[]>([
    "aggregate_score",
    "latency_p95_ms",
    "required_ram_mb",
    "estimated_cost_usd",
  ]);

  // Step 6: Weights
  const [weights, setWeights] = useState<Record<string, number>>({
    aggregate_score: 0.4,
    latency_p95_ms: 0.3,
    required_ram_mb: 0.3,
  });
  const [useCustomWeights, setUseCustomWeights] = useState(false);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Queries
  const { data: experimentsData, isLoading: loadingExps } = useQuery({
    queryKey: ["workspace-experiments", workspaceId],
    queryFn: () => fetchWorkspaceExperiments(workspaceId),
    enabled: isOpen && Boolean(workspaceId),
  });

  const { data: objectives = [] } = useQuery({
    queryKey: ["recommendation-objectives", workspaceId],
    queryFn: () => fetchObjectives(workspaceId),
    enabled: isOpen && Boolean(workspaceId),
  });

  const { data: presets = {} } = useQuery({
    queryKey: ["preference-presets", workspaceId],
    queryFn: () => fetchPresets(workspaceId),
    enabled: isOpen && Boolean(workspaceId),
  });

  const { data: profiles = [] } = useQuery({
    queryKey: ["optimization-profiles", workspaceId],
    queryFn: () => fetchOptimizationProfiles(workspaceId),
    enabled: isOpen && Boolean(workspaceId),
  });

  // Fetch trials for selected experiments
  const [experimentTrialsMap, setExperimentTrialsMap] = useState<
    Record<string, Array<{ id: string; trial_number: number; name: string; status: string }>>
  >({});

  useEffect(() => {
    if (!isOpen || selectedExperimentIds.length === 0) return;
    selectedExperimentIds.forEach(async (expId) => {
      if (!experimentTrialsMap[expId]) {
        try {
          const detail = await fetchExperimentDetail(workspaceId, expId);
          setExperimentTrialsMap((prev) => ({
            ...prev,
            [expId]: detail.trials || [],
          }));
        } catch {
          // Ignore
        }
      }
    });
  }, [selectedExperimentIds, isOpen, workspaceId, experimentTrialsMap]);

  // Apply Optimization Profile defaults when selected
  useEffect(() => {
    if (selectedProfileId) {
      const prof = profiles.find((p) => p.id === selectedProfileId);
      if (prof) {
        if (prof.objectives?.length > 0) setSelectedObjectives(prof.objectives);
        if (Object.keys(prof.weights || {}).length > 0) {
          setWeights(prof.weights);
          setUseCustomWeights(true);
        }
        if (prof.constraints) {
          setConstraints((prev) => ({
            ...prev,
            ...(prof.constraints as typeof constraints),
          }));
        }
      }
    }
  }, [selectedProfileId, profiles]);

  // Pre-flight Candidate Validation Mutation
  const validateMutation = useMutation({
    mutationFn: () =>
      validateCandidates(workspaceId, {
        experiment_ids: selectedExperimentIds,
        trial_ids: selectedTrialIds.length > 0 ? selectedTrialIds : undefined,
      }),
    onSuccess: (data) => {
      setValidationResults(data);
    },
    onError: (err: Error) => {
      setErrorMsg(err.message || "Failed to validate candidate trials.");
    },
  });

  // Create & Execute Run Mutation
  const executeMutation = useMutation({
    mutationFn: (req: CreateRecommendationRunRequest) =>
      createRecommendationRun(workspaceId, req),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["recommendation-runs", workspaceId] });
      if (onRunCreated) onRunCreated(data.id);
      onClose();
    },
    onError: (err: Error) => {
      setErrorMsg(err.message || "Execution failed.");
    },
  });

  if (!isOpen) return null;

  const totalWeight = Object.values(weights).reduce((a, b) => a + (Number(b) || 0), 0);
  const isWeightValid = !useCustomWeights || Math.abs(totalWeight - 1.0) <= 0.005;

  const handleNext = () => {
    setErrorMsg(null);
    if (step === 1) {
      if (!name.trim()) {
        setErrorMsg("Please provide a name for this recommendation run.");
        return;
      }
    }
    if (step === 2) {
      if (selectedExperimentIds.length === 0) {
        setErrorMsg("Please select at least one completed experiment.");
        return;
      }
    }
    if (step === 3) {
      // Trigger pre-flight validation
      validateMutation.mutate();
    }
    if (step === 6) {
      if (useCustomWeights && !isWeightValid) {
        setErrorMsg(`Custom weights must sum to 100% (currently ${(totalWeight * 100).toFixed(1)}%).`);
        return;
      }
    }
    setStep((s) => Math.min(s + 1, totalSteps));
  };

  const handleBack = () => {
    setErrorMsg(null);
    setStep((s) => Math.max(s - 1, 1));
  };

  const handleFinish = () => {
    setErrorMsg(null);
    executeMutation.mutate({
      name: name.trim(),
      description: description.trim() || undefined,
      experiment_ids: selectedExperimentIds,
      trial_ids: selectedTrialIds.length > 0 ? selectedTrialIds : undefined,
      optimization_profile_id: selectedProfileId || undefined,
      selected_objectives: selectedObjectives,
      weights: useCustomWeights ? weights : undefined,
      hard_constraints: constraints,
    });
  };

  const applyPreset = (presetKey: string) => {
    const pWeights = presets[presetKey];
    if (pWeights) {
      setWeights(pWeights);
      setUseCustomWeights(true);
    }
  };

  const completedExperiments =
    experimentsData?.items.filter((e) => e.status === "COMPLETED") || [];

  return (
    <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl w-full max-w-3xl overflow-hidden shadow-2xl my-8">
        {/* Wizard Header */}
        <div className="flex items-center justify-between p-6 border-b border-neutral-800 bg-neutral-950/60">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-500" />
              <h2 className="text-base font-semibold text-neutral-100">
                New Recommendation Run &amp; Pareto Matrix
              </h2>
            </div>
            <p className="text-xs text-neutral-400 mt-0.5">
              Step {step} of {totalSteps}: {getStepTitle(step)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Wizard Progress Bar */}
        <div className="w-full bg-neutral-800 h-1">
          <div
            className="bg-emerald-500 h-full transition-all duration-300"
            style={{ width: `${(step / totalSteps) * 100}%` }}
          />
        </div>

        {/* Wizard Body */}
        <div className="p-6 min-h-[380px] max-h-[70vh] overflow-y-auto">
          {errorMsg && (
            <div className="p-3 mb-4 bg-red-950/50 border border-red-800 rounded-lg text-xs text-red-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* STEP 1: Identify the Decision */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-neutral-300">
                  Recommendation Run Name *
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Q4 Sovereign RAG Architecture Decision"
                  className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-sm text-neutral-100 focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-neutral-300">
                  Business Objective &amp; Description
                </label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Evaluate trade-offs between local CPU quantized models vs quality on customer service evaluation suite"
                  className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-xs text-neutral-100 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="space-y-1.5 pt-2">
                <label className="text-xs font-medium text-neutral-300">
                  Load Saved Preference Profile (Optional)
                </label>
                <select
                  value={selectedProfileId}
                  onChange={(e) => setSelectedProfileId(e.target.value)}
                  className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-xs text-neutral-100 focus:outline-none focus:border-emerald-500"
                >
                  <option value="">None (Configure custom weights &amp; constraints)</option>
                  {profiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} (v{p.version})
                    </option>
                  ))}
                </select>
                <span className="text-[11px] text-neutral-500 block">
                  Profiles pre-populate target objectives, weights, and constraints.
                </span>
              </div>
            </div>
          )}

          {/* STEP 2: Select Experiments */}
          {step === 2 && (
            <div className="space-y-3">
              <p className="text-xs text-neutral-400">
                Select completed M7 experiments from this workspace to draw candidate trial configurations from:
              </p>
              {loadingExps ? (
                <div className="p-8 text-center text-xs text-neutral-500 animate-pulse">
                  Loading workspace experiments...
                </div>
              ) : completedExperiments.length === 0 ? (
                <div className="p-8 border border-neutral-800 rounded-lg bg-neutral-950/40 text-center space-y-2">
                  <Database className="w-8 h-8 text-neutral-600 mx-auto" />
                  <p className="text-sm font-medium text-neutral-300">No Completed Experiments</p>
                  <p className="text-xs text-neutral-500">
                    At least one completed M7 experiment with verified trials is required to produce recommendation evidence.
                  </p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {completedExperiments.map((exp) => {
                    const isSelected = selectedExperimentIds.includes(exp.id);
                    return (
                      <label
                        key={exp.id}
                        className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                          isSelected
                            ? "border-emerald-800 bg-emerald-950/20"
                            : "border-neutral-800 bg-neutral-950/40 hover:bg-neutral-900/60"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => {
                            if (isSelected) {
                              setSelectedExperimentIds((prev) => prev.filter((id) => id !== exp.id));
                            } else {
                              setSelectedExperimentIds((prev) => [...prev, exp.id]);
                            }
                          }}
                          className="mt-0.5 rounded border-neutral-700 bg-neutral-900 text-emerald-500 focus:ring-emerald-500"
                        />
                        <div className="space-y-0.5">
                          <span className="text-xs font-semibold text-neutral-200 block">
                            {exp.name}
                          </span>
                          <span className="text-[11px] text-neutral-500 font-mono block">
                            Model: {exp.target_model || "Configured"} | Split: {exp.evaluation_split || "DEV"}
                          </span>
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* STEP 3: Select Candidates */}
          {step === 3 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs text-neutral-400">
                  Select specific trials or leave all selected for comprehensive cohort optimization:
                </p>
                <button
                  type="button"
                  onClick={() => setSelectedTrialIds([])}
                  className="text-[11px] text-emerald-400 hover:underline"
                >
                  Select All Completed Trials
                </button>
              </div>

              <div className="space-y-3 max-h-[300px] overflow-y-auto">
                {selectedExperimentIds.map((expId) => {
                  const trials = experimentTrialsMap[expId] || [];
                  const expObj = completedExperiments.find((e) => e.id === expId);
                  return (
                    <div key={expId} className="border border-neutral-800 rounded-lg p-3 bg-neutral-950/30 space-y-2">
                      <span className="text-xs font-semibold text-neutral-300 block">
                        Experiment: {expObj?.name || expId}
                      </span>
                      {trials.length === 0 ? (
                        <span className="text-[11px] text-neutral-500">Loading trials...</span>
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {trials.map((t) => {
                            const isSelected =
                              selectedTrialIds.length === 0 || selectedTrialIds.includes(t.id);
                            return (
                              <label
                                key={t.id}
                                className={`flex items-center gap-2 p-2 rounded border text-xs cursor-pointer ${
                                  isSelected
                                    ? "border-emerald-800/80 bg-emerald-950/30 text-neutral-200"
                                    : "border-neutral-800 bg-neutral-900/40 text-neutral-500"
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => {
                                    if (selectedTrialIds.length === 0) {
                                      // Switching from "all" to subset
                                      const allIds = trials.map((x) => x.id);
                                      setSelectedTrialIds(allIds.filter((id) => id !== t.id));
                                    } else if (selectedTrialIds.includes(t.id)) {
                                      setSelectedTrialIds((prev) => prev.filter((id) => id !== t.id));
                                    } else {
                                      setSelectedTrialIds((prev) => [...prev, t.id]);
                                    }
                                  }}
                                  className="rounded border-neutral-700 bg-neutral-900 text-emerald-500 focus:ring-emerald-500"
                                />
                                <span className="truncate font-medium">
                                  #{t.trial_number}: {t.name}
                                </span>
                              </label>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* STEP 4: Define Hard Constraints */}
          {step === 4 && (
            <div className="space-y-4">
              <p className="text-xs text-neutral-400">
                Non-negotiable thresholds evaluated BEFORE multi-objective optimization. Failing configurations cannot participate in the Pareto frontier:
              </p>

              <div className="grid grid-cols-2 gap-4 text-xs">
                <div className="space-y-1">
                  <label className="text-neutral-300 font-medium">Min Quality Score (pts)</label>
                  <input
                    type="number"
                    value={constraints.min_quality_score ?? ""}
                    onChange={(e) =>
                      setConstraints((prev) => ({
                        ...prev,
                        min_quality_score: e.target.value ? parseFloat(e.target.value) : undefined,
                      }))
                    }
                    className="w-full px-3 py-1.5 bg-neutral-950 border border-neutral-800 rounded-lg text-neutral-100"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-neutral-300 font-medium">Max P95 Tail Latency (ms)</label>
                  <input
                    type="number"
                    value={constraints.max_p95_latency_ms ?? ""}
                    onChange={(e) =>
                      setConstraints((prev) => ({
                        ...prev,
                        max_p95_latency_ms: e.target.value ? parseFloat(e.target.value) : undefined,
                      }))
                    }
                    className="w-full px-3 py-1.5 bg-neutral-950 border border-neutral-800 rounded-lg text-neutral-100"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-neutral-300 font-medium">Max System RAM Limit (MB)</label>
                  <input
                    type="number"
                    value={constraints.max_ram_mb ?? ""}
                    onChange={(e) =>
                      setConstraints((prev) => ({
                        ...prev,
                        max_ram_mb: e.target.value ? parseFloat(e.target.value) : undefined,
                      }))
                    }
                    className="w-full px-3 py-1.5 bg-neutral-950 border border-neutral-800 rounded-lg text-neutral-100"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-neutral-300 font-medium">Max Budget Cap (USD)</label>
                  <input
                    type="number"
                    value={constraints.max_budget_usd ?? ""}
                    onChange={(e) =>
                      setConstraints((prev) => ({
                        ...prev,
                        max_budget_usd: e.target.value ? parseFloat(e.target.value) : undefined,
                      }))
                    }
                    placeholder="e.g. 10.00 (unknown cost fails closed)"
                    className="w-full px-3 py-1.5 bg-neutral-950 border border-neutral-800 rounded-lg text-neutral-100"
                  />
                </div>
              </div>

              <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-lg space-y-2 pt-2">
                <label className="flex items-center gap-2 cursor-pointer text-xs text-neutral-300">
                  <input
                    type="checkbox"
                    checked={constraints.require_gate1_approval}
                    onChange={(e) =>
                      setConstraints((prev) => ({
                        ...prev,
                        require_gate1_approval: e.target.checked,
                      }))
                    }
                    className="rounded border-neutral-700 bg-neutral-900 text-emerald-500 focus:ring-emerald-500"
                  />
                  <span>Enforce Gate 1 Approval Attestation (Mandatory Privacy Guard)</span>
                </label>
              </div>
            </div>
          )}

          {/* STEP 5: Select Objectives */}
          {step === 5 && (
            <div className="space-y-3">
              <p className="text-xs text-neutral-400">
                Select dimensions for multi-objective optimization and Pareto dominance evaluation:
              </p>

              <div className="space-y-2 border border-neutral-800 rounded-lg p-3 bg-neutral-950/40 max-h-[300px] overflow-y-auto">
                {objectives.map((obj) => {
                  const isChecked = selectedObjectives.includes(obj.key);
                  return (
                    <label
                      key={obj.key}
                      className="flex items-start justify-between gap-3 p-2 rounded hover:bg-neutral-900/50 cursor-pointer"
                    >
                      <div className="flex items-start gap-2">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {
                            if (isChecked) {
                              if (selectedObjectives.length > 1) {
                                setSelectedObjectives((prev) => prev.filter((k) => k !== obj.key));
                              }
                            } else {
                              setSelectedObjectives((prev) => [...prev, obj.key]);
                            }
                          }}
                          className="mt-0.5 rounded border-neutral-700 bg-neutral-900 text-emerald-500 focus:ring-emerald-500"
                        />
                        <div className="space-y-0.5">
                          <span className="text-xs font-semibold text-neutral-200 block">
                            {obj.display_name} ({obj.unit})
                          </span>
                          <span className="text-[11px] text-neutral-400 block">
                            {obj.description}
                          </span>
                        </div>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-neutral-800 text-neutral-400 font-mono shrink-0">
                        {obj.direction}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          {/* STEP 6: Preferences / Weights */}
          {step === 6 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-xs text-neutral-400">
                  Optionally configure preference weights. Pareto analysis runs regardless of whether weights are set:
                </p>
                <button
                  type="button"
                  onClick={() => setUseCustomWeights(!useCustomWeights)}
                  className="text-xs text-emerald-400 hover:underline"
                >
                  {useCustomWeights ? "Disable Weights (Pure Pareto)" : "Enable Weighted Scoring"}
                </button>
              </div>

              {useCustomWeights && (
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    {Object.keys(presets).map((pKey) => (
                      <button
                        key={pKey}
                        type="button"
                        onClick={() => applyPreset(pKey)}
                        className="px-2.5 py-1 text-xs bg-neutral-800 hover:bg-neutral-700 text-neutral-200 rounded border border-neutral-700 transition-colors"
                      >
                        {pKey.replace(/_/g, " ")}
                      </button>
                    ))}
                  </div>

                  <div className="space-y-2 border border-neutral-800 rounded-lg p-3 bg-neutral-950/40">
                    {selectedObjectives.map((objKey) => {
                      const wVal = weights[objKey] ?? 0;
                      return (
                        <div key={objKey} className="flex items-center justify-between gap-3 text-xs">
                          <span className="text-neutral-300 font-medium truncate max-w-[200px]">
                            {objKey.replace(/_/g, " ")}
                          </span>
                          <div className="flex items-center gap-2">
                            <input
                              type="number"
                              min="0"
                              max="1"
                              step="0.05"
                              value={wVal}
                              onChange={(e) =>
                                setWeights((prev) => ({
                                  ...prev,
                                  [objKey]: parseFloat(e.target.value) || 0,
                                }))
                              }
                              className="w-16 px-2 py-0.5 bg-neutral-900 border border-neutral-700 rounded text-right font-mono text-neutral-100"
                            />
                            <span className="text-[10px] text-neutral-500 w-8">
                              {(wVal * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="flex justify-end">
                    <span
                      className={`text-xs font-mono font-medium ${
                        isWeightValid ? "text-emerald-400" : "text-amber-400"
                      }`}
                    >
                      Total Weight: {(totalWeight * 100).toFixed(1)}% / 100%
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 7: Pre-Flight Review */}
          {step === 7 && (
            <div className="space-y-4">
              <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-lg space-y-2 text-xs">
                <span className="font-semibold text-neutral-200 block">Pre-Flight Summary</span>
                <div className="grid grid-cols-2 gap-2 text-neutral-400">
                  <div>Name: <span className="text-neutral-200 font-medium">{name}</span></div>
                  <div>Selected Experiments: <span className="text-neutral-200 font-medium">{selectedExperimentIds.length}</span></div>
                  <div>Selected Objectives: <span className="text-neutral-200 font-medium">{selectedObjectives.length}</span></div>
                  <div>Weights Mode: <span className="text-neutral-200 font-medium">{useCustomWeights ? "Custom Preference Weights" : "Pure Pareto"}</span></div>
                </div>
              </div>

              {/* Pre-flight Candidate Validation Results */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-neutral-300 block">
                  Candidate Cohort Pre-flight Inspection ({validationResults.length} candidates)
                </span>
                <div className="border border-neutral-800 rounded-lg overflow-x-auto max-h-[180px] bg-neutral-950/40">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-neutral-800 bg-neutral-900/50 text-neutral-400">
                        <th className="py-2 px-3">Candidate</th>
                        <th className="py-2 px-3">Trial Status</th>
                        <th className="py-2 px-3">Eligibility</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-800/40">
                      {validationResults.map((vr) => (
                        <tr key={vr.trial_id}>
                          <td className="py-1.5 px-3 font-medium text-neutral-200">
                            {vr.candidate_label}
                          </td>
                          <td className="py-1.5 px-3 font-mono text-[11px] text-neutral-400">
                            {vr.trial_status}
                          </td>
                          <td className="py-1.5 px-3">
                            {vr.is_eligible ? (
                              <span className="text-emerald-400 font-medium text-[11px] inline-flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3" /> Eligible
                              </span>
                            ) : (
                              <span className="text-red-400 font-medium text-[11px] inline-flex items-center gap-1">
                                <XCircle className="w-3 h-3" /> Ineligible: {vr.exclusion_reasons[0] || ""}
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Free-Only Policy Notice */}
              <div className="p-3 bg-neutral-950/80 border border-neutral-800 rounded-lg text-[11px] text-neutral-400">
                <strong>Free-Only Policy Guarantee:</strong> Calculations execute deterministically on local CPU. Zero cloud spend ($0.00) will be incurred.
              </div>
            </div>
          )}

          {/* STEP 8: Calculate & Execute */}
          {step === 8 && (
            <div className="space-y-6 text-center py-6">
              <Sparkles className="w-12 h-12 text-emerald-500 mx-auto animate-pulse" />
              <div className="space-y-1">
                <h3 className="text-base font-semibold text-neutral-100">
                  Ready to Compute Pareto Frontier
                </h3>
                <p className="text-xs text-neutral-400 max-w-md mx-auto">
                  Clicking calculate will normalize metrics, compute multi-objective dominance, evaluate preference scoring, and synthesize deterministic explanations.
                </p>
              </div>

              <div className="inline-block p-4 border border-neutral-800 rounded-lg bg-neutral-950/60 text-xs text-neutral-400 text-left font-mono">
                <div>&bull; Candidates: {validationResults.length} trial configurations</div>
                <div>&bull; Objectives: {selectedObjectives.join(", ")}</div>
                <div>&bull; Algorithm: Deterministic Pareto Frontier v1.0.0</div>
                <div>&bull; Expected Expenditure: $0.00</div>
              </div>
            </div>
          )}
        </div>

        {/* Wizard Footer Controls */}
        <div className="flex items-center justify-between p-4 border-t border-neutral-800 bg-neutral-950/60">
          <button
            type="button"
            onClick={handleBack}
            disabled={step === 1 || executeMutation.isPending}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs text-neutral-400 hover:text-neutral-200 disabled:opacity-30 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" /> Back
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs text-neutral-400 hover:text-neutral-200 transition-colors"
            >
              Cancel
            </button>
            {step < totalSteps ? (
              <button
                type="button"
                onClick={handleNext}
                disabled={validateMutation.isPending}
                className="inline-flex items-center gap-1 px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors"
              >
                Next <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleFinish}
                disabled={executeMutation.isPending}
                className="inline-flex items-center gap-1.5 px-5 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition-colors shadow-lg shadow-emerald-950/40"
              >
                <Check className="w-4 h-4" />
                {executeMutation.isPending ? "Executing Optimization..." : "Execute Recommendation"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

function getStepTitle(step: number): string {
  switch (step) {
    case 1:
      return "Identify Decision & Objective";
    case 2:
      return "Select Source Experiments";
    case 3:
      return "Filter Candidate Trials";
    case 4:
      return "Define Hard Constraints";
    case 5:
      return "Select Optimization Objectives";
    case 6:
      return "User Preference Weights";
    case 7:
      return "Pre-Flight Cohort Review";
    case 8:
      return "Compute & Finalize";
    default:
      return "";
  }
}
