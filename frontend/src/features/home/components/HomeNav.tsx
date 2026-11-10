import { useState } from "react";
import { Link } from "react-router-dom";
import { Shield, Menu, X, LayoutDashboard, UserCheck, ChevronRight } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";

interface HomeNavProps {
  onOpenPilot: () => void;
}

export function HomeNav({ onOpenPilot }: HomeNavProps) {
  const { user } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: "Why Mizan", href: "#why-mizan" },
    { label: "Platform", href: "#platform" },
    { label: "Audience", href: "#audience" },
    { label: "How It Works", href: "#how-it-works" },
    { label: "Differentiators", href: "#differentiators" },
    { label: "Trust & Governance", href: "#trust-governance" },
    { label: "FAQ", href: "#faq" },
  ];

  const handleScrollTo = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    e.preventDefault();
    setMobileMenuOpen(false);
    const element = document.querySelector(href);
    if (element) {
      element.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full bg-white/95 backdrop-blur-xl border-b border-slate-200/80 text-slate-900 transition-all shadow-[0_1px_12px_rgba(0,0,0,0.04)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 sm:h-20 flex items-center justify-between">
        {/* Brand Emblem */}
        <Link to="/" className="flex items-center gap-3 sm:gap-3.5 group no-underline text-slate-900">
          <div className="relative w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-emerald-600 via-teal-600 to-orange-500 p-[1.5px] shadow-md shadow-emerald-900/10">
            <div className="w-full h-full bg-white rounded-[10px] flex items-center justify-center font-black text-lg text-emerald-700 font-display group-hover:text-emerald-600 transition-colors">
              M
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-orange-500 ring-2 ring-white" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-lg sm:text-xl font-black tracking-tight text-slate-950 font-display">
                MIZAN
              </span>
              <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold tracking-wider bg-orange-50 text-orange-700 border border-orange-200/80 rounded uppercase">
                ENTERPRISE
              </span>
            </div>
            <span className="text-[9px] sm:text-[10px] text-slate-500 font-mono tracking-widest uppercase font-semibold">
              AI LIFECYCLE & GOVERNANCE
            </span>
          </div>
        </Link>

        {/* Desktop Navigation Links */}
        <nav className="hidden lg:flex items-center gap-0.5 bg-slate-100/85 backdrop-blur-md border border-slate-200/90 px-3 py-1.5 rounded-full text-xs font-semibold text-slate-600 font-display shadow-[inset_0_1px_2px_rgba(0,0,0,0.04)]">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={(e) => handleScrollTo(e, link.href)}
              className="px-3 py-1.5 rounded-full hover:text-emerald-700 hover:bg-white hover:shadow-xs transition-all cursor-pointer font-medium text-slate-700"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Right CTA / Auth Action Buttons */}
        <div className="hidden sm:flex items-center gap-2 sm:gap-2.5">
          {user ? (
            <div className="flex items-center gap-2.5">
              <div className="flex items-center gap-2 text-xs text-slate-700 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 font-mono">
                <UserCheck size={14} className="text-emerald-600" />
                <span className="font-semibold max-w-[130px] truncate">{user.full_name}</span>
              </div>
              <Link
                to="/dashboard"
                className="btn-emerald-luxury inline-flex items-center gap-2 h-9 px-4 text-xs font-display font-semibold rounded-lg text-white transition-all shadow-sm shadow-emerald-700/20"
              >
                <LayoutDashboard size={14} />
                Open Console
              </Link>
            </div>
          ) : (
            <div className="flex items-center gap-2 sm:gap-2.5">
              <Link
                to="/login"
                className="h-9 px-3.5 text-xs font-display font-semibold text-slate-700 hover:text-emerald-700 rounded-lg hover:bg-slate-100/80 transition-colors flex items-center"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="btn-emerald-luxury h-9 px-4 text-xs font-display font-semibold text-white rounded-lg shadow-sm shadow-emerald-700/20 transition-all flex items-center"
              >
                Sign Up
              </Link>
              <button
                type="button"
                onClick={onOpenPilot}
                className="btn-orange-luxury h-9 px-4 text-xs font-display font-semibold text-white rounded-lg shadow-sm shadow-orange-700/20 transition-all flex items-center gap-1.5 cursor-pointer"
              >
                <Shield size={13} className="text-white" />
                <span>Request Pilot</span>
              </button>
            </div>
          )}
        </div>

        {/* Mobile menu toggle */}
        <div className="flex items-center gap-2 lg:hidden">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile dropdown menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-slate-200 bg-white px-5 pt-4 pb-6 space-y-4 shadow-xl">
          <nav className="flex flex-col space-y-1">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={(e) => handleScrollTo(e, link.href)}
                className="text-sm font-semibold text-slate-700 hover:text-emerald-700 py-2.5 flex items-center justify-between border-b border-slate-100 font-display"
              >
                <span>{link.label}</span>
                <ChevronRight size={14} className="text-slate-400" />
              </a>
            ))}
          </nav>

          <div className="pt-2 flex flex-col gap-2.5">
            {user ? (
              <Link
                to="/dashboard"
                className="btn-emerald-luxury w-full py-2.5 text-center text-xs font-display font-semibold rounded-xl text-white"
              >
                Open Console
              </Link>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-2">
                  <Link
                    to="/login"
                    className="w-full py-2.5 text-center text-xs font-display font-semibold text-slate-800 bg-slate-100 rounded-xl"
                  >
                    Sign In
                  </Link>
                  <Link
                    to="/register"
                    className="btn-emerald-luxury w-full py-2.5 text-center text-xs font-display font-semibold text-white rounded-xl"
                  >
                    Sign Up
                  </Link>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    onOpenPilot();
                  }}
                  className="btn-orange-luxury w-full py-2.5 text-xs font-display font-semibold text-white rounded-xl flex items-center justify-center gap-1.5"
                >
                  <Shield size={14} />
                  Request a Pilot
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
