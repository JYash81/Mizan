import { Scale, ShieldCheck, GitCommit, Gauge, Network, CheckCircle2 } from "lucide-react";
import type { Differentiator } from "../types";
import { useScrollReveal } from "../hooks/useScrollReveal";

export function DifferentiatorsSection() {
  const sectionRef = useScrollReveal();

  const differentiators: (Differentiator & {
    icon: typeof Scale;
    accentColor: "emerald" | "orange";
    architecturalStandard: string;
  })[] = [
    {
      id: "evidence-over-assumptions",
      icon: Scale,
      accentColor: "emerald",
      title: "Evidence over assumptions",
      summary: "Structure model comparisons and optimization around measurable evaluation results.",
      detail:
        "Instead of subjective impressions or marketing benchmarks, Mizan runs multi-engine deterministic test suites on your domain data, measuring precision, latency, throughput, and error rates quantitatively.",
      architecturalStandard: "Deterministic Multi-Engine Benchmarks vs. Guesswork",
    },
    {
      id: "governance-by-design",
      icon: ShieldCheck,
      accentColor: "orange",
      title: "Governance by design",
      summary: "Use distinct approval workflows, role-based access and traceable decision records.",
      detail:
        "Human review is built directly into lifecycle boundaries—requiring verified sign-offs before documents are masked, compute budgets are spent, and release manifests are published to production.",
      architecturalStandard: "Three-Gate Human Authority Protocol vs. Unchecked Deployments",
    },
    {
      id: "verifiable-provenance",
      icon: GitCommit,
      accentColor: "emerald",
      title: "Verifiable model provenance",
      summary: "Connect model versions, build information, artifacts, release manifests and approval records.",
      detail:
        "Every deployed artifact carries an immutable provenance trail linking its base weights, training dataset hash, hyper-parameter recipe, evaluation scorecard, and signing identity.",
      architecturalStandard: "Ed25519 Cryptographic Manifests vs. Lost Audit Lineage",
    },
    {
      id: "operational-oversight",
      icon: Gauge,
      accentColor: "orange",
      title: "Deployment with operational oversight",
      summary: "Connect approved releases to runtime environments, health monitoring and controlled rollback processes.",
      detail:
        "Deployment is not the end of the lifecycle. Mizan links runtime health, SLO telemetry, and incident notifications directly to release versions, enabling rapid rollback if anomalies occur.",
      architecturalStandard: "Continuous Telemetry & Instant Rollback vs. Blind Production Outages",
    },
    {
      id: "flexible-architecture",
      icon: Network,
      accentColor: "emerald",
      title: "Flexible deployment architecture",
      summary: "Support customer runtime architectures designed for local operation and offline-capable execution where configured and supported.",
      detail:
        "Separate your management plane from execution environments. Run models within customer-controlled private VPCs or on-premises nodes without exposing sensitive payloads to external providers.",
      architecturalStandard: "Customer-Local Private Daemon vs. External Cloud Lock-in",
    },
  ];

  return (
    <section
      id="differentiators"
      ref={sectionRef}
      className="py-28 lg:py-40 bg-[#FAFDFB] text-slate-900 border-b border-slate-200/80 relative noise-overlay"
    >
      {/* Ambient background glows */}
      <div className="absolute top-1/3 right-1/4 w-[500px] h-[350px] bg-emerald-100/30 rounded-full blur-3xl pointer-events-none orb-2" />
      <div className="absolute bottom-1/4 left-1/4 w-[400px] h-[300px] bg-orange-100/30 rounded-full blur-3xl pointer-events-none orb-1" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header Block with Scroll Reveal */}
        <div className="max-w-3xl scroll-reveal">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-orange-50 border border-orange-200 text-orange-800 text-xs font-mono tracking-wider uppercase mb-5 font-semibold premium-pill">
            SECTION 05 // ARCHITECTURAL DIFFERENTIATION
          </div>
          <h2 className="text-3xl sm:text-5xl font-black tracking-[-0.035em] text-slate-950 leading-[1.12] font-display">
            Beyond experimentation.{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 via-teal-600 to-orange-500">
              Built around evidence, governance and control.
            </span>
          </h2>
          <p className="mt-5 text-slate-600 text-base sm:text-lg leading-relaxed font-normal">
            Most AI tooling stops at model playground prompts or ad-hoc scripts. Mizan is engineered
            for organizations where repeatability, verifiable evidence, and operational accountability
            are core technical imperatives.
          </p>
        </div>

        {/* 5 Differentiator Cards Bento Grid with Staggered Scroll Reveal */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 items-stretch">
          {differentiators.map((diff, idx) => {
            const Icon = diff.icon;
            const isOrange = diff.accentColor === "orange";
            const delay = `${0.1 + idx * 0.08}s`;
            const isFeatured = idx === 0;

            return (
              <div
                key={diff.id}
                className={`p-7 sm:p-9 rounded-3xl bg-white border border-slate-200/90 hover:border-emerald-400 hover:shadow-2xl hover:shadow-emerald-500/10 transition-all duration-300 flex flex-col justify-between shadow-sm group scroll-reveal relative overflow-hidden ${
                  isFeatured ? "lg:col-span-2" : "lg:col-span-1"
                }`}
                style={{ "--reveal-delay": delay } as React.CSSProperties}
              >
                {/* Subtle top indicator bar */}
                <div
                  className={`absolute top-0 left-0 right-0 h-1 transition-all ${
                    isOrange ? "bg-orange-400 group-hover:h-1.5" : "bg-emerald-500 group-hover:h-1.5"
                  }`}
                />

                <div className="space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div
                      className={`w-11 h-11 rounded-2xl flex items-center justify-center border transition-colors ${
                        isOrange
                          ? "bg-orange-50 text-orange-600 border-orange-200 group-hover:bg-orange-500 group-hover:text-white"
                          : "bg-emerald-50 text-emerald-600 border-emerald-200 group-hover:bg-emerald-600 group-hover:text-white"
                      }`}
                    >
                      <Icon size={20} />
                    </div>
                    <span className="text-xs font-mono font-semibold text-slate-400">
                      DIFF 0{idx + 1}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-xl font-bold text-slate-900 tracking-tight font-display text-balance">{diff.title}</h3>
                    <p
                      className={`text-xs font-mono mt-1.5 font-semibold tracking-wide ${
                        isOrange ? "text-orange-700" : "text-emerald-700"
                      }`}
                    >
                      {diff.summary}
                    </p>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed font-normal pt-2 border-t border-slate-100 text-pretty">
                    {diff.detail}
                  </p>
                </div>

                <div className="mt-6 pt-3 border-t border-slate-100 text-[10px] font-mono text-slate-600 flex items-center gap-1.5">
                  <CheckCircle2
                    size={13}
                    className={`shrink-0 ${isOrange ? "text-orange-600" : "text-emerald-600"}`}
                  />
                  <span className="truncate font-medium">{diff.architecturalStandard}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Engineering Integrity Statement with Scroll Reveal */}
        <div
          className="mt-16 p-7 sm:p-9 rounded-3xl bg-gradient-to-r from-emerald-50/70 via-white to-orange-50/70 border border-slate-200/90 text-xs text-slate-700 leading-relaxed max-w-4xl mx-auto text-center font-normal shadow-sm scroll-reveal relative overflow-hidden"
          style={{ "--reveal-delay": "0.25s" } as React.CSSProperties}
        >
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-teal-400 to-orange-500" />
          <p>
            <strong className="text-slate-900 font-bold font-display">Engineered with Architectural Integrity:</strong>{" "}
            Mizan avoids speculative hype and exaggerated promises. It provides concrete, demonstrable
            capabilities—giving your engineers, platform architects, and governance officers the exact
            levers required to operationalize AI responsibly.
          </p>
        </div>
      </div>
    </section>
  );
}
