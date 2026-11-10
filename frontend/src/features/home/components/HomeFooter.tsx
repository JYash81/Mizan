import { Link } from "react-router-dom";

interface HomeFooterProps {
  onOpenPilot: () => void;
}

export function HomeFooter({ onOpenPilot }: HomeFooterProps) {
  const scrollTo = (href: string) => {
    const el = document.querySelector(href);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <footer className="bg-slate-50 text-slate-600 text-xs border-t border-slate-200/90 noise-overlay relative">
      <div className="absolute top-0 left-0 right-0 premium-divider" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10">
          {/* Col 1: Brand & Category Definition */}
          <div className="space-y-4 md:col-span-1">
            <div className="flex items-center gap-3 text-slate-900">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-700 p-[1.5px] shadow-sm">
                <div className="w-full h-full bg-white rounded-[10px] flex items-center justify-center font-bold text-emerald-700 text-sm">
                  M
                </div>
              </div>
              <span className="text-lg font-black tracking-tight text-slate-900 font-display">MIZAN</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed font-normal">
              Enterprise AI Lifecycle Management, Experimentation, Evaluation and Governance Platform.
            </p>
            <p className="text-[11px] text-slate-500 leading-relaxed font-normal">
              Providing organizations with structured evidence, deterministic benchmark suites,
              and cryptographic release governance.
            </p>
          </div>

          {/* Col 2: Platform Modules */}
          <div className="space-y-3">
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900">
              Platform Modules
            </h4>
            <ul className="space-y-2 text-slate-600">
              <li>
                <a
                  href="#platform"
                  onClick={(e) => {
                    e.preventDefault();
                    scrollTo("#platform");
                  }}
                  className="hover:text-emerald-700 transition-colors"
                >
                  Data Protection & Masking (Gate 1)
                </a>
              </li>
              <li>
                <a
                  href="#platform"
                  onClick={(e) => {
                    e.preventDefault();
                    scrollTo("#platform");
                  }}
                  className="hover:text-emerald-700 transition-colors"
                >
                  AI Evaluation & Benchmark Suites
                </a>
              </li>
              <li>
                <a
                  href="#platform"
                  onClick={(e) => {
                    e.preventDefault();
                    scrollTo("#platform");
                  }}
                  className="hover:text-emerald-700 transition-colors"
                >
                  Hardware & Cost Preflights (Gate 2)
                </a>
              </li>
              <li>
                <a
                  href="#platform"
                  onClick={(e) => {
                    e.preventDefault();
                    scrollTo("#platform");
                  }}
                  className="hover:text-emerald-700 transition-colors"
                >
                  Artifact Registry & Provenance (Gate 3)
                </a>
              </li>
              <li>
                <a
                  href="#platform"
                  onClick={(e) => {
                    e.preventDefault();
                    scrollTo("#platform");
                  }}
                  className="hover:text-emerald-700 transition-colors"
                >
                  Model & Application Zoo
                </a>
              </li>
              <li>
                <a
                  href="#platform"
                  onClick={(e) => {
                    e.preventDefault();
                    scrollTo("#platform");
                  }}
                  className="hover:text-emerald-700 transition-colors"
                >
                  Customer Runtime & Operations
                </a>
              </li>
            </ul>
          </div>

          {/* Col 3: Architecture & Governance */}
          <div className="space-y-3">
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900">
              Architecture & Trust
            </h4>
            <ul className="space-y-2 text-slate-600">
              <li>
                <a
                  href="#how-it-works"
                  onClick={(e) => {
                    e.preventDefault();
                    scrollTo("#how-it-works");
                  }}
                  className="hover:text-emerald-700 transition-colors"
                >
                  5-Stage Connected Lifecycle
                </a>
              </li>
              <li>
                <a
                  href="#trust-governance"
                  onClick={(e) => {
                    e.preventDefault();
                    scrollTo("#trust-governance");
                  }}
                  className="hover:text-emerald-700 transition-colors"
                >
                  Three-Gate Approval Protocol
                </a>
              </li>
              <li>
                <a
                  href="#differentiators"
                  onClick={(e) => {
                    e.preventDefault();
                    scrollTo("#differentiators");
                  }}
                  className="hover:text-emerald-700 transition-colors"
                >
                  Evidence-Driven Decisions
                </a>
              </li>
              <li>
                <a
                  href="#faq"
                  onClick={(e) => {
                    e.preventDefault();
                    scrollTo("#faq");
                  }}
                  className="hover:text-emerald-700 transition-colors"
                >
                  Platform & Deployment FAQ
                </a>
              </li>
              <li>
                <button
                  type="button"
                  onClick={onOpenPilot}
                  className="text-left text-orange-600 hover:text-orange-700 font-semibold transition-colors cursor-pointer"
                >
                  Request Technical Pilot
                </button>
              </li>
            </ul>
          </div>

          {/* Col 4: Account & Access */}
          <div className="space-y-3">
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900">
              Account & Workspace
            </h4>
            <ul className="space-y-2 text-slate-600">
              <li>
                <Link to="/login" className="hover:text-emerald-700 transition-colors font-medium">
                  Sign In to Console
                </Link>
              </li>
              <li>
                <Link to="/register" className="hover:text-emerald-700 transition-colors font-medium">
                  Create Organization Account
                </Link>
              </li>
              <li>
                <Link to="/forgot-password" className="hover:text-emerald-700 transition-colors">
                  Reset Password
                </Link>
              </li>
              <li>
                <Link to="/verify-email" className="hover:text-emerald-700 transition-colors">
                  Email Verification
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-12 pt-8 border-t border-slate-200 flex flex-col md:flex-row items-center justify-between gap-4 text-[11px] text-slate-500 font-mono">
          <p>© {new Date().getFullYear()} Mizan Technologies. All rights reserved.</p>
          <p className="max-w-xl text-center md:text-right text-slate-500 font-sans text-xs">
            Mizan provides structured controls and evidence-driven lifecycle management.
            Capabilities vary according to customer deployment topology and configured compute hardware.
          </p>
        </div>
      </div>
    </footer>
  );
}
