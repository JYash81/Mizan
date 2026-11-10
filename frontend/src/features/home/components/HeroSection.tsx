import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Shield,
  CheckCircle2,
  Lock,
  Cpu,
  Activity,
  Database,
  KeyRound,
  FileCheck2,
  SlidersHorizontal,
  RotateCcw,
  Sparkles,
} from "lucide-react";

interface HeroSectionProps {
  onOpenPilot: () => void;
}

export function HeroSection({ onOpenPilot }: HeroSectionProps) {
  const [activeTab, setActiveTab] = useState<"gate1" | "gate2" | "gate3" | "runtime">("gate1");
  const [showMasked, setShowMasked] = useState(true);

  const scrollTo = (href: string) => {
    const el = document.querySelector(href);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section className="relative overflow-hidden bg-white text-slate-900 pt-8 sm:pt-12 lg:pt-14 pb-24 lg:pb-36 noise-overlay">
      {/* Precision Micro-Dot Matrix Layer */}
      <div
        className="absolute inset-0 pointer-events-none opacity-40"
        style={{
          backgroundImage: "radial-gradient(#059669 0.75px, transparent 0.75px), radial-gradient(#F97316 0.75px, transparent 0.75px)",
          backgroundSize: "32px 32px",
          backgroundPosition: "0 0, 16px 16px",
          maskImage: "radial-gradient(ellipse 70% 60% at 50% 35%, black 20%, transparent 80%)",
          WebkitMaskImage: "radial-gradient(ellipse 70% 60% at 50% 35%, black 20%, transparent 80%)",
        }}
      />

      {/* Living diffused atmospheric ambient light orbs */}
      <div className="absolute top-[-10%] left-[12%] w-[650px] h-[500px] bg-gradient-to-br from-emerald-200/35 via-teal-100/20 to-transparent rounded-full blur-[110px] pointer-events-none orb-1" />
      <div className="absolute top-[-5%] right-[10%] w-[600px] h-[450px] bg-gradient-to-bl from-orange-200/25 via-amber-100/15 to-transparent rounded-full blur-[110px] pointer-events-none orb-2" />
      <div className="absolute bottom-[-10%] left-[38%] w-[520px] h-[380px] bg-gradient-to-t from-emerald-100/20 via-cyan-50/10 to-transparent rounded-full blur-[100px] pointer-events-none orb-3" />
      <div className="absolute inset-0 gradient-mesh-bg pointer-events-none opacity-70" />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Top Hero Text */}
        <div className="text-center max-w-5xl mx-auto flex flex-col items-center space-y-5 sm:space-y-6">
          {/* Eyebrow badge */}
          <div
            className="hero-fade-up inline-flex items-center gap-2 sm:gap-2.5 px-3.5 sm:px-4 py-1.5 rounded-full bg-white/90 backdrop-blur-md border border-slate-200/90 text-slate-800 text-[11px] sm:text-xs font-mono font-bold tracking-wider uppercase shadow-[0_2px_8px_rgba(0,0,0,0.03)]"
            style={{ animationDelay: '0s' }}
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="text-emerald-800">ENTERPRISE AI LIFECYCLE</span>
            <span className="text-orange-500 font-extrabold">&</span>
            <span className="text-orange-700">GOVERNANCE PLATFORM</span>
            <span className="inline-block w-px h-3 bg-slate-200 mx-0.5" />
            <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 text-[10px] font-bold border border-emerald-200/70">
              V1.4 CONTROL PLANE
            </span>
          </div>

          {/* Main Headline */}
          <h1 className="font-display tracking-[-0.03em] text-slate-950 w-full text-center">
            <span className="hero-text-line block text-3xl sm:text-5xl lg:text-[3.35rem] xl:text-[3.85rem] font-extrabold leading-[1.14] text-slate-950 sm:whitespace-nowrap">
              Build AI with evidence.
            </span>
            <span className="hero-text-line block text-3xl sm:text-5xl lg:text-[3.35rem] xl:text-[3.85rem] font-extrabold leading-[1.14] gradient-text-emerald sm:whitespace-nowrap">
              Govern it with control.
            </span>
            <span className="hero-text-line block text-3xl sm:text-5xl lg:text-[3.35rem] xl:text-[3.85rem] font-extrabold leading-[1.14] gradient-text-orange sm:whitespace-nowrap">
              Deploy it with confidence.
            </span>
          </h1>

          {/* Supporting Description */}
          <p
            className="hero-fade-up text-base sm:text-lg lg:text-[1.125rem] text-slate-600 font-normal leading-[1.65] max-w-2xl sm:max-w-3xl mx-auto text-pretty"
            style={{ animationDelay: '0.45s' }}
          >
            Mizan brings AI experimentation, evaluation, optimization, governance and runtime operations
            into one structured platform—helping organizations make better AI decisions with measurable
            evidence and traceable control.
          </p>

          {/* Architectural positioning callout with warm orange badge */}
          <div
            className="hero-fade-up inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-orange-50/70 backdrop-blur-xs border border-orange-200/80 text-[11px] sm:text-xs font-medium text-orange-950 shadow-xs max-w-xl mx-auto text-center justify-center text-pretty"
            style={{ animationDelay: '0.6s' }}
          >
            <Shield size={13} className="text-orange-600 shrink-0" />
            <span className="leading-snug">
              Engineered as an enterprise AI lifecycle and infrastructure platform—not a conversational assistant or chatbot wrapper.
            </span>
          </div>

          {/* Action CTAs */}
          <div
            className="hero-fade-up pt-1 sm:pt-2 flex flex-wrap items-center justify-center gap-3 sm:gap-4"
            style={{ animationDelay: '0.75s' }}
          >
            <button
              type="button"
              onClick={() => scrollTo("#platform")}
              className="btn-emerald-luxury h-12 px-7 rounded-xl text-white font-display font-semibold text-sm flex items-center gap-2 group cursor-pointer transition-all shadow-[0_4px_16px_rgba(5,150,105,0.25)] hover:shadow-[0_6px_24px_rgba(5,150,105,0.35)]"
            >
              <span>Explore the Platform</span>
              <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </button>

            <button
              type="button"
              onClick={() => scrollTo("#how-it-works")}
              className="btn-white-luxury h-12 px-6 rounded-xl font-display font-semibold text-sm text-slate-800 hover:text-emerald-800 bg-white border border-slate-200/90 hover:border-emerald-300 flex items-center gap-2 cursor-pointer shadow-[0_2px_8px_rgba(0,0,0,0.04)] hover:shadow-[0_4px_16px_rgba(0,0,0,0.08)] transition-all"
            >
              Discover How Mizan Works
            </button>

            <button
              type="button"
              onClick={onOpenPilot}
              className="btn-orange-luxury h-12 px-6 rounded-xl text-white font-display font-semibold text-sm flex items-center gap-2 cursor-pointer transition-all shadow-[0_4px_16px_rgba(234,88,12,0.25)] hover:shadow-[0_6px_24px_rgba(234,88,12,0.35)]"
            >
              <Shield size={15} className="text-white" />
              <span>Request a Pilot</span>
            </button>
          </div>

          {/* Sign In & Sign Up Options */}
          <div
            className="hero-fade-up pt-1 text-xs text-slate-500 flex items-center justify-center gap-2 flex-wrap font-medium"
            style={{ animationDelay: '0.9s' }}
          >
            <span>Ready to get started?</span>
            <Link
              to="/register"
              className="text-emerald-700 hover:text-emerald-800 font-bold underline underline-offset-4 decoration-emerald-300 hover:decoration-emerald-600 transition-colors"
            >
              Create an organization account
            </Link>
            <span className="text-slate-300">•</span>
            <span>Already registered?</span>
            <Link
              to="/login"
              className="text-orange-700 hover:text-orange-800 font-bold underline underline-offset-4 decoration-orange-300 hover:decoration-orange-600 transition-colors"
            >
              Sign In to workspace
            </Link>
          </div>
        </div>

        {/* Handcrafted Interactive Platform Workbench in Premium White */}
        <div
          className="hero-fade-up mt-12 sm:mt-14 max-w-5xl mx-auto workbench-frame bg-white border border-slate-200/80 rounded-2xl overflow-hidden relative shadow-[0_20px_60px_-15px_rgba(0,0,0,0.08)]"
          style={{ animationDelay: '1.05s' }}
        >
          {/* Animated top border accent */}
          <div className="absolute top-0 left-0 right-0 h-[2px] animated-border" />
          {/* Top Titlebar */}
          <div className="px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-400" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span className="ml-3 font-mono text-xs text-slate-600 font-medium">
                mizan-workbench://interactive-lifecycle-inspector
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
              <span className="text-[11px] font-mono text-emerald-800 font-bold tracking-wide">
                GOVERNED PIPELINE ACTIVE
              </span>
            </div>
          </div>

          {/* Interactive Navigation Tabs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 border-b border-slate-200 bg-slate-50/50">
            <button
              type="button"
              onClick={() => setActiveTab("gate1")}
              className={`p-3.5 text-left text-xs font-medium transition-all border-r border-slate-200 last:border-r-0 cursor-pointer flex items-center gap-2.5 ${
                activeTab === "gate1"
                  ? "bg-white text-emerald-950 border-b-2 border-b-emerald-600 shadow-sm"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/60"
              }`}
            >
              <Database size={16} className={activeTab === "gate1" ? "text-emerald-600" : "text-slate-400"} />
              <div>
                <span className="block text-[10px] font-mono text-emerald-700 font-bold uppercase">GATE 01</span>
                <strong className="block text-xs font-bold text-slate-900">Data Protection</strong>
              </div>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("gate2")}
              className={`p-3.5 text-left text-xs font-medium transition-all border-r border-slate-200 last:border-r-0 cursor-pointer flex items-center gap-2.5 ${
                activeTab === "gate2"
                  ? "bg-white text-orange-950 border-b-2 border-b-orange-600 shadow-sm"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/60"
              }`}
            >
              <Cpu size={16} className={activeTab === "gate2" ? "text-orange-600" : "text-slate-400"} />
              <div>
                <span className="block text-[10px] font-mono text-orange-700 font-bold uppercase">GATE 02</span>
                <strong className="block text-xs font-bold text-slate-900">Hardware Intel</strong>
              </div>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("gate3")}
              className={`p-3.5 text-left text-xs font-medium transition-all border-r border-slate-200 last:border-r-0 cursor-pointer flex items-center gap-2.5 ${
                activeTab === "gate3"
                  ? "bg-white text-emerald-950 border-b-2 border-b-emerald-600 shadow-sm"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/60"
              }`}
            >
              <Lock size={16} className={activeTab === "gate3" ? "text-emerald-600" : "text-slate-400"} />
              <div>
                <span className="block text-[10px] font-mono text-emerald-700 font-bold uppercase">GATE 03</span>
                <strong className="block text-xs font-bold text-slate-900">Artifact Release</strong>
              </div>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("runtime")}
              className={`p-3.5 text-left text-xs font-medium transition-all cursor-pointer flex items-center gap-2.5 ${
                activeTab === "runtime"
                  ? "bg-white text-orange-950 border-b-2 border-b-orange-600 shadow-sm"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/60"
              }`}
            >
              <Activity size={16} className={activeTab === "runtime" ? "text-orange-600" : "text-slate-400"} />
              <div>
                <span className="block text-[10px] font-mono text-orange-700 font-bold uppercase">OPERATE</span>
                <strong className="block text-xs font-bold text-slate-900">Customer Runtime</strong>
              </div>
            </button>
          </div>

          {/* Workbench Screen Content */}
          <div className="p-6 lg:p-8 bg-white">
            {activeTab === "gate1" && (
              <div className="space-y-5 animate-in fade-in duration-200">
                <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200">
                  <div className="flex items-center gap-2.5">
                    <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                      SCAN COMPLETED · 100% AUDITED
                    </span>
                    <span className="text-xs text-slate-600 font-mono font-medium">
                      dataset_corpus_clinical_v2.jsonl (4.2 MB)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowMasked(!showMasked)}
                    className="text-xs font-mono font-semibold text-emerald-700 hover:text-emerald-900 underline underline-offset-4 flex items-center gap-1.5 cursor-pointer"
                  >
                    <SlidersHorizontal size={13} />
                    Toggle: {showMasked ? "Viewing Sanitized Text" : "Viewing Raw Payload"}
                  </button>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 text-slate-100 font-mono text-xs leading-relaxed shadow-inner">
                  {showMasked ? (
                    <div className="space-y-2">
                      <p>
                        {"{"} "patient_id": "PT-90412", "physician": <span className="bg-emerald-800 text-emerald-100 px-1.5 py-0.5 rounded font-bold">[MASK_NAME: DR_CLINICIAN_04]</span>,
                      </p>
                      <p>
                        &nbsp;&nbsp;"diagnosis": "Acute Type-II Cardiovascular Hypertension",
                      </p>
                      <p>
                        &nbsp;&nbsp;"tax_id": <span className="bg-emerald-800 text-emerald-100 px-1.5 py-0.5 rounded font-bold">[REDACTED_SSN: ***-**-9104]</span>,
                      </p>
                      <p>
                        &nbsp;&nbsp;"gate1_compliance": <span className="text-emerald-400 font-bold">"APPROVED_BY_COMPLIANCE_OFFICER"</span> {"}"}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2 text-rose-200">
                      <p>
                        {"{"} "patient_id": "PT-90412", "physician": "Dr. Arthur Pendelton",
                      </p>
                      <p>
                        &nbsp;&nbsp;"diagnosis": "Acute Type-II Cardiovascular Hypertension",
                      </p>
                      <p>
                        &nbsp;&nbsp;"tax_id": "492-10-9104",  <span className="text-orange-400 font-bold">// CRITICAL: UNMASKED PII DETECTED</span>
                      </p>
                      <p>
                        &nbsp;&nbsp;"gate1_compliance": <span className="text-amber-400">"PENDING_MASKING_APPROVAL"</span> {"}"}
                      </p>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                    <span className="text-slate-500 block text-[10px] font-mono font-semibold uppercase">PII ENTITIES IDENTIFIED</span>
                    <strong className="text-slate-900 text-sm">34 Individuals / 12 SSNs</strong>
                  </div>
                  <div className="p-3.5 rounded-xl bg-emerald-50/60 border border-emerald-200 text-xs">
                    <span className="text-emerald-700 block text-[10px] font-mono font-semibold uppercase">MASKING PROTOCOL</span>
                    <strong className="text-emerald-900 text-sm font-bold">Deterministic Hashing</strong>
                  </div>
                  <div className="p-3.5 rounded-xl bg-orange-50/60 border border-orange-200 text-xs">
                    <span className="text-orange-700 block text-[10px] font-mono font-semibold uppercase">GATE 1 HUMAN REVIEW</span>
                    <strong className="text-orange-950 text-sm font-bold flex items-center gap-1.5">
                      <CheckCircle2 size={14} className="text-emerald-600" /> Signed by Data Officer
                    </strong>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "gate2" && (
              <div className="space-y-5 animate-in fade-in duration-200">
                <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200">
                  <div className="flex items-center gap-2.5">
                    <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-orange-50 text-orange-800 border border-orange-200">
                      GATE 2 PREFLIGHT FEASIBLE
                    </span>
                    <span className="text-xs text-slate-600 font-mono font-medium">
                      Target GPU: NVIDIA RTX 4090 / A10G (24 GB VRAM)
                    </span>
                  </div>
                  <span className="text-xs font-mono font-semibold text-slate-700">
                    Candidate: Llama-3.3-70B-Instruct (4-Bit AWQ)
                  </span>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-700">VRAM Budget Allocation:</span>
                    <span className="font-mono text-emerald-700 font-bold">18.4 GB / 24.0 GB (76.6% Allocated)</span>
                  </div>
                  <div className="w-full h-3.5 rounded-full bg-slate-100 border border-slate-200 overflow-hidden flex shadow-inner">
                    <div style={{ width: "55%" }} className="bg-emerald-600 h-full" title="Weights: 13.2 GB" />
                    <div style={{ width: "16%" }} className="bg-orange-500 h-full" title="KV Cache: 3.8 GB" />
                    <div style={{ width: "6%" }} className="bg-amber-400 h-full" title="CUDA Overhead: 1.4 GB" />
                  </div>
                  <div className="flex flex-wrap items-center gap-4 text-[11px] font-mono font-medium text-slate-600">
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-emerald-600" /> Weights: 13.2 GB</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-orange-500" /> KV Cache: 3.8 GB</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-amber-400" /> CUDA Runtime: 1.4 GB</span>
                    <span className="text-emerald-700 font-bold ml-auto">Free Headroom: 5.6 GB</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                    <span className="text-slate-500 block text-[10px] font-mono font-semibold uppercase">ESTIMATED THROUGHPUT</span>
                    <strong className="text-slate-900 text-sm">62 tok/sec (Batch Size 4)</strong>
                  </div>
                  <div className="p-3.5 rounded-xl bg-orange-50/70 border border-orange-200 text-xs">
                    <span className="text-orange-700 block text-[10px] font-mono font-semibold uppercase">HOURLY INFERENCE BUDGET</span>
                    <strong className="text-orange-950 text-sm font-bold">$0.74 / Hour Active</strong>
                  </div>
                  <div className="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs">
                    <span className="text-emerald-700 block text-[10px] font-mono font-semibold uppercase">GATE 2 SPEND SIGN-OFF</span>
                    <strong className="text-emerald-950 text-sm font-bold flex items-center gap-1.5">
                      <CheckCircle2 size={14} className="text-emerald-600" /> Preflight Passed
                    </strong>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "gate3" && (
              <div className="space-y-5 animate-in fade-in duration-200">
                <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200">
                  <div className="flex items-center gap-2.5">
                    <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                      GATE 3 CRYPTOGRAPHICALLY SIGNED
                    </span>
                    <span className="text-xs text-slate-600 font-mono font-medium">
                      manifest://mizan-release-v1.4.0.json
                    </span>
                  </div>
                  <span className="text-xs font-mono text-orange-700 font-bold flex items-center gap-1.5">
                    <KeyRound size={14} /> Ed25519 Verified
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 text-slate-100 font-mono text-xs space-y-1.5 shadow-inner">
                  <p className="text-slate-400 font-semibold">// Immutable Cryptographic Provenance Manifest</p>
                  <p><span className="text-emerald-400">"release_id"</span>: "rel_981a44e2b0",</p>
                  <p><span className="text-emerald-400">"artifact_hash"</span>: "sha256:8f4c20d75b318e8f8101a91e5d799d82136e...",</p>
                  <p><span className="text-emerald-400">"dataset_parent"</span>: "ds_masked_clinical_v2#gate1_approved",</p>
                  <p><span className="text-emerald-400">"eval_suite_score"</span>: {"{"} "exact_match": 0.942, "latency_p95_ms": 138 {"}"},</p>
                  <p><span className="text-orange-400">"approver_identity"</span>: "secops_lead_ed25519:pk_89df210...",</p>
                  <p><span className="text-orange-400">"signature"</span>: "sig_ed25519:7bc341908ae31f0a82b49c..."</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                  <div className="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs">
                    <span className="text-emerald-700 block text-[10px] font-mono font-semibold uppercase">TAMPER-EVIDENT STATUS</span>
                    <strong className="text-emerald-950 text-sm font-bold">SHA-256 Intact</strong>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                    <span className="text-slate-600 block text-[10px] font-mono font-semibold uppercase">CATALOG ELIGIBILITY</span>
                    <strong className="text-slate-900 text-sm">Approved for Model Zoo</strong>
                  </div>
                  <div className="p-3.5 rounded-xl bg-orange-50/70 border border-orange-200 text-xs">
                    <span className="text-orange-700 block text-[10px] font-mono font-semibold uppercase">GATE 3 FORMAL SIGN-OFF</span>
                    <strong className="text-orange-950 text-sm font-bold flex items-center gap-1.5">
                      <FileCheck2 size={14} className="text-emerald-600" /> 2 of 2 Approvals Met
                    </strong>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "runtime" && (
              <div className="space-y-5 animate-in fade-in duration-200">
                <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200">
                  <div className="flex items-center gap-2.5">
                    <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-orange-50 text-orange-800 border border-orange-200">
                      DAEMON ACTIVE · BLUE/GREEN LIVE
                    </span>
                    <span className="text-xs text-slate-600 font-mono font-medium">
                      Site: Private-Cluster-OnPrem-01
                    </span>
                  </div>
                  <span className="text-xs font-mono text-orange-700 font-bold flex items-center gap-1.5">
                    <RotateCcw size={13} /> Instant Rollback Armed
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-1">
                    <span className="text-emerald-800 text-[10px] font-mono font-bold uppercase">SERVICE LEVEL OBJECTIVE</span>
                    <div className="text-2xl font-black text-emerald-950 font-mono">99.98%</div>
                    <span className="text-[11px] text-emerald-700 font-medium">Zero error budget breaches</span>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                    <span className="text-slate-500 text-[10px] font-mono font-bold uppercase">P95 INFERENCE LATENCY</span>
                    <div className="text-2xl font-black text-slate-900 font-mono">138 ms</div>
                    <span className="text-[11px] text-slate-600 font-medium">-24ms below target ceiling</span>
                  </div>

                  <div className="p-4 rounded-xl bg-orange-50/70 border border-orange-200 space-y-1">
                    <span className="text-orange-800 text-[10px] font-mono font-bold uppercase">BLUE / GREEN TRAFFIC</span>
                    <div className="text-2xl font-black text-orange-950 font-mono">90 / 10</div>
                    <span className="text-[11px] text-orange-700 font-medium">Slot A: Live · Slot B: Staging</span>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 flex items-center justify-between font-medium">
                  <div className="flex items-center gap-2">
                    <Sparkles size={14} className="text-orange-600" />
                    <span>Customer-Local Architecture: Payloads never leave your private environment.</span>
                  </div>
                  <span className="font-mono text-slate-500 text-[11px]">Control Plane Synchronized</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
