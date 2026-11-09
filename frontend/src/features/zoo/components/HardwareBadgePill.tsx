import { CheckCircle2, Cpu, HelpCircle, XCircle } from "lucide-react";
import type { HardwareCompatibilityBadge, HardwareSnapshot } from "../types";

interface HardwareBadgePillProps {
  badge: HardwareCompatibilityBadge;
  hardwareName?: string | null;
  category?: string | null;
  evidenceType?: string | null;
  compact?: boolean;
}

export function HardwareBadgePill({
  badge,
  hardwareName,
  category,
  evidenceType,
  compact = false,
}: HardwareBadgePillProps) {
  const badgeConfig = {
    TESTED: {
      color: "bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800",
      icon: CheckCircle2,
      label: "TESTED",
      desc: "Measured physical benchmark",
    },
    ESTIMATED: {
      color: "bg-blue-50 text-blue-700 border-blue-300 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800",
      icon: Cpu,
      label: "ESTIMATED",
      desc: "M8 analytical resource estimation",
    },
    INCOMPATIBLE: {
      color: "bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800",
      icon: XCircle,
      label: "INCOMPATIBLE",
      desc: "Exceeds hardware memory or compute bounds",
    },
    UNKNOWN: {
      color: "bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
      icon: HelpCircle,
      label: "UNKNOWN",
      desc: "Insufficient benchmark data",
    },
  }[badge];

  const Icon = badgeConfig.icon;

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold border ${badgeConfig.color}`}
        title={`${badgeConfig.label}: ${badgeConfig.desc} (${hardwareName || "General"})`}
      >
        <Icon className="w-3.5 h-3.5" />
        <span>{badgeConfig.label}</span>
      </span>
    );
  }

  return (
    <div
      className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-md text-xs font-medium border ${badgeConfig.color}`}
    >
      <Icon className="w-4 h-4 shrink-0" />
      <div className="flex flex-col">
        <div className="flex items-center gap-1.5">
          <span className="font-bold tracking-wider">{badgeConfig.label}</span>
          {hardwareName && <span className="opacity-90 font-normal">· {hardwareName}</span>}
        </div>
        <span className="text-[10px] opacity-75">
          {category ? `${category} · ` : ""}
          {evidenceType ? `${evidenceType} evidence` : badgeConfig.desc}
        </span>
      </div>
    </div>
  );
}

export function HardwareSnapshotList({ snapshots }: { snapshots: HardwareSnapshot[] }) {
  if (!snapshots || snapshots.length === 0) {
    return (
      <div className="text-xs text-muted-foreground italic">
        No hardware benchmarks or estimates attached.
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {snapshots.map((s, idx) => (
        <HardwareBadgePill
          key={s.snapshot_digest || idx}
          badge={s.badge}
          hardwareName={s.hardware_name}
          category={s.category}
          evidenceType={s.evidence_type}
        />
      ))}
    </div>
  );
}
