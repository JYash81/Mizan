import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { FaqItem } from "../types";
import { useScrollReveal } from "../hooks/useScrollReveal";

export function FaqSection() {
  const [openId, setOpenId] = useState<string | null>("faq-1");
  const sectionRef = useScrollReveal();

  const faqs: FaqItem[] = [
    {
      id: "faq-1",
      question: "What is Mizan?",
      answer:
        "Mizan is an enterprise AI lifecycle platform that connects experimentation, evaluation, optimization, governance, release management and runtime operations into one structured, traceable workflow.",
    },
    {
      id: "faq-2",
      question: "Is Mizan an AI chatbot?",
      answer:
        "No. Mizan is a platform for managing and operationalizing AI systems, rather than a general-purpose conversational assistant. It provides the infrastructure, evaluation test beds, and governance controls required to build dependable AI systems.",
    },
    {
      id: "faq-3",
      question: "Does Mizan support different AI models?",
      answer:
        "Yes. Mizan is architected for configurable model and provider workflows. It supports open-weight models (via Hugging Face and GGUF/AWQ quantized formats for local execution), proprietary models through standard provider APIs, and custom fine-tuned adapters produced through verified training recipes.",
    },
    {
      id: "faq-4",
      question: "Can organizations evaluate and compare models?",
      answer:
        "Yes. Mizan provides structured evaluation suites featuring deterministic scoring (exact match, regex, semantic similarity, and custom multi-engine evaluators). Teams can run matrix experiments and compare candidate models side-by-side across accuracy, latency, memory footprint, and cost metrics.",
    },
    {
      id: "faq-5",
      question: "Does Mizan support private or local deployment?",
      answer:
        "Yes. Mizan features a clear architectural distinction between its cloud control plane (for centralized management, evaluations, and catalog discovery) and its customer-local runtime daemon. The customer runtime runs on your private VPC or local workstation hardware, enabling offline-capable execution without sending proprietary input data to external hosts.",
    },
    {
      id: "faq-6",
      question: "Who is Mizan designed for?",
      answer:
        "Mizan is designed for enterprise AI teams, machine learning engineers, AI platform & infrastructure operators, and data-sensitive organizations seeking disciplined AI governance, measurable evaluation, and operational accountability.",
    },
  ];

  const toggle = (id: string) => {
    setOpenId(openId === id ? null : id);
  };

  return (
    <section
      id="faq"
      ref={sectionRef}
      className="py-28 lg:py-40 bg-[#FAFDFB] text-slate-900 border-b border-slate-200/80 relative noise-overlay"
    >
      {/* Ambient glows */}
      <div className="absolute top-1/3 left-1/4 w-[450px] h-[300px] bg-emerald-100/30 rounded-full blur-3xl pointer-events-none orb-2" />
      <div className="absolute bottom-1/3 right-1/4 w-[450px] h-[300px] bg-orange-100/30 rounded-full blur-3xl pointer-events-none orb-1" />

      <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto scroll-reveal">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-mono tracking-wider uppercase mb-5 font-semibold premium-pill">
            SECTION 07 // TECHNICAL & ARCHITECTURAL FAQ
          </div>
          <h2 className="text-3xl sm:text-5xl font-black tracking-[-0.03em] text-slate-950 leading-tight font-display text-balance">
            Frequently Asked Questions
          </h2>
          <p className="mt-4 text-slate-600 text-sm sm:text-base font-normal text-pretty">
            Essential answers regarding Mizan's architecture, model support, and deployment boundaries.
          </p>
        </div>

        <div className="mt-16 space-y-4">
          {faqs.map((faq, idx) => {
            const isOpen = openId === faq.id;
            const isOrange = idx % 2 === 1;
            const delay = `${0.08 + idx * 0.06}s`;

            return (
              <div
                key={faq.id}
                className={`rounded-3xl bg-white border transition-all duration-300 overflow-hidden shadow-sm scroll-reveal ${
                  isOpen
                    ? isOrange
                      ? "border-orange-300 ring-2 ring-orange-500/10 shadow-lg"
                      : "border-emerald-300 ring-2 ring-emerald-500/10 shadow-lg"
                    : "border-slate-200/90 hover:border-slate-300"
                }`}
                style={{ "--reveal-delay": delay } as React.CSSProperties}
              >
                <button
                  type="button"
                  onClick={() => toggle(faq.id)}
                  aria-expanded={isOpen}
                  className="w-full p-6 sm:p-7 text-left flex items-center justify-between gap-4 font-bold text-slate-900 hover:text-emerald-700 transition-colors cursor-pointer"
                >
                  <span className="text-base sm:text-lg flex items-center gap-3.5 font-display">
                    <span
                      className={`text-xs font-mono font-bold px-2.5 py-1 rounded-lg border ${
                        isOrange
                          ? "text-orange-700 bg-orange-50 border-orange-200"
                          : "text-emerald-700 bg-emerald-50 border-emerald-200"
                      }`}
                    >
                      0{idx + 1}
                    </span>
                    {faq.question}
                  </span>
                  <ChevronDown
                    size={18}
                    className={`shrink-0 transition-transform duration-300 ${
                      isOpen
                        ? isOrange
                          ? "rotate-180 text-orange-600"
                          : "rotate-180 text-emerald-600"
                        : "text-slate-400"
                    }`}
                  />
                </button>
                {isOpen && (
                  <div className="px-6 sm:px-7 pb-7 pt-1 text-sm text-slate-600 leading-relaxed border-t border-slate-100 font-normal">
                    {faq.answer}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
