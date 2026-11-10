import { Split, HelpCircle, FileSearch, EyeOff, AlertTriangle, CheckCircle2 } from "lucide-react";
import { useScrollReveal } from "../hooks/useScrollReveal";

export function WhyMizanSection() {
  const sectionRef = useScrollReveal();

  const problems = [
    {
      id: "fragmented-workflows",
      icon: Split,
      number: "01",
      title: "Fragmented workflows",
      description:
        "AI development often spans disconnected tools, datasets, evaluation processes and deployment environments.",
      impact:
        "Engineers transfer unversioned datasets from local notebooks, losing provenance between model weights and training runs.",
      accent: "emerald",
    },
    {
      id: "uncertain-decisions",
      icon: HelpCircle,
      number: "02",
      title: "Uncertain model decisions",
      description:
        "Model selection without consistent evaluation can lead to choices based on assumptions rather than measurable results.",
      impact:
        "Teams deploy over-sized or erratic models without quantitative benchmarks, latency guarantees, or domain accuracy verification.",
      accent: "orange",
    },
    {
      id: "limited-governance",
      icon: FileSearch,
      number: "03",
      title: "Limited governance and traceability",
      description:
        "Without structured approvals, provenance and release controls, it becomes difficult to establish who approved what, and on what evidence.",
      impact:
        "Auditors, security officers, and enterprise leaders face black-box releases lacking cryptographic provenance or sign-off history.",
      accent: "emerald",
    },
    {
      id: "deployment-visibility",
      icon: EyeOff,
      number: "04",
      title: "Deployment without sufficient visibility",
      description:
        "A successful experiment does not automatically translate into a reliable operational system. Resource constraints, runtime health and changing performance need ongoing attention.",
      impact:
        "Production instances face silent degradation, memory overruns, and uncoordinated updates without automated rollback protection.",
      accent: "orange",
    },
  ];

  return (
    <section
      id="why-mizan"
      ref={sectionRef}
      className="py-28 lg:py-40 bg-[#FAFDFB] text-slate-900 border-b border-slate-200/80 relative overflow-hidden noise-overlay"
    >
      {/* Ambient background light orbs */}
      <div className="absolute top-1/4 right-[-5%] w-[550px] h-[550px] bg-emerald-200/25 rounded-full blur-3xl pointer-events-none orb-2" />
      <div className="absolute bottom-1/4 left-[-5%] w-[550px] h-[550px] bg-orange-200/20 rounded-full blur-3xl pointer-events-none orb-3" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header Block with Scroll Reveal */}
        <div className="max-w-3xl scroll-reveal">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-mono font-bold tracking-wider uppercase mb-5 premium-pill">
            SECTION 01 // THE STRATEGIC REALITY
          </div>
          <h2 className="text-3xl sm:text-5xl font-black tracking-[-0.035em] text-slate-950 leading-[1.12] font-display text-balance">
            AI adoption is accelerating.{" "}
            <span className="gradient-text-orange">
              Control over the AI lifecycle must keep pace.
            </span>
          </h2>
          <div className="mt-6 space-y-4 text-slate-600 leading-relaxed text-base sm:text-lg font-normal text-pretty">
            <p>
              Organizations are adopting AI across products, workflows and operations. But building a
              dependable AI system involves much more than selecting a model.
            </p>
            <p>
              Data must be prepared and protected. Models must be evaluated against meaningful criteria.
              Experiments must be comparable. Hardware and resource requirements must be understood. Approvals
              must be traceable. Releases must be verified. Deployed systems must remain observable and
              manageable.
            </p>
            <p>
              When these activities happen across disconnected tools and processes, teams struggle to
              establish consistency, explain decisions and maintain control throughout the lifecycle.
            </p>
          </div>
          <div className="mt-7 inline-block px-5 py-3 rounded-2xl bg-white/90 backdrop-blur-md border border-emerald-500/30 text-emerald-950 font-bold text-sm sm:text-base shadow-sm">
            Mizan exists to bring structure to that complexity.
          </div>
        </div>

        {/* Visual Architectural Comparison: Disconnected Chaos vs. Governed Mizan */}
        <div className="mt-20 grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
          {/* Disconnected Pipeline Box (The Ungoverned Reality) */}
          <div
            className="p-7 sm:p-9 rounded-3xl bg-white/80 backdrop-blur-md border border-orange-200/80 shadow-md hover:border-orange-300 transition-all flex flex-col justify-between scroll-reveal relative overflow-hidden"
            style={{ "--reveal-delay": "0.15s" } as React.CSSProperties}
          >
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-orange-100">
                <div className="flex items-center gap-2 text-orange-800 text-xs font-mono font-bold uppercase tracking-wider">
                  <AlertTriangle size={16} className="text-orange-600" />
                  THE UNGOVERNED REALITY
                </div>
                <span className="text-[10px] font-mono font-bold text-orange-800 bg-orange-100/80 px-2.5 py-0.5 rounded-full border border-orange-300">
                  FRAGMENTED RISK
                </span>
              </div>

              <div className="mt-6 space-y-3.5 text-xs font-mono font-medium">
                <div className="p-3.5 rounded-xl bg-orange-50/50 border border-orange-200/60 flex items-center justify-between text-slate-700">
                  <span>01. Unprotected Data Ingestion</span>
                  <span className="text-rose-600 font-bold">PII Leaks / Untracked</span>
                </div>
                <div className="p-3.5 rounded-xl bg-orange-50/50 border border-orange-200/60 flex items-center justify-between text-slate-700">
                  <span>02. Vibe-Based Evaluation</span>
                  <span className="text-rose-600 font-bold">Subjective / No Scores</span>
                </div>
                <div className="p-3.5 rounded-xl bg-orange-50/50 border border-orange-200/60 flex items-center justify-between text-slate-700">
                  <span>03. Blind Compute Provisioning</span>
                  <span className="text-rose-600 font-bold">GPU Budget Runaways</span>
                </div>
                <div className="p-3.5 rounded-xl bg-orange-50/50 border border-orange-200/60 flex items-center justify-between text-slate-700">
                  <span>04. Unsigned Model Checkpoints</span>
                  <span className="text-rose-600 font-bold">Zero Cryptographic Proof</span>
                </div>
                <div className="p-3.5 rounded-xl bg-orange-50/50 border border-orange-200/60 flex items-center justify-between text-slate-700">
                  <span>05. Opaque Runtime Failures</span>
                  <span className="text-rose-600 font-bold">No Rollback Safeguard</span>
                </div>
              </div>
            </div>

            <p className="mt-6 pt-4 border-t border-orange-100 text-xs text-slate-600 leading-relaxed font-normal">
              Without structured boundaries, each stage is an isolated island. Approvals are lost in email threads, and regressions are diagnosed after customer-facing outages occur.
            </p>
          </div>

          {/* Governed Mizan Standard Box (The Mizan Governed Standard) */}
          <div
            className="p-7 sm:p-9 rounded-3xl bg-gradient-to-b from-white to-emerald-50/30 backdrop-blur-md border-2 border-emerald-500/30 shadow-xl shadow-emerald-950/5 flex flex-col justify-between scroll-reveal relative overflow-hidden"
            style={{ "--reveal-delay": "0.3s" } as React.CSSProperties}
          >
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-emerald-200/70">
                <div className="flex items-center gap-2 text-emerald-900 text-xs font-mono font-bold uppercase tracking-wider">
                  <CheckCircle2 size={16} className="text-emerald-700" />
                  THE MIZAN GOVERNED STANDARD
                </div>
                <span className="text-[10px] font-mono font-bold text-emerald-800 bg-emerald-100/80 px-2.5 py-0.5 rounded-full border border-emerald-300">
                  CONTINUOUS TRACEABILITY
                </span>
              </div>

              <div className="mt-6 space-y-3.5 text-xs font-mono font-medium">
                <div className="p-3.5 rounded-xl bg-white border border-emerald-200/80 flex items-center justify-between text-slate-800 shadow-xs">
                  <span className="flex items-center gap-2"><span className="text-emerald-700 font-bold">01.</span> Gate 1: PII Masking Approval</span>
                  <span className="text-emerald-700 font-bold">Audited & Signed</span>
                </div>
                <div className="p-3.5 rounded-xl bg-white border border-emerald-200/80 flex items-center justify-between text-slate-800 shadow-xs">
                  <span className="flex items-center gap-2"><span className="text-emerald-700 font-bold">02.</span> Deterministic Eval Suites</span>
                  <span className="text-emerald-700 font-bold">Metric Scorecards</span>
                </div>
                <div className="p-3.5 rounded-xl bg-white border border-emerald-200/80 flex items-center justify-between text-slate-800 shadow-xs">
                  <span className="flex items-center gap-2"><span className="text-emerald-700 font-bold">03.</span> Gate 2: Hardware Preflight</span>
                  <span className="text-orange-700 font-bold">VRAM & Cost Capped</span>
                </div>
                <div className="p-3.5 rounded-xl bg-white border border-emerald-200/80 flex items-center justify-between text-slate-800 shadow-xs">
                  <span className="flex items-center gap-2"><span className="text-emerald-700 font-bold">04.</span> Gate 3: Ed25519 Artifact Signing</span>
                  <span className="text-emerald-700 font-bold">Tamper-Evident</span>
                </div>
                <div className="p-3.5 rounded-xl bg-white border border-emerald-200/80 flex items-center justify-between text-slate-800 shadow-xs">
                  <span className="flex items-center gap-2"><span className="text-emerald-700 font-bold">05.</span> Customer Runtime & Blue/Green</span>
                  <span className="text-orange-700 font-bold">1-Click Rollback</span>
                </div>
              </div>
            </div>

            <p className="mt-6 pt-4 border-t border-emerald-200/70 text-xs text-slate-700 leading-relaxed font-normal">
              Every transition requires explicit, evidence-based verification. Artifacts carry their complete lineage from raw data ingestion to production inference.
            </p>
          </div>
        </div>

        {/* 4 Problem Statements Breakdown with Staggered Scroll Reveal */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-2 gap-6">
          {problems.map((prob, idx) => {
            const Icon = prob.icon;
            const isOrange = prob.accent === "orange";
            const delay = `${0.1 + idx * 0.1}s`;

            return (
              <div
                key={prob.id}
                className="p-7 sm:p-8 rounded-3xl bg-white border border-slate-200/90 shadow-sm hover:shadow-xl hover:border-emerald-300 transition-all flex flex-col justify-between scroll-reveal group"
                style={{ "--reveal-delay": delay } as React.CSSProperties}
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div
                      className={`w-11 h-11 rounded-2xl flex items-center justify-center border transition-colors ${
                        isOrange
                          ? "bg-orange-50 text-orange-700 border-orange-200 group-hover:bg-orange-600 group-hover:text-white"
                          : "bg-emerald-50 text-emerald-700 border-emerald-200 group-hover:bg-emerald-600 group-hover:text-white"
                      }`}
                    >
                      <Icon size={20} />
                    </div>
                    <span className="text-xs font-mono font-bold text-slate-400">
                      CHALLENGE {prob.number}
                    </span>
                  </div>

                  <h3 className="text-lg font-bold text-slate-950 tracking-tight font-display">{prob.title}</h3>
                  <p className="text-sm text-slate-600 leading-relaxed font-normal">
                    {prob.description}
                  </p>
                  <p className="text-xs text-slate-500 leading-relaxed pt-3 border-t border-slate-100 font-normal">
                    <strong className="text-slate-800 font-semibold">Enterprise Impact:</strong> {prob.impact}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Concluding Statement Banner (Deep Forest Emerald + Radiant Warm Orange CTA) */}
        <div
          className="mt-16 p-8 sm:p-10 rounded-3xl bg-gradient-to-r from-emerald-950 via-slate-900 to-emerald-950 text-white flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 shadow-2xl relative overflow-hidden scroll-reveal"
          style={{ "--reveal-delay": "0.2s" } as React.CSSProperties}
        >
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-teal-400 to-orange-500" />
          <div className="space-y-1.5 relative z-10">
            <span className="text-xs font-mono font-bold text-emerald-400 tracking-wider uppercase">
              THE MIZAN FOUNDATION
            </span>
            <p className="text-lg sm:text-xl font-bold text-white tracking-tight font-display">
              Mizan connects these stages through a structured, evidence-driven AI lifecycle.
            </p>
          </div>
          <a
            href="#platform"
            className="btn-orange-luxury shrink-0 px-7 py-3.5 rounded-xl text-white font-display font-bold text-xs uppercase tracking-wider transition-all cursor-pointer relative z-10"
          >
            Explore Platform Capabilities
          </a>
        </div>
      </div>
    </section>
  );
}
