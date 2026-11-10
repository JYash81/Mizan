import { useState } from "react";
import { HomeNav } from "./components/HomeNav";
import { HeroSection } from "./components/HeroSection";
import { WhyMizanSection } from "./components/WhyMizanSection";
import { PlatformSection } from "./components/PlatformSection";
import { AudienceSection } from "./components/AudienceSection";
import { HowItWorksSection } from "./components/HowItWorksSection";
import { DifferentiatorsSection } from "./components/DifferentiatorsSection";
import { TrustSecuritySection } from "./components/TrustSecuritySection";
import { FaqSection } from "./components/FaqSection";
import { CtaSection } from "./components/CtaSection";
import { HomeFooter } from "./components/HomeFooter";
import { PilotModal } from "./components/PilotModal";

export function HomePage() {
  const [isPilotOpen, setIsPilotOpen] = useState(false);

  return (
    <div className="min-h-screen bg-white text-slate-900 selection:bg-emerald-500 selection:text-white font-sans antialiased">
      {/* Top Navigation Bar with Sign In, Sign Up, and Pilot CTA */}
      <HomeNav onOpenPilot={() => setIsPilotOpen(true)} />

      {/* Main Content Flow */}
      <main id="main-content">
        {/* Main Hero Screen with Interactive Workbench */}
        <HeroSection onOpenPilot={() => setIsPilotOpen(true)} />

        {/* Section 01: Why Mizan? */}
        <WhyMizanSection />

        {/* Section 02: What is Mizan? (Interactive Platform Explorer) */}
        <PlatformSection />

        {/* Section 03: Who Needs Mizan? (Audience Groups) */}
        <AudienceSection />

        {/* Section 04: How Mizan Works (5-Stage Connected Pipeline) */}
        <HowItWorksSection />

        {/* Section 05: What Makes Mizan Different? (5 Differentiators) */}
        <DifferentiatorsSection />

        {/* Section 06: Trust, Security & Governance (Three-Gate Vault Architecture) */}
        <TrustSecuritySection />

        {/* Section 07: Technical FAQ */}
        <FaqSection />

        {/* Section 08: Final Call to Action */}
        <CtaSection onOpenPilot={() => setIsPilotOpen(true)} />
      </main>

      {/* Enterprise Footer */}
      <HomeFooter onOpenPilot={() => setIsPilotOpen(true)} />

      {/* Interactive Pilot Request Modal */}
      <PilotModal isOpen={isPilotOpen} onClose={() => setIsPilotOpen(false)} />
    </div>
  );
}
