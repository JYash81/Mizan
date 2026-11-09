import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, X, Sliders, Check, AlertCircle } from "lucide-react";
import {
  fetchOptimizationProfiles,
  createOptimizationProfile,
  deleteOptimizationProfile,
  fetchObjectives,
  fetchPresets,
} from "../api";

interface OptimizationProfilesManagerProps {
  workspaceId: string;
  isOpen: boolean;
  onClose: () => void;
}

export const OptimizationProfilesManager: React.FC<OptimizationProfilesManagerProps> = ({
  workspaceId,
  isOpen,
  onClose,
}) => {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedObjectives, setSelectedObjectives] = useState<string[]>([
    "aggregate_score",
    "latency_p95_ms",
    "required_ram_mb",
  ]);
  const [weights, setWeights] = useState<Record<string, number>>({
    aggregate_score: 0.5,
    latency_p95_ms: 0.25,
    required_ram_mb: 0.25,
  });
  const [constraints, setConstraints] = useState<{
    min_quality_score?: number;
    max_p95_latency_ms?: number;
    max_ram_mb?: number;
    max_budget_usd?: number;
    require_gate1_approval: boolean;
  }>({
    min_quality_score: 75.0,
    max_p95_latency_ms: 2500,
    max_ram_mb: 8192,
    require_gate1_approval: true,
  });
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data: profiles = [], isLoading } = useQuery({
    queryKey: ["optimization-profiles", workspaceId],
    queryFn: () => fetchOptimizationProfiles(workspaceId),
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

  const createMutation = useMutation({
    mutationFn: (req: Parameters<typeof createOptimizationProfile>[1]) =>
      createOptimizationProfile(workspaceId, req),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["optimization-profiles", workspaceId] });
      setShowCreate(false);
      setName("");
      setDescription("");
      setErrorMsg(null);
    },
    onError: (err: Error) => {
      setErrorMsg(err.message || "Failed to create profile.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (profileId: string) => deleteOptimizationProfile(workspaceId, profileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["optimization-profiles", workspaceId] });
    },
  });

  if (!isOpen) return null;

  const totalWeight = Object.values(weights).reduce((a, b) => a + (Number(b) || 0), 0);
  const isWeightValid = Math.abs(totalWeight - 1.0) <= 0.005;

  const applyPreset = (presetKey: string) => {
    const pWeights = presets[presetKey];
    if (pWeights) {
      setWeights(pWeights);
      setSelectedObjectives(Object.keys(pWeights));
    }
  };

  const handleObjectiveToggle = (key: string) => {
    if (selectedObjectives.includes(key)) {
      if (selectedObjectives.length === 1) return; // Keep at least one
      const nextObjs = selectedObjectives.filter((k) => k !== key);
      setSelectedObjectives(nextObjs);
      const nextWeights = { ...weights };
      delete nextWeights[key];
      // Normalize remainder
      const sum = Object.values(nextWeights).reduce((a, b) => a + b, 0);
      if (sum > 0) {
        Object.keys(nextWeights).forEach((k) => {
          nextWeights[k] = Number((nextWeights[k] / sum).toFixed(2));
        });
      }
      setWeights(nextWeights);
    } else {
      const nextObjs = [...selectedObjectives, key];
      setSelectedObjectives(nextObjs);
      // Give it equal share
      const share = Number((1.0 / nextObjs.length).toFixed(2));
      const nextWeights: Record<string, number> = {};
      nextObjs.forEach((k) => {
        nextWeights[k] = share;
      });
      setWeights(nextWeights);
    }
  };

  const handleWeightChange = (key: string, val: number) => {
    setWeights((prev) => ({
      ...prev,
      [key]: val,
    }));
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMsg("Profile name is required.");
      return;
    }
    if (!isWeightValid) {
      setErrorMsg(`Weights must sum to 1.0 (currently ${totalWeight.toFixed(2)}).`);
      return;
    }
    createMutation.mutate({
      name: name.trim(),
      description: description.trim() || undefined,
      objectives: selectedObjectives,
      weights,
      constraints,
      budget_currency: "USD",
    });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl w-full max-w-2xl overflow-hidden shadow-2xl my-8">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-neutral-800">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-emerald-500" />
            <h2 className="text-lg font-semibold text-neutral-100">
              Workspace Optimization Preference Profiles
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {!showCreate ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-xs text-neutral-400">
                  Reusable preference weightings and hard constraints applied during multi-objective optimization.
                </p>
                <button
                  onClick={() => setShowCreate(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  New Profile
                </button>
              </div>

              {isLoading ? (
                <div className="p-8 text-center text-sm text-neutral-400 animate-pulse">
                  Loading preference profiles...
                </div>
              ) : profiles.length === 0 ? (
                <div className="p-8 border border-neutral-800/80 rounded-xl bg-neutral-950/40 text-center space-y-2">
                  <Sliders className="w-8 h-8 text-neutral-600 mx-auto" />
                  <p className="text-sm font-medium text-neutral-300">No Custom Profiles</p>
                  <p className="text-xs text-neutral-500">
                    Create a profile to save customized objective weights and quality/latency constraints.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {profiles.map((p) => (
                    <div
                      key={p.id}
                      className="p-4 border border-neutral-800 rounded-lg bg-neutral-950/40 flex items-start justify-between gap-4"
                    >
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-neutral-200">{p.name}</span>
                          <span className="text-[10px] px-2 py-0.5 bg-neutral-800 text-neutral-400 rounded-full font-mono">
                            v{p.version}
                          </span>
                        </div>
                        {p.description && (
                          <p className="text-xs text-neutral-400">{p.description}</p>
                        )}
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {Object.entries(p.weights).map(([k, w]) => (
                            <span
                              key={k}
                              className="text-[11px] px-2 py-0.5 bg-emerald-950/50 text-emerald-300 border border-emerald-800/50 rounded"
                            >
                              {k.replace(/_/g, " ")}: {(Number(w) * 100).toFixed(0)}%
                            </span>
                          ))}
                        </div>
                      </div>
                      <button
                        onClick={() => deleteMutation.mutate(p.id)}
                        className="text-neutral-500 hover:text-red-400 p-1 transition-colors"
                        title="Delete Profile"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <form onSubmit={handleCreateSubmit} className="space-y-5">
              {errorMsg && (
                <div className="p-3 bg-red-950/50 border border-red-800/80 rounded-lg text-xs text-red-300 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-neutral-300">Profile Name *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Production Balanced QoS"
                  className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-sm text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-neutral-300">Description</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Prioritizes low latency while ensuring >= 80% accuracy"
                  className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-sm text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-emerald-500"
                />
              </div>

              {/* Presets shortcut */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-neutral-300">
                  Quick Start Presets (Auto-fills weights)
                </label>
                <div className="flex flex-wrap gap-2">
                  {Object.keys(presets).map((presetKey) => (
                    <button
                      key={presetKey}
                      type="button"
                      onClick={() => applyPreset(presetKey)}
                      className="px-2.5 py-1 text-xs bg-neutral-800 hover:bg-neutral-700 text-neutral-200 rounded border border-neutral-700 transition-colors"
                    >
                      {presetKey.replace(/_/g, " ")}
                    </button>
                  ))}
                </div>
              </div>

              {/* Objectives & Weights */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-neutral-300">
                    Included Objectives &amp; Weights
                  </label>
                  <span
                    className={`text-xs font-mono font-medium ${
                      isWeightValid ? "text-emerald-400" : "text-amber-400"
                    }`}
                  >
                    Sum: {(totalWeight * 100).toFixed(1)}% / 100%
                  </span>
                </div>

                <div className="space-y-2 border border-neutral-800 rounded-lg p-3 bg-neutral-950/40">
                  {objectives.slice(0, 8).map((obj) => {
                    const isSelected = selectedObjectives.includes(obj.key);
                    const weightVal = weights[obj.key] ?? 0;
                    return (
                      <div
                        key={obj.key}
                        className="flex items-center justify-between gap-3 text-xs"
                      >
                        <label className="flex items-center gap-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleObjectiveToggle(obj.key)}
                            className="rounded border-neutral-700 bg-neutral-900 text-emerald-500 focus:ring-emerald-500"
                          />
                          <span className={isSelected ? "text-neutral-200" : "text-neutral-500"}>
                            {obj.display_name} ({obj.unit})
                          </span>
                        </label>
                        {isSelected && (
                          <div className="flex items-center gap-2">
                            <input
                              type="number"
                              min="0"
                              max="1"
                              step="0.05"
                              value={weightVal}
                              onChange={(e) =>
                                handleWeightChange(obj.key, parseFloat(e.target.value) || 0)
                              }
                              className="w-16 px-2 py-0.5 bg-neutral-900 border border-neutral-700 rounded text-right text-xs text-neutral-100 font-mono"
                            />
                            <span className="text-[10px] text-neutral-500 w-8">
                              {(weightVal * 100).toFixed(0)}%
                            </span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Hard Constraints */}
              <div className="space-y-3 pt-2">
                <label className="text-xs font-medium text-neutral-300">
                  Default Hard Constraints (Filter thresholds)
                </label>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="text-neutral-400 block mb-1">Min Quality Score (pts)</label>
                    <input
                      type="number"
                      value={constraints.min_quality_score ?? ""}
                      onChange={(e) =>
                        setConstraints((prev) => ({
                          ...prev,
                          min_quality_score: e.target.value ? parseFloat(e.target.value) : undefined,
                        }))
                      }
                      className="w-full px-2.5 py-1.5 bg-neutral-950 border border-neutral-800 rounded text-neutral-200"
                    />
                  </div>
                  <div>
                    <label className="text-neutral-400 block mb-1">Max P95 Latency (ms)</label>
                    <input
                      type="number"
                      value={constraints.max_p95_latency_ms ?? ""}
                      onChange={(e) =>
                        setConstraints((prev) => ({
                          ...prev,
                          max_p95_latency_ms: e.target.value ? parseFloat(e.target.value) : undefined,
                        }))
                      }
                      className="w-full px-2.5 py-1.5 bg-neutral-950 border border-neutral-800 rounded text-neutral-200"
                    />
                  </div>
                  <div>
                    <label className="text-neutral-400 block mb-1">Max RAM Limit (MB)</label>
                    <input
                      type="number"
                      value={constraints.max_ram_mb ?? ""}
                      onChange={(e) =>
                        setConstraints((prev) => ({
                          ...prev,
                          max_ram_mb: e.target.value ? parseFloat(e.target.value) : undefined,
                        }))
                      }
                      className="w-full px-2.5 py-1.5 bg-neutral-950 border border-neutral-800 rounded text-neutral-200"
                    />
                  </div>
                  <div>
                    <label className="text-neutral-400 block mb-1">Max Budget (USD)</label>
                    <input
                      type="number"
                      value={constraints.max_budget_usd ?? ""}
                      onChange={(e) =>
                        setConstraints((prev) => ({
                          ...prev,
                          max_budget_usd: e.target.value ? parseFloat(e.target.value) : undefined,
                        }))
                      }
                      placeholder="e.g. 50.00"
                      className="w-full px-2.5 py-1.5 bg-neutral-950 border border-neutral-800 rounded text-neutral-200"
                    />
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-neutral-800">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="px-4 py-2 text-xs text-neutral-400 hover:text-neutral-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || !isWeightValid}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors"
                >
                  <Check className="w-3.5 h-3.5" />
                  {createMutation.isPending ? "Saving..." : "Save Profile"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
