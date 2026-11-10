import { useState } from "react";
import {
  Database,
  Award,
  Cpu,
  Hammer,
  Archive,
  Boxes,
  Server,
  Activity,
  CheckCircle2,
  Lock,
  ChevronRight,
} from "lucide-react";
import type { PlatformCapability } from "../types";
import { useScrollReveal } from "../hooks/useScrollReveal";

export function PlatformSection() {
  const [selectedId, setSelectedId] = useState<string>("data-protection");
  const sectionRef = useScrollReveal();

  const capabilities: (PlatformCapability & {
    icon: typeof Database;
    technicalArtifact: string;
    theme: "emerald" | "orange";
  })[] = [
    {
      id: "data-protection",
      number: "01",
      title: "Data Protection & Preparation",
      summary:
        "Prepare datasets for AI workflows with document ingestion, dataset versioning, sensitive-data detection, masking and controlled approval processes.",
      details: [
        "Document ingestion with text extraction and metadata chunking",
        "Automated PII/PHI detection across enterprise files",
        "Configurable masking policies (redact, hash, synthetic replace)",
        "Gate 1 human sign-off before training or evaluation inclusion",
      ],
      badge: "Gate 1 Protected",
      icon: Database,
      technicalArtifact: "dataset_manifest_v2.json (Gate 1 Signed)",
      theme: "emerald",
    },
    {
      id: "evaluation",
      number: "02",
      title: "AI Evaluation & Experimentation",
      summary:
        "Create structured evaluation suites, examine model responses, compare experiments and understand performance through measurable evaluation criteria.",
      details: [
        "Multi-engine deterministic scoring (exact, semantic, regex, custom)",
        "Repeatable test matrices and parameter sweeps",
        "Side-by-side run comparisons with differential metric breakdowns",
        "Threshold-gated pass/fail quality criteria",
      ],
      badge: "Deterministic",
      icon: Award,
      technicalArtifact: "eval_scorecard_matrix_run841.json",
      theme: "emerald",
    },
    {
      id: "resource-intelligence",
      number: "03",
      title: "Resource Intelligence & Optimization",
      summary:
        "Assess hardware compatibility, memory requirements, inference constraints and resource estimates before committing to an implementation. Compare eligible candidates through explainable recommendations and evidence-based trade-offs.",
      details: [
        "Deterministic VRAM memory calculators for fp16, 8-bit, and 4-bit formats",
        "Compute cost and latency feasibility preflights",
        "Weighted multi-objective ranking of candidate models",
        "Gate 2 budget and hardware allocation sign-offs",
      ],
      badge: "Gate 2 Budgeted",
      icon: Cpu,
      technicalArtifact: "hardware_feasibility_preflight.json",
      theme: "orange",
    },
    {
      id: "model-building",
      number: "04",
      title: "Model Building & Development",
      summary:
        "Manage model-building workflows, supported fine-tuning recipes, quantization processes, checkpoint artifacts and reproducible build configurations.",
      details: [
        "Parameter-efficient LoRA / QLoRA adaptation pipelines",
        "Automated quantization (GGUF, AWQ, GPTQ) for target hardware",
        "Checkpoint lineage with verifiable configuration manifests",
        "Reproducible build environments and logs",
      ],
      badge: "Reproducible",
      icon: Hammer,
      technicalArtifact: "build_recipe_lora_rank16.yaml",
      theme: "emerald",
    },
    {
      id: "artifact-governance",
      number: "05",
      title: "Artifact Governance & Release Management",
      summary:
        "Maintain model provenance, verify artifacts, track release manifests and enforce human approval before controlled release.",
      details: [
        "Ed25519 cryptographic signing of model binaries and configs",
        "Immutable parent-child lineage linking datasets to checkpoints",
        "Release manifest authorization and approval signatures",
        "Gate 3 verified sign-off prior to catalog listing",
      ],
      badge: "Gate 3 Certified",
      icon: Archive,
      technicalArtifact: "release_manifest_ed25519.sig",
      theme: "emerald",
    },
    {
      id: "discovery",
      number: "06",
      title: "Model & Application Discovery",
      summary:
        "Organize approved model and application listings with version information, compatibility evidence and publication controls.",
      details: [
        "Internal organization Model Zoo with permissioned access",
        "Application Zoo for packaged customer runtime services",
        "Hardware compatibility tags and memory requirements",
        "Explicit publication and deprecation lifecycle controls",
      ],
      badge: "Model Zoo",
      icon: Boxes,
      technicalArtifact: "catalog_listing_meta.json",
      theme: "orange",
    },
    {
      id: "runtime-deployment",
      number: "07",
      title: "Customer Runtime & Deployment",
      summary:
        "Manage customer runtime applications, deployment packages, local execution environments, blue/green slots and controlled activation workflows.",
      details: [
        "Customer-local runtime daemon for private on-prem or VPC nodes",
        "Zero payload egress: inference data remains within customer boundary",
        "Blue/green slot management with instant traffic switching",
        "Offline-capable execution with local cache verification",
      ],
      badge: "Private Runtime",
      icon: Server,
      technicalArtifact: "daemon_runtime_config.yaml",
      theme: "emerald",
    },
    {
      id: "monitoring-operations",
      number: "08",
      title: "Monitoring & Operations",
      summary:
        "Observe operational metrics, service-level objectives, alerts, incidents and rollback activity through a structured operations environment.",
      details: [
        "Real-time latency, throughput, and error-budget tracking",
        "SLO breach notifications and automated threshold alerts",
        "Single-click rollback to previously signed artifact versions",
        "Privacy-preserving operational telemetry without payload leakage",
      ],
      badge: "Live Telemetry",
      icon: Activity,
      technicalArtifact: "slo_telemetry_stream.metrics",
      theme: "orange",
    },
  ];

  const currentCap = capabilities.find((c) => c.id === selectedId) || capabilities[0];
  const CurrentIcon = currentCap.icon;
  const isCurrentOrange = currentCap.theme === "orange";

  return (
    <section
      id="platform"
      ref={sectionRef}
      className="py-28 lg:py-40 bg-white text-slate-900 border-b border-slate-200/80 relative noise-overlay"
    >
      {/* Background ambient lighting */}
      <div className="absolute top-1/3 left-1/4 w-[600px] h-[400px] bg-emerald-100/30 rounded-full blur-3xl pointer-events-none orb-1" />
      <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[350px] bg-orange-100/25 rounded-full blur-3xl pointer-events-none orb-2" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header Block with Scroll Reveal */}
        <div className="max-w-3xl scroll-reveal">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-mono font-bold tracking-wider uppercase mb-5 premium-pill">
            SECTION 02 // PLATFORM CAPABILITIES
          </div>
          <h2 className="text-3xl sm:text-5xl font-black tracking-[-0.035em] text-slate-950 leading-[1.12] font-display text-balance">
            One platform.{" "}
            <span className="gradient-text-emerald-orange">
              A more structured AI lifecycle.
            </span>
          </h2>
          <p className="mt-5 text-slate-600 text-base sm:text-lg leading-relaxed font-normal text-pretty">
            Mizan is an enterprise platform that helps teams manage the journey from data preparation
            and AI experimentation to model governance, release management and runtime operations.
            It brings the critical workflows together while preserving visibility into decisions,
            approvals, artifacts and operational status.
          </p>
        </div>

        {/* Master Interactive Workbench / Inspector */}
        <div className="mt-16 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Navigation Rail (8 Capabilities) */}
          <div className="lg:col-span-5 space-y-2.5 scroll-reveal" style={{ "--reveal-delay": "0.1s" } as React.CSSProperties}>
            {capabilities.map((cap) => {
              const Icon = cap.icon;
              const isSelected = cap.id === selectedId;
              const isOrange = cap.theme === "orange";
              return (
                <button
                  key={cap.id}
                  type="button"
                  onClick={() => setSelectedId(cap.id)}
                  className={`w-full p-4 rounded-2xl text-left transition-all flex items-center justify-between border cursor-pointer ${
                    isSelected
                      ? isOrange
                        ? "bg-orange-50/90 border-orange-400 shadow-md text-orange-950 font-bold"
                        : "bg-emerald-50/90 border-emerald-400 shadow-md text-emerald-950 font-bold"
                      : "bg-white/80 backdrop-blur-sm border-slate-200/80 text-slate-700 hover:text-slate-900 hover:bg-slate-50 hover:border-slate-300 shadow-xs"
                  }`}
                >
                  <div className="flex items-center gap-3.5">
                    <span
                      className={`text-xs font-mono font-bold px-2 py-0.5 rounded-lg ${
                        isSelected
                          ? isOrange
                            ? "bg-orange-200/80 text-orange-900"
                            : "bg-emerald-200/80 text-emerald-900"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {cap.number}
                    </span>
                    <Icon
                      size={18}
                      className={
                        isSelected
                          ? isOrange
                            ? "text-orange-600"
                            : "text-emerald-600"
                          : "text-slate-400"
                      }
                    />
                    <span className="text-sm tracking-tight font-display">{cap.title}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded-full hidden sm:inline-block font-semibold ${
                        isOrange
                          ? "bg-orange-100/70 text-orange-800 border border-orange-200"
                          : "bg-emerald-100/70 text-emerald-800 border border-emerald-200"
                      }`}
                    >
                      {cap.badge}
                    </span>
                    <ChevronRight
                      size={15}
                      className={
                        isSelected
                          ? isOrange
                            ? "text-orange-600 translate-x-0.5 transition-transform"
                            : "text-emerald-600 translate-x-0.5 transition-transform"
                          : "text-slate-400"
                      }
                    />
                  </div>
                </button>
              );
            })}
          </div>

          {/* Right Active Capability Inspector */}
          <div
            className="lg:col-span-7 p-7 sm:p-9 rounded-3xl bg-white border border-slate-200/80 shadow-2xl workbench-frame scroll-reveal relative overflow-hidden"
            style={{ "--reveal-delay": "0.2s" } as React.CSSProperties}
          >
            {/* Top accent line */}
            <div
              className={`absolute top-0 left-0 right-0 h-1 ${
                isCurrentOrange
                  ? "bg-gradient-to-r from-orange-400 to-amber-500"
                  : "bg-gradient-to-r from-emerald-500 to-teal-400"
              }`}
            />

            <div className="flex items-center justify-between pb-5 border-b border-slate-100">
              <div className="flex items-center gap-3.5">
                <div
                  className={`w-12 h-12 rounded-2xl flex items-center justify-center border transition-colors ${
                    isCurrentOrange
                      ? "bg-orange-50 border-orange-200 text-orange-600"
                      : "bg-emerald-50 border-emerald-200 text-emerald-600"
                  }`}
                >
                  <CurrentIcon size={24} />
                </div>
                <div>
                  <span
                    className={`text-[10px] font-mono uppercase tracking-widest block font-bold ${
                      isCurrentOrange ? "text-orange-700" : "text-emerald-700"
                    }`}
                  >
                    CAPABILITY {currentCap.number} // WORKSPACE INSPECTOR
                  </span>
                  <h3 className="text-xl sm:text-2xl font-black text-slate-950 tracking-tight font-display">
                    {currentCap.title}
                  </h3>
                </div>
              </div>

              <span
                className={`px-3 py-1 rounded-full text-xs font-mono font-bold border ${
                  isCurrentOrange
                    ? "bg-orange-50 text-orange-800 border-orange-200"
                    : "bg-emerald-50 text-emerald-800 border border-emerald-200"
                }`}
              >
                {currentCap.badge}
              </span>
            </div>

            <div className="mt-7 space-y-6">
              <div>
                <h4 className="text-xs font-mono uppercase text-slate-400 mb-2 font-bold tracking-wider">
                  Purpose & Core Value
                </h4>
                <p className="text-sm sm:text-base text-slate-700 leading-relaxed font-normal">
                  {currentCap.summary}
                </p>
              </div>

              {/* Technical Execution Points */}
              <div>
                <h4 className="text-xs font-mono uppercase text-slate-400 mb-3 font-bold tracking-wider">
                  Engineered Capabilities
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {currentCap.details.map((item, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-2xl bg-slate-50/80 border border-slate-200/70 text-xs text-slate-700 flex items-start gap-2.5 font-medium shadow-xs"
                    >
                      <CheckCircle2
                        size={15}
                        className={`shrink-0 mt-0.5 ${
                          isCurrentOrange ? "text-orange-600" : "text-emerald-600"
                        }`}
                      />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Verifiable Artifact Badge */}
              <div className="p-4 rounded-2xl bg-slate-950 text-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs font-mono shadow-inner border border-slate-800">
                <div className="flex items-center gap-2">
                  <Lock size={14} className={isCurrentOrange ? "text-orange-400" : "text-emerald-400"} />
                  <span>
                    Governed Output: <strong className="text-white">{currentCap.technicalArtifact}</strong>
                  </span>
                </div>
                <span
                  className={`text-[11px] px-2.5 py-0.5 rounded-full font-bold ${
                    isCurrentOrange
                      ? "bg-orange-950/80 text-orange-300 border border-orange-700/80"
                      : "bg-emerald-950/80 text-emerald-300 border border-emerald-700/80"
                  }`}
                >
                  Traceability Hash Verified
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
