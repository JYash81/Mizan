import React, { useState } from "react";
import { compareHardware } from "../api";
import type { HardwareComparisonResponse, QuantizationFormat } from "../types";

interface Props {
  workspaceId: string;
  quantizations: QuantizationFormat[];
}

export const HardwareComparisonMatrix: React.FC<Props> = ({
  workspaceId,
  quantizations,
}) => {
  const [modelName, setModelName] = useState("Llama-3-8B");
  const [paramCount, setParamCount] = useState<number>(8000);
  const [quantFormat, setQuantFormat] = useState("Q4_K_M");
  const contextLength = 2048;
  const batchSize = 1;
  const [execMode, setExecMode] = useState("INFERENCE_CPU");

  const [comparison, setComparison] = useState<HardwareComparisonResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCompare = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const res = await compareHardware(workspaceId, {
        model_name: modelName,
        parameter_count_millions: paramCount,
        quantization_format: quantFormat,
        context_length: contextLength,
        batch_size: batchSize,
        execution_mode: execMode,
      });
      setComparison(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to run comparison.");
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
    <div className="space-y-6">
      <div className="p-6 rounded-xl border border-neutral-800 bg-neutral-900/60">
        <h3 className="text-lg font-medium text-neutral-100">
          Cross-Hardware Compatibility Matrix
        </h3>
        <p className="text-xs text-neutral-400 mt-1">
          Evaluate memory feasibility and runtime support across all reference hardware profiles simultaneously.
        </p>

        <form onSubmit={handleCompare} className="mt-4 grid grid-cols-1 md:grid-cols-6 gap-3 text-xs">
          <div className="md:col-span-2">
            <label className="text-neutral-400 block mb-1">Model Name</label>
            <input
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
              required
            />
          </div>

          <div>
            <label className="text-neutral-400 block mb-1">Params (M)</label>
            <input
              type="number"
              value={paramCount}
              onChange={(e) => setParamCount(parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-1.5 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
              step="100"
              required
            />
          </div>

          <div>
            <label className="text-neutral-400 block mb-1">Quantization</label>
            <select
              value={quantFormat}
              onChange={(e) => setQuantFormat(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
            >
              {quantizations.length > 0 ? (
                quantizations.map((q) => (
                  <option key={q.format_key} value={q.format_key}>
                    {q.format_key}
                  </option>
                ))
              ) : (
                <>
                  <option value="Q4_K_M">Q4_K_M</option>
                  <option value="Q8_0">Q8_0</option>
                  <option value="FP16">FP16</option>
                  <option value="AWQ">AWQ</option>
                </>
              )}
            </select>
          </div>

          <div>
            <label className="text-neutral-400 block mb-1">Execution Mode</label>
            <select
              value={execMode}
              onChange={(e) => setExecMode(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="INFERENCE_CPU">CPU Inference</option>
              <option value="INFERENCE_GPU">GPU Inference</option>
              <option value="FINE_TUNE_LORA">LoRA Fine-Tune</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs transition-colors disabled:opacity-50"
            >
              {isLoading ? "Comparing..." : "Compare All"}
            </button>
          </div>
        </form>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-sm">
          {error}
        </div>
      )}

      {comparison && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {comparison.profiles.map((p) => (
            <div
              key={p.profile_key}
              className="p-5 rounded-xl border border-neutral-800 bg-neutral-900/60 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-xs px-2.5 py-0.5 rounded-full border border-neutral-700 bg-neutral-800 text-neutral-300 font-medium">
                      {p.category.replace("_", " ")}
                    </span>
                    <h4 className="text-base font-medium text-neutral-100 mt-2">
                      {p.profile_name}
                    </h4>
                    <span className="text-xs text-neutral-500 font-mono">{p.profile_key}</span>
                  </div>
                  <span
                    className={`text-xs px-2.5 py-1 rounded-full border font-semibold ${getFeasibilityBadge(
                      p.feasibility_status
                    )}`}
                  >
                    {p.feasibility_status.replace("_", " ")}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-4 pt-3 border-t border-neutral-800 text-xs">
                  <div>
                    <span className="text-neutral-500 block">Required Memory</span>
                    <span className="text-neutral-200 font-mono font-medium">
                      {p.required_vram_mb > 0
                        ? `${p.required_vram_mb.toFixed(0)} MB VRAM`
                        : `${p.required_ram_mb.toFixed(0)} MB RAM`}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">Available Capacity</span>
                    <span className="text-neutral-200 font-mono font-medium">
                      {p.available_vram_mb > 0
                        ? `${(p.available_vram_mb / 1024).toFixed(1)} GB VRAM`
                        : `${(p.available_ram_mb / 1024).toFixed(1)} GB RAM`}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">Estimated Headroom</span>
                    <span
                      className={`font-mono font-semibold ${
                        p.headroom_mb >= 0 ? "text-emerald-400" : "text-rose-400"
                      }`}
                    >
                      {p.headroom_mb.toFixed(1)} MB
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">Format Supported</span>
                    <span className={p.quantization_supported ? "text-emerald-400" : "text-rose-400"}>
                      {p.quantization_supported ? "Yes" : "No"}
                    </span>
                  </div>
                </div>

                <div className="mt-3 p-2.5 rounded-lg bg-neutral-950/70 border border-neutral-800/80 text-xs text-neutral-400">
                  <span className="text-neutral-300 font-medium">Observation: </span>
                  {p.reason}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
