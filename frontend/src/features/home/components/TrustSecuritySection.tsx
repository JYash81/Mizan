import {
  ShieldCheck,
  Lock,
  UserCheck,
  FileCheck2,
  KeyRound,
  Terminal,
  Activity,
  RotateCcw,
} from "lucide-react";
import { useScrollReveal } from "../hooks/useScrollReveal";

export function TrustSecuritySection() {
  const sectionRef = useScrollReveal();

  const controls = [
    {
      icon: Lock,
      accent: "emerald",
      title: "Role-based access and workspace isolation",
      description: "Fine-grained tenant boundaries preventing cross-department dataset and model leakage.",
      tag: "WORKSPACE ISOLATION",
    },
    {
      icon: ShieldCheck,
      accent: "emerald",
      title: "Sensitive-data masking and dataset approval",
      description: "Automated PII/PHI detection, redaction, and Gate 1 human verification before data training.",
      tag: "GATE 1 DATA PRIVACY",
    },
    {
      icon: UserCheck,
      accent: "orange",
      title: "Explicit authorization workflows",
      description: "Multi-tiered role permissions ensuring only certified reviewers can approve compute or models.",
      tag: "AUTHORIZATION PROTOCOL",
    },
    {
      icon: KeyRound,
      accent: "emerald",
      title: "Cryptographic artifact verification",
      description: "Ed25519 signatures and SHA-256 package checksums validating untampered artifact lineage.",
      tag: "CRYPTOGRAPHIC PROVENANCE",
    },
    {
      icon: FileCheck2,
      accent: "emerald",
      title: "Human-controlled release approvals",
      description: "Mandatory Gate 3 sign-offs before any model or application can be published to the catalog.",
      tag: "GATE 3 RELEASE GOVERNANCE",
    },
    {
      icon: Terminal,
      accent: "orange",
      title: "Runtime command validation",
      description: "Customer runtime daemon validates execution parameters against signed manifests prior to start.",
      tag: "RUNTIME INTEGRITY",
    },
    {
      icon: Activity,
      accent: "emerald",
      title: "Privacy-conscious operational telemetry",
      description: "Monitors latency, memory, error rates, and health without capturing private user inference payloads.",
      tag: "TELEMETRY PRIVACY",
    },
    {
      icon: RotateCcw,
      accent: "orange",
      title: "Release revocation and rollback safeguards",
      description: "Immediate operational deactivation and version rollback if anomalies or regressions are detected.",
      tag: "FAILSAFE SAFEGUARDS",
    },
  ];

  return (
    <section
      id="trust-governance"
      ref={sectionRef}
      className="py-28 lg:py-40 bg-white text-slate-900 border-b border-slate-200/80 relative noise-overlay"
    >
      {/* Ambient background glows */}
      <div className="absolute top-1/4 left-1/3 w-[600px] h-[350px] bg-emerald-100/35 rounded-full blur-3xl pointer-events-none orb-1" />
      <div className="absolute bottom-1/3 right-1/4 w-[450px] h-[300px] bg-orange-100/30 rounded-full blur-3xl pointer-events-none orb-2" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header Block with Scroll Reveal */}
        <div className="max-w-3xl scroll-reveal">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-mono tracking-wider uppercase mb-5 font-semibold premium-pill">
            SECTION 06 // TRUST & GOVERNANCE ARCHITECTURE
          </div>
          <h2 className="text-3xl sm:text-5xl font-black tracking-[-0.035em] text-slate-950 leading-[1.12] font-display text-balance">
            Trust should be part of the architecture,{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 via-teal-600 to-orange-500">
              not an afterthought.
            </span>
          </h2>
          <p className="mt-5 text-slate-600 text-base sm:text-lg leading-relaxed font-normal text-pretty">
            AI systems require more than good model performance. Organizations also need visibility
            into data handling, access permissions, approvals, artifact integrity and operational
            decisions.
          </p>
        </div>

        {/* Three-Gate Human Authority Pipeline Banner with Scroll Reveal */}
        <div
          className="mt-16 p-7 sm:p-9 rounded-3xl bg-gradient-to-b from-white to-slate-50/80 border-2 border-emerald-500/20 shadow-2xl workbench-frame scroll-reveal relative overflow-hidden"
          style={{ "--reveal-delay": "0.15s" } as React.CSSProperties}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-5 border-b border-slate-200/80 gap-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-700">
                <KeyRound size={16} />
              </div>
              <span className="text-xs font-mono font-bold text-slate-900 uppercase tracking-wider font-display">
                THE THREE-GATE HUMAN AUTHORITY PROTOCOL
              </span>
            </div>
            <span className="text-[10px] font-mono font-semibold text-emerald-800 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200 w-fit">
              MANDATORY BOUNDARY ENFORCEMENT
            </span>
          </div>

          <div className="mt-7 grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Gate 01 */}
            <div className="p-6 rounded-2xl bg-white border border-emerald-200/90 shadow-sm space-y-2.5 hover:border-emerald-400 hover:shadow-lg transition-all duration-300">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-lg border border-emerald-200">
                  GATE 01
                </span>
                <span className="text-[10px] font-mono text-slate-400 font-semibold">DATA PRIVACY</span>
              </div>
              <h4 className="text-sm font-bold text-slate-900 font-display">Data Protection & Masking Approval</h4>
              <p className="text-xs text-slate-600 leading-relaxed font-normal">
                Ensures PII/PHI is masked and audited before raw documents enter model training or evaluation suites.
              </p>
            </div>

            {/* Gate 02 */}
            <div className="p-6 rounded-2xl bg-white border border-orange-200/90 shadow-sm space-y-2.5 hover:border-orange-400 hover:shadow-lg transition-all duration-300">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-orange-700 bg-orange-50 px-2.5 py-0.5 rounded-lg border border-orange-200">
                  GATE 02
                </span>
                <span className="text-[10px] font-mono text-slate-400 font-semibold">FINANCIAL COMPUTE</span>
              </div>
              <h4 className="text-sm font-bold text-slate-900 font-display">Hardware & Compute Spend Preflight</h4>
              <p className="text-xs text-slate-600 leading-relaxed font-normal">
                Enforces financial budget limits and preflights resource requirements before cloud compute is provisioned.
              </p>
            </div>

            {/* Gate 03 */}
            <div className="p-6 rounded-2xl bg-white border border-emerald-200/90 shadow-sm space-y-2.5 hover:border-emerald-400 hover:shadow-lg transition-all duration-300">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-lg border border-emerald-200">
                  GATE 03
                </span>
                <span className="text-[10px] font-mono text-slate-400 font-semibold">PROVENANCE SIGN-OFF</span>
              </div>
              <h4 className="text-sm font-bold text-slate-900 font-display">Artifact Release & Cryptographic Signing</h4>
              <p className="text-xs text-slate-600 leading-relaxed font-normal">
                Ed25519 signs model weights, evaluation reports, and manifests before catalog publishing and runtime deployment.
              </p>
            </div>
          </div>
        </div>

        {/* 8 Structured Controls Grid with Staggered Scroll Reveal */}
        <div className="mt-16 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {controls.map((ctrl, i) => {
            const Icon = ctrl.icon;
            const isOrange = ctrl.accent === "orange";
            const delay = `${0.05 + i * 0.05}s`;

            return (
              <div
                key={i}
                className="p-6 rounded-3xl bg-white border border-slate-200/90 hover:border-emerald-400 hover:shadow-xl hover:shadow-emerald-500/10 transition-all duration-300 flex flex-col justify-between space-y-4 shadow-sm group scroll-reveal relative overflow-hidden"
                style={{ "--reveal-delay": delay } as React.CSSProperties}
              >
                {/* Subtle top indicator bar */}
                <div
                  className={`absolute top-0 left-0 right-0 h-1 transition-all ${
                    isOrange ? "bg-orange-400 group-hover:h-1.5" : "bg-emerald-500 group-hover:h-1.5"
                  }`}
                />

                <div className="flex items-center justify-between">
                  <div
                    className={`w-10 h-10 rounded-2xl flex items-center justify-center border transition-colors ${
                      isOrange
                        ? "bg-orange-50 text-orange-600 border-orange-200 group-hover:bg-orange-500 group-hover:text-white"
                        : "bg-emerald-50 text-emerald-600 border-emerald-200 group-hover:bg-emerald-600 group-hover:text-white"
                    }`}
                  >
                    <Icon size={20} />
                  </div>
                  <span
                    className={`text-[9px] font-mono font-bold tracking-wider px-2 py-0.5 rounded border ${
                      isOrange
                        ? "text-orange-700 bg-orange-50 border-orange-200"
                        : "text-emerald-700 bg-emerald-50 border-emerald-200"
                    }`}
                  >
                    {ctrl.tag}
                  </span>
                </div>

                <div>
                  <h3 className="text-sm font-bold text-slate-900 leading-snug font-display">
                    {ctrl.title}
                  </h3>
                  <p className="text-xs text-slate-600 mt-2 leading-relaxed font-normal">
                    {ctrl.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Concluding Statement with Scroll Reveal */}
        <div
          className="mt-16 max-w-3xl mx-auto p-7 sm:p-9 rounded-3xl bg-gradient-to-r from-emerald-50/80 via-white to-orange-50/80 border border-slate-200/90 text-center shadow-lg scroll-reveal relative overflow-hidden"
          style={{ "--reveal-delay": "0.3s" } as React.CSSProperties}
        >
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-teal-400 to-orange-500" />
          <p className="text-base sm:text-lg font-bold text-slate-900 font-display">
            Because dependable AI requires both technical capability and responsible operational control.
          </p>
          <p className="mt-2 text-xs text-slate-600">
            Mizan embeds these controls at code, data, and protocol levels—ensuring every model release is accountable and verifiable.
          </p>
        </div>
      </div>
    </section>
  );
}
