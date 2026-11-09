import React from "react";
import { CheckCircle2, AlertTriangle, XCircle, Play, ArrowUpRight } from "lucide-react";
import type { RuntimeSlot } from "../types";

interface SlotCardProps {
  slot: RuntimeSlot;
  isActive: boolean;
  onRunGoldenTests: (slotId: string) => void;
  onActivate: (slot: RuntimeSlot) => void;
  isLoading?: boolean;
}

export const SlotCard: React.FC<SlotCardProps> = ({
  slot,
  isActive,
  onRunGoldenTests,
  onActivate,
  isLoading = false,
}) => {
  const isSlotA = slot.slot_name === "SLOT_A";
  const slotTheme = isSlotA
    ? "border-blue-500/30 bg-blue-500/5"
    : "border-emerald-500/30 bg-emerald-500/5";

  const getReadinessBadge = () => {
    switch (slot.readiness_state) {
      case "READY":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
            <CheckCircle2 className="w-3.5 h-3.5" /> Ready
          </span>
        );
      case "LOADING":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
            <AlertTriangle className="w-3.5 h-3.5 animate-spin" /> Loading
          </span>
        );
      case "UNHEALTHY":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300">
            <XCircle className="w-3.5 h-3.5" /> Unhealthy
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400">
            Uninitialized
          </span>
        );
    }
  };

  const getGoldenTestBadge = () => {
    switch (slot.golden_test_status) {
      case "PASSED":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
            Golden Tests Passed
          </span>
        );
      case "FAILED":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300 border border-red-300 dark:border-red-800">
            Golden Tests Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
            Golden Tests Not Run
          </span>
        );
    }
  };

  return (
    <div className={`rounded-xl border p-5 transition-all shadow-sm ${slotTheme}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={`w-9 h-9 rounded-lg flex items-center justify-center font-bold text-sm ${
              isSlotA ? "bg-blue-600 text-white" : "bg-emerald-600 text-white"
            }`}
          >
            {isSlotA ? "A" : "B"}
          </div>
          <div>
            <h3 className="text-base font-semibold text-foreground">
              {isSlotA ? "Slot A (Blue)" : "Slot B (Green)"}
            </h3>
            <p className="text-xs text-muted-foreground font-mono">
              Engine: {slot.engine_adapter_key}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isActive ? (
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-600 text-white tracking-wide uppercase">
              Active Serving
            </span>
          ) : (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-muted text-muted-foreground">
              {slot.status === "EMPTY" ? "Empty Slot" : "Staged Candidate"}
            </span>
          )}
        </div>
      </div>

      <div className="space-y-2.5 mb-5 text-sm">
        <div className="flex justify-between items-center py-1 border-b border-border/50">
          <span className="text-muted-foreground">Model Version</span>
          <span className="font-mono font-medium text-xs">
            {slot.model_version_id || "None Loaded"}
          </span>
        </div>
        <div className="flex justify-between items-center py-1 border-b border-border/50">
          <span className="text-muted-foreground">Traffic Readiness</span>
          {getReadinessBadge()}
        </div>
        <div className="flex justify-between items-center py-1 border-b border-border/50">
          <span className="text-muted-foreground">Golden Tests Gate</span>
          {getGoldenTestBadge()}
        </div>
        <div className="flex justify-between items-center py-1">
          <span className="text-muted-foreground">Manifest Digest</span>
          <span className="font-mono text-xs text-muted-foreground truncate max-w-[180px]">
            {slot.release_manifest_digest ? `${slot.release_manifest_digest.slice(0, 16)}...` : "—"}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2.5 pt-2">
        {slot.status !== "EMPTY" && (
          <button
            type="button"
            onClick={() => onRunGoldenTests(slot.id)}
            disabled={isLoading}
            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-input bg-background hover:bg-muted transition-colors"
          >
            <Play className="w-3.5 h-3.5 text-primary" /> Run Golden Tests
          </button>
        )}

        {!isActive && slot.status !== "EMPTY" && (
          <button
            type="button"
            onClick={() => onActivate(slot)}
            disabled={isLoading || slot.golden_test_status !== "PASSED"}
            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ArrowUpRight className="w-3.5 h-3.5" /> Promote to Active
          </button>
        )}
      </div>
    </div>
  );
};
