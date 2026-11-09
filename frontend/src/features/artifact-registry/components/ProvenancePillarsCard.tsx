import { CheckCircle2, AlertTriangle, XCircle, ShieldCheck, Database, FileCode2, Cpu, Award } from "lucide-react";
import type { ModelVersion } from "../types";

interface ProvenancePillarsCardProps {
  version: ModelVersion;
}

export function ProvenancePillarsCard({ version }: ProvenancePillarsCardProps) {
  const summary = version.provenance_summary as Record<string, unknown> | null;
  const checks = (summary?.checks as Record<string, { passed: boolean; details: Record<string, unknown> }>) || {};
  const warnings = (summary?.warnings as string[]) || [];
  const blockers = (summary?.blockers as string[]) || [];

  const pillars = [
    {
      id: "BASE_MODEL_LICENSE",
      title: "1. Base Model & License",
      icon: ShieldCheck,
      desc: version.source_model_key,
      check: checks.BASE_MODEL_LICENSE,
    },
    {
      id: "DATASET_GATE1_DATA_RIGHTS",
      title: "2. Data Rights & Gate 1",
      icon: Database,
      desc: version.dataset_version_digest ? `Digest: ${version.dataset_version_digest.slice(0, 12)}...` : "Base / Pretrained",
      check: checks.DATASET_GATE1_DATA_RIGHTS,
    },
    {
      id: "BUILD_MANIFEST_PROVENANCE",
      title: "3. Build Manifest & Recipe",
      icon: FileCode2,
      desc: version.recipe_key,
      check: checks.BUILD_MANIFEST_PROVENANCE,
    },
    {
      id: "EVALUATION_EVIDENCE",
      title: "4. Evaluation & Quality",
      icon: Award,
      desc: version.quality_delta !== null && version.quality_delta !== undefined
        ? `Score: ${version.final_evaluation_score ?? "-"} (Δ ${version.quality_delta > 0 ? "+" : ""}${version.quality_delta})`
        : "Standard Evaluation",
      check: checks.EVALUATION_EVIDENCE,
    },
    {
      id: "HARDWARE_FEASIBILITY",
      title: "5. Hardware Feasibility",
      icon: Cpu,
      desc: `${version.min_ram_mb} MB RAM / ${version.min_vram_mb} MB VRAM`,
      check: checks.HARDWARE_FEASIBILITY,
    },
  ];

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-sm space-y-6">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <h3 className="text-lg font-semibold tracking-tight text-foreground flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-500" />
            5-Pillar Release Provenance Verification
          </h3>
          <p className="text-sm text-muted-foreground mt-0.5">
            Strict enterprise audit verifying licensing, privacy Gate 1, training integrity, evaluation metrics, and hardware.
          </p>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
            blockers.length === 0
              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
              : "bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20"
          }`}
        >
          {blockers.length === 0 ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5" />
              Provenance Verified
            </>
          ) : (
            <>
              <XCircle className="w-3.5 h-3.5" />
              {blockers.length} Blocker(s)
            </>
          )}
        </span>
      </div>

      {/* Pillars Grid */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {pillars.map((p) => {
          const Icon = p.icon;
          const passed = p.check ? p.check.passed : true;
          return (
            <div
              key={p.id}
              className={`p-4 rounded-lg border text-left transition-colors ${
                passed
                  ? "bg-background/50 border-border hover:border-primary/40"
                  : "bg-red-500/5 border-red-500/30"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 rounded-md bg-secondary text-primary">
                  <Icon className="w-4 h-4" />
                </div>
                {passed ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-500" />
                )}
              </div>
              <h4 className="text-xs font-semibold text-foreground truncate">{p.title}</h4>
              <p className="text-xs text-muted-foreground mt-1 truncate" title={p.desc}>
                {p.desc}
              </p>
            </div>
          );
        })}
      </div>

      {/* Warnings & Blockers Notices */}
      {blockers.length > 0 && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 space-y-1">
          <div className="flex items-center gap-2 text-sm font-semibold text-red-600 dark:text-red-400">
            <XCircle className="w-4 h-4" />
            Release Blockers Detected:
          </div>
          <ul className="list-disc list-inside text-xs text-red-600/90 dark:text-red-400/90 space-y-0.5">
            {blockers.map((b, idx) => (
              <li key={idx}>{b}</li>
            ))}
          </ul>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 space-y-1">
          <div className="flex items-center gap-2 text-sm font-semibold text-amber-600 dark:text-amber-400">
            <AlertTriangle className="w-4 h-4" />
            Compliance Advisories & Warnings:
          </div>
          <ul className="list-disc list-inside text-xs text-amber-700 dark:text-amber-300 space-y-0.5">
            {warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
