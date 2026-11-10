import { useState, type FormEvent } from "react";
import { X, CheckCircle2, Shield, Building2, Mail, User, Sparkles, Send } from "lucide-react";
import type { PilotRequest } from "../types";

interface PilotModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PilotModal({ isOpen, onClose }: PilotModalProps) {
  const [formData, setFormData] = useState<PilotRequest>({
    fullName: "",
    workEmail: "",
    organization: "",
    teamSize: "10-50",
    useCase: "Model Evaluation & Benchmarking",
    notes: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    // Simulate enterprise pilot provisioning dispatch
    setTimeout(() => {
      setIsSubmitting(false);
      setIsSuccess(true);
    }, 750);
  };

  const handleReset = () => {
    setIsSuccess(false);
    setFormData({
      fullName: "",
      workEmail: "",
      organization: "",
      teamSize: "10-50",
      useCase: "Model Evaluation & Benchmarking",
      notes: "",
    });
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="pilot-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-lg bg-white rounded-3xl shadow-2xl border-2 border-emerald-500/20 overflow-hidden text-slate-900">
        {/* Header */}
        <div className="px-6 py-5 bg-gradient-to-r from-emerald-50/70 via-white to-orange-50/70 border-b border-slate-200/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-100 border border-emerald-200 flex items-center justify-center text-emerald-700 shadow-xs">
              <Shield size={20} />
            </div>
            <div>
              <h2 id="pilot-modal-title" className="text-lg font-bold text-slate-900 tracking-tight font-display">
                Request an Enterprise Pilot
              </h2>
              <p className="text-xs text-slate-500 font-normal">
                Experience governed AI lifecycle management on your infrastructure
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleReset}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {isSuccess ? (
            <div className="py-6 text-center space-y-4">
              <div className="w-14 h-14 rounded-full bg-emerald-100 border border-emerald-300 text-emerald-700 flex items-center justify-center mx-auto shadow-sm">
                <CheckCircle2 size={32} />
              </div>
              <div className="space-y-1">
                <h3 className="text-xl font-bold text-slate-900 font-display">Pilot Request Received</h3>
                <p className="text-sm text-slate-600 max-w-md mx-auto font-normal">
                  Thank you, <strong className="text-slate-900">{formData.fullName}</strong>. We have
                  received your evaluation request for <strong className="text-slate-900">{formData.organization}</strong>.
                </p>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-left text-xs text-slate-700 space-y-2 max-w-md mx-auto font-normal">
                <div className="flex items-center gap-2 font-bold text-emerald-800 font-mono">
                  <Sparkles size={14} className="text-emerald-600" />
                  NEXT PROVISIONING STEPS
                </div>
                <p>
                  1. Our architecture team will review your deployment constraints and target compute hardware.
                </p>
                <p>
                  2. We will contact you at <span className="text-emerald-700 font-mono font-semibold">{formData.workEmail}</span> to provision an isolated tenant environment.
                </p>
              </div>
              <button
                type="button"
                onClick={handleReset}
                className="w-full py-3.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm transition-colors shadow-lg shadow-emerald-600/20 cursor-pointer"
              >
                Close & Return to Platform
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="pilot-fullname" className="block text-xs font-mono font-semibold text-slate-700 mb-1">
                    FULL NAME *
                  </label>
                  <div className="relative">
                    <User size={15} className="absolute left-3 top-3 text-slate-400" />
                    <input
                      id="pilot-fullname"
                      required
                      type="text"
                      placeholder="e.g. Dr. Sarah Jenkins"
                      value={formData.fullName}
                      onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                      className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 focus:bg-white transition-all text-slate-900 placeholder-slate-400"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="pilot-email" className="block text-xs font-mono font-semibold text-slate-700 mb-1">
                    WORK EMAIL *
                  </label>
                  <div className="relative">
                    <Mail size={15} className="absolute left-3 top-3 text-slate-400" />
                    <input
                      id="pilot-email"
                      required
                      type="email"
                      placeholder="s.jenkins@enterprise.com"
                      value={formData.workEmail}
                      onChange={(e) => setFormData({ ...formData, workEmail: e.target.value })}
                      className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 focus:bg-white transition-all text-slate-900 placeholder-slate-400"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="pilot-org" className="block text-xs font-mono font-semibold text-slate-700 mb-1">
                    ORGANIZATION / COMPANY *
                  </label>
                  <div className="relative">
                    <Building2 size={15} className="absolute left-3 top-3 text-slate-400" />
                    <input
                      id="pilot-org"
                      required
                      type="text"
                      placeholder="e.g. Meridian Financial Group"
                      value={formData.organization}
                      onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                      className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 focus:bg-white transition-all text-slate-900 placeholder-slate-400"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="pilot-teamsize" className="block text-xs font-mono font-semibold text-slate-700 mb-1">
                    AI / ENGINEERING TEAM SIZE
                  </label>
                  <select
                    id="pilot-teamsize"
                    value={formData.teamSize}
                    onChange={(e) => setFormData({ ...formData, teamSize: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 focus:bg-white transition-all text-slate-900 cursor-pointer"
                  >
                    <option value="1-10">1 - 10 engineers</option>
                    <option value="10-50">10 - 50 engineers</option>
                    <option value="50-250">50 - 250 engineers</option>
                    <option value="250+">250+ enterprise wide</option>
                  </select>
                </div>
              </div>

              <div>
                <label htmlFor="pilot-usecase" className="block text-xs font-mono font-semibold text-slate-700 mb-1">
                  PRIMARY EVALUATION FOCUS *
                </label>
                <select
                  id="pilot-usecase"
                  value={formData.useCase}
                  onChange={(e) => setFormData({ ...formData, useCase: e.target.value })}
                  className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 focus:bg-white transition-all text-slate-900 cursor-pointer"
                >
                  <option value="Model Evaluation & Benchmarking">Model Evaluation & Benchmark Suites</option>
                  <option value="Data Protection & PII Masking">Data Ingestion, Masking & Protection (Gate 1)</option>
                  <option value="Hardware Cost & Optimization">Hardware Cost Optimization & VRAM Planning (Gate 2)</option>
                  <option value="Artifact Governance & Release Manifests">Artifact Governance & Cryptographic Signing (Gate 3)</option>
                  <option value="Private Local Customer Runtime">Private / Local Customer Runtime & Blue-Green Rollouts</option>
                  <option value="Full End-to-End AI Lifecycle">Complete End-to-End AI Lifecycle Platform</option>
                </select>
              </div>

              <div>
                <label htmlFor="pilot-notes" className="block text-xs font-mono font-semibold text-slate-700 mb-1">
                  TECHNICAL ENVIRONMENT OR REQUIREMENTS (OPTIONAL)
                </label>
                <textarea
                  id="pilot-notes"
                  rows={2}
                  placeholder="e.g. On-premise air-gapped cluster, Kubernetes, custom LLM fine-tuning..."
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 focus:bg-white transition-all text-slate-900 placeholder-slate-400 resize-none"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="btn-emerald-luxury w-full py-3.5 px-4 rounded-xl text-white font-display font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-60 cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Submitting Pilot Request...
                    </>
                  ) : (
                    <>
                      <Send size={15} />
                      Submit Pilot Request
                    </>
                  )}
                </button>
                <p className="mt-2.5 text-center text-[11px] text-slate-500 font-normal">
                  No credit card required. Our architecture team configures pilot tenants according to your compliance parameters.
                </p>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
