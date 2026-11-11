import React, { useState } from "react";
import { estimateResources } from "../api";
import type { HardwareProfile, QuantizationFormat, ResourceEstimate } from "../types";

interface Props {
  workspaceId: string;
  profiles: HardwareProfile[];
  quantizations: QuantizationFormat[];
}

export const ResourceEstimatorForm: React.FC<Props> = ({
  workspaceId,
  profiles,
  quantizations,
}) => {
  const [modelName, setModelName] = useState("Llama-3-8B");
  const [paramCount, setParamCount] = useState<number>(8000);
  const [quantFormat, setQuantFormat] = useState("Q4_K_M");
  const [contextLength, setContextLength] = useState<number>(2048);
  const [batchSize, setBatchSize] = useState<number>(1);
  const [execMode, setExecMode] = useState("INFERENCE_CPU");
  const [profileKey, setProfileKey] = useState("LOCAL_CPU_I5_8GB");

  const [estimate, setEstimate] = useState<ResourceEstimate | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const presets = [
    { label: "1B (e.g. TinyLlama)", name: "TinyLlama-1.1B", params: 1100 },
    { label: "3.8B (e.g. Phi-3)", name: "Phi-3-Mini-3.8B", params: 3800 },
    { label: "7B (e.g. Mistral)", name: "Mistral-7B", params: 7000 },
    { label: "8B (e.g. Llama-3)", name: "Llama-3-8B", params: 8000 },
    { label: "70B (e.g. Llama-3 70B)", name: "Llama-3-70B", params: 70000 },
  ];

  const handleEstimate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const res = await estimateResources(workspaceId, {
        model_name: modelName,
        parameter_count_millions: paramCount,
        quantization_format: quantFormat,
        context_length: contextLength,
        batch_size: batchSize,
        execution_mode: execMode,
        hardware_profile_key: profileKey,
      });
      setEstimate(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to calculate estimate.");
    } finally {
      setIsLoading(false);
    }
  };

  const getFeasibilityBadge = (status: string) => {
    switch (status) {
      case "FEASIBLE_ESTIMATE":
        return "bg-emerald-950/80 text-emerald-300 border-emerald-700";
      case "LIKELY_FEASIBLE":
        return "bg-amber-950/80 text-amber-300 border-amber-700";
      case "NOT_FEASIBLE":
        return "bg-rose-950/80 text-rose-300 border-rose-700";
      default:
        return "bg-neutral-800 text-neutral-400 border-neutral-700";
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Form Controls */}
      <div className="lg:col-span-5 space-y-5 p-6 rounded-xl border border-neutral-800 bg-neutral-900/60">
        <div>
          <h3 className="text-lg font-medium text-neutral-100">
            Model Resource Estimator
          </h3>
          <p className="text-xs text-neutral-400 mt-1">
            Deterministic weights, KV cache, and runtime overhead calculator.
          </p>
        </div>

        {/* Quick Presets */}
        <div>
          <label className="text-xs text-neutral-500 block mb-1.5">Model Size Presets</label>
          <div className="flex gap-1.5 flex-wrap">
            {presets.map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => {
                  setModelName(p.name);
                  setParamCount(p.params);
                }}
                className={`text-xs px-2.5 py-1 rounded-lg border transition-colors ${
                  paramCount === p.params
                    ? "bg-emerald-950 text-emerald-300 border-emerald-700"
                    : "bg-neutral-950/80 text-neutral-400 border-neutral-800 hover:border-neutral-700"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleEstimate} className="space-y-4 text-xs">
          <div>
            <label className="text-neutral-400 block mb-1">Model Name</label>
            <input
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
              required
            />
          </div>

          <div>
            <label className="text-neutral-400 block mb-1">
              Parameters (in Millions, e.g. 8000 = 8B)
            </label>
            <input
              type="number"
              value={paramCount}
              onChange={(e) => setParamCount(parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
              step="10"
              min="10"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-neutral-400 block mb-1">Quantization Format</label>
              <select
                value={quantFormat}
                onChange={(e) => setQuantFormat(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
              >
                {quantizations.length > 0 ? (
                  quantizations.map((q) => (
                    <option key={q.format_key} value={q.format_key}>
                      {q.format_key} ({q.effective_reference_bits} bits)
                    </option>
                  ))
                ) : (
                  <>
                    <option value="Q4_K_M">Q4_K_M (4.9 bits)</option>
                    <option value="Q8_0">Q8_0 (8.5 bits)</option>
                    <option value="FP16">FP16 (16.0 bits)</option>
                    <option value="AWQ">AWQ (4.5 bits, GPU)</option>
                  </>
                )}
              </select>
            </div>

            <div>
              <label className="text-neutral-400 block mb-1">Execution Mode</label>
              <select
                value={execMode}
                onChange={(e) => setExecMode(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="INFERENCE_CPU">Inference (CPU)</option>
                <option value="INFERENCE_GPU">Inference (GPU)</option>
                <option value="FINE_TUNE_LORA">Fine-Tuning (LoRA 1%)</option>
                <option value="FINE_TUNE_FULL">Fine-Tuning (Full Adam)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-neutral-400 block mb-1">Context Length</label>
              <select
                value={contextLength}
                onChange={(e) => setContextLength(parseInt(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
              >
                <option value={1024}>1,024 tokens</option>
                <option value={2048}>2,048 tokens</option>
                <option value={4096}>4,096 tokens</option>
                <option value={8192}>8,192 tokens</option>
                <option value={16384}>16,384 tokens</option>
              </select>
            </div>

            <div>
              <label className="text-neutral-400 block mb-1">Batch Size</label>
              <input
                type="number"
                value={batchSize}
                onChange={(e) => setBatchSize(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
                min="1"
                max="32"
              />
            </div>
          </div>

          <div>
            <label className="text-neutral-400 block mb-1">Target Hardware Profile</label>
            <select
              value={profileKey}
              onChange={(e) => setProfileKey(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
            >
              {profiles.map((p) => (
                <option key={p.profile_key} value={p.profile_key}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 mt-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition-colors disabled:opacity-50"
          >
            {isLoading ? "Calculating..." : "Calculate Resource Requirements"}
          </button>
        </form>
      </div>

      {/* Results Panel */}
      <div className="lg:col-span-7 space-y-5">
        {error && (
          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-sm">
            {error}
          </div>
        )}

        {estimate ? (
          <div className="p-6 rounded-xl border border-neutral-800 bg-neutral-900/60 space-y-6">
            <div className="flex items-start justify-between flex-wrap gap-3">
              <div>
                <span className="text-xs text-neutral-500 uppercase tracking-wide">
                  Estimation Result
                </span>
                <h3 className="text-xl font-semibold text-neutral-100 mt-1">
                  {estimate.model_name} on {estimate.hardware_profile_name}
                </h3>
                <p className="text-xs text-neutral-400 mt-0.5">
                  Format: <span className="font-mono text-neutral-200">{estimate.quantization_format}</span> &bull; Mode:{" "}
                  <span className="font-mono text-neutral-200">{estimate.execution_mode}</span>
                </p>
              </div>

              <div className="flex flex-col items-end">
                <span
                  className={`text-xs px-3 py-1 rounded-full border font-semibold ${getFeasibilityBadge(
                    estimate.feasibility_status
                  )}`}
                >
                  {estimate.feasibility_status.replace("_", " ")}
                </span>
                <span className="text-xs text-neutral-500 mt-1">
                  Headroom:{" "}
                  <span
                    className={
                      estimate.headroom_mb >= 0
                        ? "text-emerald-400 font-semibold"
                        : "text-rose-400 font-semibold"
                    }
                  >
                    {estimate.headroom_mb.toFixed(1)} MB
                  </span>
                </span>
              </div>
            </div>

            {/* Component Breakdown Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-lg bg-neutral-950/70 border border-neutral-800">
                <span className="text-xs text-neutral-500 block">Model Weights</span>
                <span className="text-base font-semibold text-neutral-200 mt-1 block">
                  {estimate.weight_memory_mb.toFixed(1)} MB
                </span>
                <span className="text-xs text-neutral-400 mt-0.5 block">
                  Artifact: {estimate.artifact_size_mb.toFixed(1)} MB
                </span>
              </div>

              <div className="p-3.5 rounded-lg bg-neutral-950/70 border border-neutral-800">
                <span className="text-xs text-neutral-500 block">KV Cache</span>
                <span className="text-base font-semibold text-neutral-200 mt-1 block">
                  {estimate.kv_cache_memory_mb.toFixed(1)} MB
                </span>
                <span className="text-xs text-neutral-400 mt-0.5 block truncate">
                  {estimate.calculation_details?.kv_cache_calculation_method?.toLowerCase() || "standard"}
                </span>
              </div>

              <div className="p-3.5 rounded-lg bg-neutral-950/70 border border-neutral-800">
                <span className="text-xs text-neutral-500 block">Runtime Overhead</span>
                <span className="text-base font-semibold text-neutral-200 mt-1 block">
                  {estimate.runtime_overhead_mb.toFixed(1)} MB
                </span>
                <span className="text-xs text-neutral-400 mt-0.5 block">
                  Activations & Buffers
                </span>
              </div>

              <div className="p-3.5 rounded-lg bg-neutral-950/70 border border-neutral-800">
                <span className="text-xs text-neutral-500 block">Peak Execution RAM</span>
                <span className="text-base font-semibold text-purple-300 mt-1 block">
                  {estimate.peak_memory_mb.toFixed(1)} MB
                </span>
                <span className="text-xs text-neutral-400 mt-0.5 block">
                  Available: {estimate.available_memory_mb.toFixed(0)} MB
                </span>
              </div>
            </div>

            {/* Assumptions & Warnings */}
            {estimate.assumptions_and_warnings.length > 0 && (
              <div className="p-4 rounded-lg bg-neutral-950 border border-neutral-800 space-y-2 text-xs">
                <span className="font-semibold text-neutral-300 block">
                  Methodology & Constraints:
                </span>
                <ul className="list-disc list-inside space-y-1 text-neutral-400">
                  {estimate.assumptions_and_warnings.map((warn, i) => (
                    <li key={i}>{warn}</li>
                  ))}
                  <li>Calculations include a mandatory 15% safety headroom buffer.</li>
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="p-12 rounded-xl border border-dashed border-neutral-800 bg-neutral-900/30 text-center text-sm text-neutral-500">
            Configure your model parameters on the left and click &quot;Calculate Resource Requirements&quot; to inspect peak execution memory and headroom.
          </div>
        )}
      </div>
    </div>
  );
};
