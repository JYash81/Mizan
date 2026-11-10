import { Building2, Code2, Cpu, ShieldAlert, CheckCircle2 } from "lucide-react";
import { useScrollReveal } from "../hooks/useScrollReveal";

export function AudienceSection() {
  const sectionRef = useScrollReveal();

  const audiences = [
    {
      id: "enterprise-teams",
      icon: Building2,
      role: "ENTERPRISE AI TEAMS",
      title: "Cross-Functional AI Organizations",
      description:
        "For organizations developing AI capabilities across departments, products and business processes.",
      challenge: "Disconnected evaluation criteria, uncoordinated model choices, and untracked releases across business units.",
      solution: "Centralized workspace isolation, standardized evaluation suites, and unified audit trails.",
      capabilities: [
        "Multi-tenant workspace isolation with RBAC",
        "Consistent evaluation baselines across teams",
        "Traceable sign-offs for compliance and executive review",
      ],
      theme: "emerald",
    },
    {
      id: "ml-engineers",
      icon: Code2,
      role: "ML & AI ENGINEERS",
      title: "Practitioners & Model Builders",
      description:
        "For engineers who need to compare models, evaluate results, understand resource constraints, manage artifacts and move validated implementations towards deployment.",
      challenge: "Subjective evaluation, unexpected VRAM overflows, and irreproducible training checkpoints.",
      solution: "Deterministic multi-engine benchmarks, VRAM preflight calculators, and LoRA build pipelines.",
      capabilities: [
        "Side-by-side metric comparisons (exact, semantic, regex)",
        "Preflight hardware calculators (fp16, 8bit, 4bit AWQ)",
        "Versioned artifact manifests with hyper-parameter lineage",
      ],
      theme: "orange",
    },
    {
      id: "platform-infra",
      icon: Cpu,
      role: "PLATFORM & INFRASTRUCTURE",
      title: "Operations & Reliability Engineers",
      description:
        "For teams responsible for model lifecycle operations, release control, deployment environments, runtime reliability and operational oversight.",
      challenge: "Runaway cloud GPU costs, opaque production degradations, and high-risk manual updates.",
      solution: "Gate 2 budget sign-offs, zero-downtime blue/green slots, and automated rollback triggers.",
      capabilities: [
        "Gate 2 spend approvals before cloud compute execution",
        "Customer runtime daemon with blue/green slot activation",
        "Real-time SLO monitoring and 1-click artifact rollback",
      ],
      theme: "emerald",
    },
    {
      id: "data-sensitive",
      icon: ShieldAlert,
      role: "DATA-SENSITIVE ORGANIZATIONS",
      title: "Security & Governance Officers",
      description:
        "For organizations that need stronger control over datasets, sensitive information, approval workflows, artifact provenance and customer-controlled runtime environments.",
      challenge: "Accidental PII/PHI leakage into training data, untracked models, and external payload transmission.",
      solution: "Gate 1 automated masking, Ed25519 signing, and private local runtime execution.",
      capabilities: [
        "Gate 1 automated PII/PHI detection & redaction",
        "Ed25519 cryptographic release signing (Gate 3)",
        "Local offline-capable runtime with zero payload egress",
      ],
      theme: "orange",
    },
  ];

  return (
    <section
      id="audience"
      ref={sectionRef}
      className="py-28 lg:py-40 bg-[#FAFDFB] text-slate-900 border-b border-slate-200/80 relative noise-overlay"
    >
      {/* Ambient background light orbs */}
      <div className="absolute top-1/4 left-[-5%] w-[550px] h-[550px] bg-emerald-200/20 rounded-full blur-3xl pointer-events-none orb-1" />
      <div className="absolute bottom-1/4 right-[-5%] w-[550px] h-[550px] bg-orange-200/20 rounded-full blur-3xl pointer-events-none orb-2" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header Block with Scroll Reveal */}
        <div className="max-w-3xl scroll-reveal">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-mono font-bold tracking-wider uppercase mb-5 premium-pill">
            SECTION 03 // AUDIENCE & STAKEHOLDERS
          </div>
          <h2 className="text-3xl sm:text-5xl font-black tracking-[-0.035em] text-slate-950 leading-[1.12] font-display text-balance">
            Built for the teams responsible for{" "}
            <span className="gradient-text-emerald-orange">
              making AI work in the real world.
            </span>
          </h2>
          <p className="mt-5 text-slate-600 text-base sm:text-lg leading-relaxed font-normal text-pretty">
            Organizations need more than model access. They need structured tooling that empowers
            engineers to experiment rapidly while providing platform and governance teams with
            absolute operational control.
          </p>
        </div>

        {/* 4 Audience Cards with Staggered Scroll Reveal */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-2 gap-8">
          {audiences.map((aud, idx) => {
            const Icon = aud.icon;
            const isOrange = aud.theme === "orange";
            const delay = `${0.1 + idx * 0.1}s`;

            return (
              <div
                key={aud.id}
                className="p-7 sm:p-9 rounded-3xl bg-white border border-slate-200/80 shadow-sm hover:shadow-2xl transition-all duration-300 flex flex-col justify-between scroll-reveal group relative overflow-hidden"
                style={{ "--reveal-delay": delay } as React.CSSProperties}
              >
                {/* Subtle top indicator bar */}
                <div
                  className={`absolute top-0 left-0 right-0 h-1 transition-all ${
                    isOrange ? "bg-orange-400 group-hover:h-1.5" : "bg-emerald-500 group-hover:h-1.5"
                  }`}
                />

                <div className="space-y-4">
                  <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                    <div className="flex items-center gap-3.5">
                      <div
                        className={`w-12 h-12 rounded-2xl flex items-center justify-center border transition-colors ${
                          isOrange
                            ? "bg-orange-50 border-orange-200 text-orange-600 group-hover:bg-orange-600 group-hover:text-white"
                            : "bg-emerald-50 border-emerald-200 text-emerald-600 group-hover:bg-emerald-600 group-hover:text-white"
                        }`}
                      >
                        <Icon size={22} />
                      </div>
                      <div>
                        <span
                          className={`text-[10px] font-mono font-bold tracking-wider block ${
                            isOrange ? "text-orange-700" : "text-emerald-700"
                          }`}
                        >
                          {aud.role}
                        </span>
                        <h3 className="text-lg font-bold text-slate-950 tracking-tight font-display">
                          {aud.title}
                        </h3>
                      </div>
                    </div>
                  </div>

                  <p className="text-sm text-slate-600 leading-relaxed font-normal">
                    {aud.description}
                  </p>

                  <div className="p-4 rounded-2xl bg-slate-50/80 border border-slate-200/70 text-xs space-y-2 font-mono">
                    <div className="text-slate-600">
                      <strong className="text-rose-600 font-bold">Daily Friction:</strong> {aud.challenge}
                    </div>
                    <div className="text-slate-800">
                      <strong
                        className={
                          isOrange ? "text-orange-700 font-bold" : "text-emerald-700 font-bold"
                        }
                      >
                        Mizan Standard:
                      </strong>{" "}
                      {aud.solution}
                    </div>
                  </div>

                  <ul className="pt-2 space-y-2.5">
                    {aud.capabilities.map((cap, i) => (
                      <li key={i} className="text-xs text-slate-700 flex items-center gap-2.5 font-medium">
                        <CheckCircle2
                          size={14}
                          className={
                            isOrange
                              ? "text-orange-600 shrink-0"
                              : "text-emerald-600 shrink-0"
                          }
                        />
                        <span>{cap}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          })}
        </div>

        {/* Closing Statement with Scroll Reveal */}
        <div
          className="mt-16 p-8 sm:p-10 rounded-3xl bg-white border border-slate-200/80 text-center max-w-4xl mx-auto shadow-xl scroll-reveal relative overflow-hidden"
          style={{ "--reveal-delay": "0.3s" } as React.CSSProperties}
        >
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-teal-400 to-orange-500" />
          <p className="text-base sm:text-lg font-semibold text-slate-800 leading-relaxed font-display">
            Whether you are evaluating your first AI implementation or managing multiple AI systems,
            Mizan provides a structured foundation for making AI development more accountable and
            operationally manageable.
          </p>
        </div>
      </div>
    </section>
  );
}
