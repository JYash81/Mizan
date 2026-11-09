import React from "react";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HardDrive,
  Cpu,
  Layers,
  ShieldCheck,
} from "lucide-react";
import type { BuildPreflightResponse } from "../types";

interface ResourcePreflightCardProps {
  preflight: BuildPreflightResponse | null;
  isLoading?: boolean;
}

export const ResourcePreflightCard: React.FC<ResourcePreflightCardProps> = ({
  preflight,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/60 p-6 animate-pulse">
        <div className="h-6 w-48 bg-slate-700 rounded mb-4" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="h-20 bg-slate-700 rounded" />
          <div className="h-20 bg-slate-700 rounded" />
          <div className="h-20 bg-slate-700 rounded" />
          <div className="h-20 bg-slate-700 rounded" />
        </div>
      </div>
    );
  }

  if (!preflight) {
    return (
      <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/40 p-6 text-center text-slate-400">
        <Cpu className="mx-auto h-8 w-8 text-slate-500 mb-2" />
        <p className="text-sm font-medium">Select model and recipe to calculate M8 resource preflight</p>
      </div>
    );
  }

  const isFeasible = preflight.is_feasible;

  return (
    <div
      className={`rounded-lg border p-6 transition-all ${
        isFeasible
          ? "border-emerald-500/40 bg-slate-800/80 shadow-emerald-950/20 shadow-lg"
          : "border-rose-500/40 bg-slate-800/80 shadow-rose-950/20 shadow-lg"
      }`}
    >
      {/* Header with Feasibility Status */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-700 pb-4 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-slate-100">
              Hardware Preflight & Resource Feasibility
            </h3>
            <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
              Milestone 8 Model
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Target Hardware:{" "}
            <span className="font-medium text-slate-200">{preflight.hardware_name}</span>{" "}
            ({preflight.target_hardware_profile})
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isFeasible ? (
            <span
              data-testid="preflight-status-feasible"
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
            >
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              FEASIBLE ESTIMATE
            </span>
          ) : (
            <span
              data-testid="preflight-status-infeasible"
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40"
            >
              <XCircle className="h-4 w-4 text-rose-400" />
              NOT FEASIBLE
            </span>
          )}
        </div>
      </div>

      {/* Resource Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
        <div className="rounded-md border border-slate-700 bg-slate-900/60 p-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
            <Cpu className="h-3.5 w-3.5 text-cyan-400" />
            Peak Working RAM
          </div>
          <div className="text-lg font-bold text-slate-100">
            {preflight.peak_memory_mb.toLocaleString()} <span className="text-xs font-normal text-slate-400">MB</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">Weights + KV + Overhead</p>
        </div>

        <div className="rounded-md border border-slate-700 bg-slate-900/60 p-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
            <Layers className="h-3.5 w-3.5 text-indigo-400" />
            Model Weights
          </div>
          <div className="text-lg font-bold text-slate-100">
            {preflight.weight_memory_mb.toLocaleString()} <span className="text-xs font-normal text-slate-400">MB</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">FP16 / Quantized Base</p>
        </div>

        <div className="rounded-md border border-slate-700 bg-slate-900/60 p-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
            <HardDrive className="h-3.5 w-3.5 text-amber-400" />
            KV Cache Memory
          </div>
          <div className="text-lg font-bold text-slate-100">
            {preflight.kv_cache_mb.toLocaleString()} <span className="text-xs font-normal text-slate-400">MB</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">Seq window & batch</p>
        </div>

        <div className="rounded-md border border-slate-700 bg-slate-900/60 p-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
            <HardDrive className="h-3.5 w-3.5 text-emerald-400" />
            Total Disk Required
          </div>
          <div className="text-lg font-bold text-slate-100">
            {(preflight.total_disk_required_mb / 1024.0).toFixed(1)} <span className="text-xs font-normal text-slate-400">GB</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">Download + Checkpoints</p>
        </div>
      </div>

      {/* Infeasibility Warnings / Reasons */}
      {!isFeasible && preflight.block_reasons.length > 0 && (
        <div className="rounded-md border border-rose-500/30 bg-rose-950/30 p-3.5 mb-4">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-rose-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-semibold text-rose-300">
                Execution Blocked by Hardware Constraints:
              </p>
              <ul className="list-disc list-inside text-xs text-rose-200/90 mt-1 space-y-0.5">
                {preflight.block_reasons.map((reason, idx) => (
                  <li key={idx}>{reason}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Free-Only Policy Confirmation */}
      <div className="flex items-center justify-between text-xs text-slate-400 bg-slate-900/40 rounded px-3 py-2 border border-slate-800">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          <span>Strict Free-Only Policy: $0.00 additional cloud spend.</span>
        </div>
        <span className="text-slate-500">Mode: {preflight.execution_mode}</span>
      </div>
    </div>
  );
};
