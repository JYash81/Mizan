import React, { useState } from "react";
import type { HardwareProfile } from "../types";

interface Props {
  profiles: HardwareProfile[];
}

export const HardwareProfileCards: React.FC<Props> = ({ profiles }) => {
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const getCategoryBadgeClass = (category: string) => {
    switch (category) {
      case "LOCAL_WORKSTATION":
        return "bg-emerald-950/70 text-emerald-400 border-emerald-800";
      case "CLOUD_CPU":
        return "bg-sky-950/70 text-sky-400 border-sky-800";
      case "CLOUD_GPU":
        return "bg-purple-950/70 text-purple-400 border-purple-800";
      default:
        return "bg-neutral-800 text-neutral-300 border-neutral-700";
    }
  };

  const getEvidenceBadgeClass = (evidence: string) => {
    switch (evidence) {
      case "MEASURED":
        return "bg-emerald-950/80 text-emerald-300 border-emerald-700";
      case "VENDOR_REFERENCE":
        return "bg-blue-950/80 text-blue-300 border-blue-700";
      case "ESTIMATED":
        return "bg-amber-950/80 text-amber-300 border-amber-700";
      default:
        return "bg-neutral-800 text-neutral-400 border-neutral-700";
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-neutral-100">
            Hardware Knowledge Base & Profile Registry
          </h2>
          <p className="text-sm text-neutral-400 mt-1">
            Standard reference and tenant-inspected hardware specifications with explicit evidence provenance.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {profiles.map((p) => {
          const isSelected = selectedKey === p.profile_key;
          return (
            <div
              key={p.id}
              className={`rounded-xl border transition-all p-5 flex flex-col justify-between ${
                isSelected
                  ? "border-emerald-500 bg-neutral-900/90 shadow-lg shadow-emerald-950/20"
                  : "border-neutral-800 bg-neutral-900/50 hover:border-neutral-700"
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full border font-medium ${getCategoryBadgeClass(
                          p.category
                        )}`}
                      >
                        {p.category.replace("_", " ")}
                      </span>
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full border font-mono ${getEvidenceBadgeClass(
                          p.evidence_type
                        )}`}
                      >
                        {p.evidence_type}
                      </span>
                      {p.is_reference && (
                        <span className="text-xs px-2 py-0.5 rounded bg-neutral-800 text-neutral-300 border border-neutral-700">
                          Reference
                        </span>
                      )}
                    </div>
                    <h3 className="text-lg font-medium text-neutral-100 mt-2.5">
                      {p.name}
                    </h3>
                    <p className="text-xs text-neutral-400 font-mono mt-0.5">
                      {p.profile_key}
                    </p>
                  </div>
                </div>

                {/* Specs overview grid */}
                <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-neutral-800/80 text-xs">
                  <div>
                    <span className="text-neutral-500 block">CPU & Cores</span>
                    <span className="text-neutral-200 font-medium">
                      {p.cpu_model || "Generic"} ({p.logical_cores || 1} vCPU)
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">System RAM</span>
                    <span className="text-neutral-200 font-medium">
                      {(p.system_ram_mb / 1024).toFixed(1)} GB Total
                      {p.available_ram_mb && (
                        <span className="text-neutral-400 ml-1">
                          ({(p.available_ram_mb / 1024).toFixed(1)} GB avail)
                        </span>
                      )}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">GPU / Accelerator</span>
                    <span className="text-neutral-200 font-medium">
                      {p.gpu_model || "None (CPU Only)"}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">Dedicated VRAM</span>
                    <span className="text-neutral-200 font-medium">
                      {p.gpu_vram_mb ? `${(p.gpu_vram_mb / 1024).toFixed(0)} GB VRAM` : "0 MB"}
                    </span>
                  </div>
                </div>

                {/* Capabilities Badges */}
                <div className="flex items-center gap-2 mt-4 flex-wrap">
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      p.supports_cpu_inference
                        ? "bg-emerald-950 text-emerald-400 border border-emerald-900"
                        : "bg-neutral-800/50 text-neutral-500"
                    }`}
                  >
                    CPU Inference: {p.supports_cpu_inference ? "Yes" : "No"}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      p.supports_gpu_inference
                        ? "bg-purple-950 text-purple-400 border border-purple-900"
                        : "bg-neutral-800/50 text-neutral-500"
                    }`}
                  >
                    GPU Inference: {p.supports_gpu_inference ? "Yes" : "No"}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      p.supports_fine_tuning
                        ? "bg-sky-950 text-sky-400 border border-sky-900"
                        : "bg-neutral-800/50 text-neutral-500"
                    }`}
                  >
                    Fine-Tuning: {p.supports_fine_tuning ? "Yes" : "No"}
                  </span>
                </div>

                {/* Limitations warning */}
                {p.limitations && (
                  <div className="mt-3 p-2.5 rounded-lg bg-amber-950/20 border border-amber-900/40 text-amber-300 text-xs">
                    <span className="font-semibold">Constraint: </span>
                    {p.limitations}
                  </div>
                )}

                {/* Expanded Details */}
                {isSelected && (
                  <div className="mt-4 pt-4 border-t border-neutral-800 text-xs space-y-2.5 text-neutral-300 animate-fadeIn">
                    <div>
                      <span className="text-neutral-500 block">Supported Quantizations:</span>
                      <span className="font-mono text-neutral-300">
                        {p.supported_quantizations.join(", ") || "None"}
                      </span>
                    </div>
                    <div>
                      <span className="text-neutral-500 block">Supported Runtimes:</span>
                      <span className="font-mono text-neutral-300">
                        {p.supported_runtimes.join(", ") || "None"}
                      </span>
                    </div>
                    <div>
                      <span className="text-neutral-500 block">Supported Precisions:</span>
                      <span className="font-mono text-neutral-300">
                        {p.supported_numeric_precisions.join(", ") || "None"}
                      </span>
                    </div>
                    {p.memory_bandwidth_gbps && (
                      <div>
                        <span className="text-neutral-500 block">Memory Bandwidth:</span>
                        <span>{p.memory_bandwidth_gbps} GB/s</span>
                      </div>
                    )}
                    {p.source_url && (
                      <div>
                        <span className="text-neutral-500 block">Reference Source:</span>
                        <a
                          href={p.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sky-400 hover:underline break-all"
                        >
                          {p.source_url}
                        </a>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="mt-4 pt-3 border-t border-neutral-800/60 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setSelectedKey(isSelected ? null : p.profile_key)}
                  className="text-xs text-neutral-400 hover:text-neutral-200 transition-colors"
                >
                  {isSelected ? "Hide Full Specifications ▲" : "View Full Specifications ▼"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
