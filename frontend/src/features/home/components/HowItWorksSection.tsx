import { ArrowRight, Database, Award, Cpu, ShieldCheck, Activity, CheckCircle2 } from "lucide-react";
import type { LifecycleStage } from "../types";
import { useScrollReveal } from "../hooks/useScrollReveal";

export function HowItWorksSection() {
  const sectionRef = useScrollReveal();

  const stages: (LifecycleStage & {
    icon: typeof Database;
    gateNotice?: string;
    gateColor: "emerald" | "orange";
    stageOutput: string;
  })[] = [
    {
      number: "01",
      name: "Prepare",
      summary: "Ingest, organize, version and protect the data used in AI workflows.",
      deliverable: "Sanitized, PII-masked dataset with verified Gate 1 authorization",
      gateNotice: "Gate 1: Data Masking",
      gateColor: "emerald",
      stageOutput: "dataset_v2.jsonl (Masked)",
      icon: Database,
    },
    {
      number: "02",
      name: "Evaluate",
      summary: "Establish evaluation criteria, test model behavior and generate measurable results.",
      deliverable: "Quantitative scorecards across deterministic benchmark test suites",
      gateColor: "emerald",
      stageOutput: "eval_scorecard.json",
      icon: Award,
    },
    {
      number: "03",
      name: "Optimize",
      summary: "Compare experiments, understand performance trade-offs and assess resource feasibility.",
      deliverable: "VRAM-checked, quantization-tested candidate model with budget sign-off",
      gateNotice: "Gate 2: Hardware Preflight",
      gateColor: "orange",
      stageOutput: "vram_preflight.json",
      icon: Cpu,
    },
    {
      number: "04",
      name: "Govern & Release",
      summary: "Verify provenance, validate artifacts and obtain the required human approvals.",
      deliverable: "Ed25519 cryptographically signed artifact bundle and release manifest",
      gateNotice: "Gate 3: Release Sign-off",
      gateColor: "emerald",
      stageOutput: "release_manifest.sig",
      icon: ShieldCheck,
    },
    {
      number: "05",
      name: "Operate",
      summary: "Activate approved releases, manage runtime environments and monitor operational performance.",
      deliverable: "Healthy customer runtime deployment with live SLO observability & rollback",
      gateColor: "orange",
      stageOutput: "runtime_telemetry (Active)",
      icon: Activity,
    },
  ];

  return (
    <section
      id="how-it-works"
      ref={sectionRef}
      className="py-28 lg:py-40 bg-white text-slate-900 border-b border-slate-200/80 relative noise-overlay"
    >
      {/* Ambient background glows */}
      <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-[550px] h-[350px] bg-emerald-100/40 rounded-full blur-3xl pointer-events-none orb-2" />
      <div className="absolute top-1/3 right-1/4 w-[450px] h-[300px] bg-orange-100/35 rounded-full blur-3xl pointer-events-none orb-1" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header Block with Scroll Reveal */}
        <div className="max-w-3xl scroll-reveal">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-mono tracking-wider uppercase mb-5 font-semibold premium-pill">
            SECTION 04 // CONNECTED ARCHITECTURE
          </div>
          <h2 className="text-3xl sm:text-5xl font-black tracking-[-0.035em] text-slate-950 leading-[1.12] font-display">
            From data readiness to{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 via-teal-600 to-orange-500">
              operational AI.
            </span>
          </h2>
          <p className="mt-5 text-slate-600 text-base sm:text-lg leading-relaxed font-normal">
            Mizan coordinates the complete lifecycle in a continuous, traceable pipeline.
            Each stage produces verifiable artifacts, quantitative evidence, and explicit sign-offs
            before advancing to the next operational boundary.
          </p>
        </div>

        {/* 5-Stage Connected Pipeline Flow with Staggered Scroll Reveal */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-5 gap-4 relative">
          {stages.map((stage, idx) => {
            const Icon = stage.icon;
            const isLast = idx === stages.length - 1;
            const isOrange = stage.gateColor === "orange";
            const delay = `${0.1 + idx * 0.08}s`;

            return (
              <div
                key={stage.number}
                className="relative flex flex-col justify-between p-6 rounded-3xl bg-white border border-slate-200/90 hover:border-emerald-400 hover:shadow-2xl hover:shadow-emerald-500/10 transition-all group shadow-sm scroll-reveal overflow-hidden"
                style={{ "--reveal-delay": delay } as React.CSSProperties}
              >
                {/* Horizontal flow connector indicator on desktop - perfectly aligned to stage icon row */}
                {!isLast && (
                  <div className="hidden md:flex absolute -right-3 top-10.5 -translate-y-1/2 z-20 w-6 h-6 rounded-full bg-white border border-slate-300 items-center justify-center text-slate-500 shadow-sm">
                    <ArrowRight size={11} className="text-emerald-600" />
                  </div>
                )}

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-xs font-mono font-bold px-2 py-0.5 rounded-lg border ${
                        isOrange
                          ? "text-orange-700 bg-orange-50 border-orange-200"
                          : "text-emerald-700 bg-emerald-50 border-emerald-200"
                      }`}
                    >
                      STAGE {stage.number}
                    </span>
                    <div
                      className={`w-9 h-9 rounded-xl flex items-center justify-center border transition-colors ${
                        isOrange
                          ? "bg-orange-50 text-orange-600 border-orange-200 group-hover:bg-orange-500 group-hover:text-white"
                          : "bg-emerald-50 text-emerald-600 border-emerald-200 group-hover:bg-emerald-600 group-hover:text-white"
                      }`}
                    >
                      <Icon size={16} />
                    </div>
                  </div>

                  <div>
                    <h3 className="text-lg font-bold text-slate-900 tracking-tight font-display text-balance">{stage.name}</h3>
                    <p className="text-xs text-slate-600 mt-2 leading-relaxed font-normal text-pretty">
                      {stage.summary}
                    </p>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100 space-y-2.5">
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/70 text-[10px] font-mono text-slate-700 space-y-1">
                    <span className="text-slate-400 block uppercase font-medium">STAGE ARTIFACT:</span>
                    <strong className="text-slate-900 block truncate">{stage.stageOutput}</strong>
                  </div>

                  {stage.gateNotice ? (
                    <div
                      className={`inline-flex items-center gap-1.5 text-[10px] font-mono font-semibold px-2.5 py-1 rounded-lg border w-full justify-center ${
                        isOrange
                          ? "text-orange-700 bg-orange-50 border-orange-200"
                          : "text-emerald-700 bg-emerald-50 border-emerald-200"
                      }`}
                    >
                      <CheckCircle2 size={11} className={isOrange ? "text-orange-600" : "text-emerald-600"} />
                      <span>{stage.gateNotice}</span>
                    </div>
                  ) : (
                    <div className="inline-flex items-center gap-1.5 text-[10px] font-mono font-semibold text-slate-600 bg-slate-100/80 px-2.5 py-1 rounded-lg border border-slate-200 w-full justify-center">
                      <span>Deterministic Scorecard</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Transition Summary Bar with Scroll Reveal */}
        <div
          className="mt-14 p-6 rounded-3xl bg-gradient-to-r from-emerald-50/80 via-white to-orange-50/80 border border-slate-200/90 text-xs text-slate-700 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm scroll-reveal relative overflow-hidden"
          style={{ "--reveal-delay": "0.3s" } as React.CSSProperties}
        >
          <div className="flex items-center gap-3">
            <span className="w-3 h-3 rounded-full bg-emerald-500 pulse-ring shrink-0" />
            <span>
              <strong className="text-slate-900 font-bold font-display">Continuous Traceability:</strong> Every model release cryptographically references its source dataset version, benchmark scorecard, and authorized signing identity.
            </span>
          </div>
          <span className="font-mono text-slate-600 text-[11px] bg-white px-3.5 py-1.5 rounded-xl border border-slate-200/80 shadow-xs font-medium shrink-0">
            No unlinked experiments · No unsigned deployments
          </span>
        </div>
      </div>
    </section>
  );
}
