import { Link } from "react-router-dom";
import { ArrowRight, Shield, CheckCircle2, Lock } from "lucide-react";
import { useScrollReveal } from "../hooks/useScrollReveal";

interface CtaSectionProps {
  onOpenPilot: () => void;
}

export function CtaSection({ onOpenPilot }: CtaSectionProps) {
  const sectionRef = useScrollReveal();

  return (
    <section
      ref={sectionRef}
      className="py-28 lg:py-40 bg-white text-slate-900 relative overflow-hidden border-b border-slate-200/80 noise-overlay"
    >
      {/* Living background orbs and gradient mesh */}
      <div className="absolute top-1/2 left-1/3 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-emerald-100/40 rounded-full blur-3xl pointer-events-none orb-1" />
      <div className="absolute top-1/2 right-1/4 w-[500px] h-[350px] bg-orange-100/35 rounded-full blur-3xl pointer-events-none orb-2" />
      <div className="absolute inset-0 gradient-mesh-bg pointer-events-none opacity-40" />

      <div className="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="p-8 sm:p-14 lg:p-16 rounded-3xl bg-gradient-to-b from-white via-white to-emerald-50/20 border-2 border-emerald-500/20 shadow-2xl workbench-frame text-center space-y-8 relative overflow-hidden scroll-reveal">
          {/* Subtle animated top accent ribbon */}
          <div className="absolute top-0 left-0 right-0 h-1.5 animated-border" />

          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-mono font-semibold uppercase tracking-wider premium-pill">
            <Shield size={13} className="text-emerald-700" />
            READY FOR CONTROLLED ENTERPRISE DEPLOYMENT
          </div>

          <h2 className="text-3xl sm:text-5xl lg:text-6xl font-black tracking-[-0.035em] text-slate-950 leading-[1.12] font-display text-balance">
            Move from AI experimentation to{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 via-teal-600 to-orange-500">
              controlled implementation.
            </span>
          </h2>

          <p className="text-base sm:text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed font-normal text-pretty">
            Build a clearer path from your AI ideas to evaluated, governed and operational systems.
            Discover how Mizan can bring structure, visibility and accountability to your AI lifecycle.
          </p>

          {/* Action CTAs */}
          <div className="pt-4 flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/register"
              className="btn-emerald-luxury px-8 py-4 rounded-xl text-white font-display font-bold text-sm flex items-center gap-2 group cursor-pointer"
            >
              Explore Mizan
              <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </Link>

            <button
              type="button"
              onClick={onOpenPilot}
              className="btn-orange-luxury px-8 py-4 rounded-xl text-white font-display font-bold text-sm flex items-center gap-2 cursor-pointer"
            >
              <Shield size={16} className="text-white" />
              Request a Pilot
            </button>
          </div>

          {/* Existing account prompt */}
          <div className="pt-2 text-xs text-slate-500 flex items-center justify-center gap-2 sm:gap-3 flex-wrap">
            <span>Already registered with Mizan?</span>
            <Link
              to="/login"
              className="text-emerald-700 hover:text-emerald-900 font-bold underline underline-offset-4"
            >
              Sign In to your workspace console
            </Link>
          </div>

          {/* Assurance badges */}
          <div className="pt-10 border-t border-slate-200/80 flex flex-wrap items-center justify-center gap-8 text-xs font-mono text-slate-600">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={14} className="text-emerald-600" />
              <span>Deterministic Benchmark Evaluations</span>
            </div>
            <div className="flex items-center gap-2">
              <Lock size={14} className="text-orange-600" />
              <span>Ed25519 Cryptographic Provenance</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 size={14} className="text-emerald-600" />
              <span>Customer-Local Private Runtimes</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
