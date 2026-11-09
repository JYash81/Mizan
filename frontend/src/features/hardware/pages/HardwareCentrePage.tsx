import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Cpu, Gauge, Calculator, GitCompare, DollarSign, ShieldCheck } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import {
  fetchHardwareProfiles,
  fetchLatestHardwareSnapshot,
  fetchLatestBenchmark,
  fetchQuantizations,
  fetchPricingCatalog,
  fetchGate2Requests,
} from "../api";
import { HardwareProfileCards } from "../components/HardwareProfileCards";
import { LocalHardwareDetector } from "../components/LocalHardwareDetector";
import { ResourceEstimatorForm } from "../components/ResourceEstimatorForm";
import { HardwareComparisonMatrix } from "../components/HardwareComparisonMatrix";
import { CostCentreView } from "../components/CostCentreView";
import { Gate2RequestsList } from "../components/Gate2RequestsList";

type TabKey = "PROFILES" | "LOCAL" | "ESTIMATOR" | "COMPARE" | "COST" | "GATE2";

export const HardwareCentrePage: React.FC = () => {
  const { activeWorkspace } = useAuth();
  const workspaceId = activeWorkspace?.id;
  const [activeTab, setActiveTab] = useState<TabKey>("PROFILES");

  const { data: profiles = [], isLoading: loadingProfiles } = useQuery({
    queryKey: ["hardware-profiles", workspaceId],
    queryFn: () => fetchHardwareProfiles(workspaceId!),
    enabled: Boolean(workspaceId),
  });

  const { data: latestSnapshot = null, refetch: refetchSnapshot } = useQuery({
    queryKey: ["hardware-snapshot", workspaceId],
    queryFn: () => fetchLatestHardwareSnapshot(workspaceId!),
    enabled: Boolean(workspaceId),
  });

  const { data: latestBenchmark = null, refetch: refetchBenchmark } = useQuery({
    queryKey: ["hardware-benchmark", workspaceId],
    queryFn: () => fetchLatestBenchmark(workspaceId!),
    enabled: Boolean(workspaceId),
  });

  const { data: quantizations = [] } = useQuery({
    queryKey: ["quantizations", workspaceId],
    queryFn: () => fetchQuantizations(workspaceId!),
    enabled: Boolean(workspaceId),
  });

  const { data: catalog = [] } = useQuery({
    queryKey: ["pricing-catalog", workspaceId],
    queryFn: () => fetchPricingCatalog(workspaceId!),
    enabled: Boolean(workspaceId),
  });

  const { data: gate2Requests = [], refetch: refetchGate2 } = useQuery({
    queryKey: ["gate2-requests", workspaceId],
    queryFn: () => fetchGate2Requests(workspaceId!),
    enabled: Boolean(workspaceId),
  });

  if (!workspaceId) {
    return (
      <div className="max-w-7xl mx-auto p-12 my-6 bg-slate-900 text-slate-200 rounded-2xl border border-slate-800 shadow-xl text-center space-y-3">
        <Cpu className="w-10 h-10 mx-auto text-emerald-500" />
        <h2 className="text-lg font-semibold text-slate-100">No Workspace Selected</h2>
        <p className="text-xs text-slate-400">Please select an active workspace to view the Hardware &amp; Cost Centre.</p>
      </div>
    );
  }

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: "PROFILES", label: "Hardware Profiles", icon: <Cpu className="w-4 h-4" /> },
    { key: "LOCAL", label: "Local & Benchmark", icon: <Gauge className="w-4 h-4" /> },
    { key: "ESTIMATOR", label: "Resource Estimator", icon: <Calculator className="w-4 h-4" /> },
    { key: "COMPARE", label: "Cross-Hardware Comparison", icon: <GitCompare className="w-4 h-4" /> },
    { key: "COST", label: "Cost & Pricing", icon: <DollarSign className="w-4 h-4" /> },
    { key: "GATE2", label: "Gate 2 Approvals", icon: <ShieldCheck className="w-4 h-4" /> },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6 bg-slate-900 text-slate-100 rounded-2xl border border-slate-800 shadow-xl my-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-neutral-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-100 flex items-center gap-2">
            <Cpu className="w-6 h-6 text-emerald-500" />
            Hardware Knowledge Base &amp; Gate 2 Financial Centre
          </h1>
          <p className="text-sm text-neutral-400 mt-1">
            Reference hardware registry, deterministic resource and memory estimators, Decimal pricing catalog, and Ed25519 digitally-signed financial approvals.
          </p>
        </div>
      </div>

      {/* Tabs navigation */}
      <div className="flex gap-2 border-b border-neutral-800 pb-2 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
              activeTab === t.key
                ? "bg-neutral-800 text-emerald-400 border border-neutral-700 shadow-sm"
                : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Active Tab View */}
      {loadingProfiles ? (
        <div className="py-16 text-center text-sm text-neutral-500">
          Loading hardware profiles and specifications...
        </div>
      ) : (
        <div>
          {activeTab === "PROFILES" && <HardwareProfileCards profiles={profiles} />}

          {activeTab === "LOCAL" && (
            <LocalHardwareDetector
              workspaceId={workspaceId}
              initialSnapshot={latestSnapshot}
              initialBenchmark={latestBenchmark}
            />
          )}

          {activeTab === "ESTIMATOR" && (
            <ResourceEstimatorForm
              workspaceId={workspaceId}
              profiles={profiles}
              quantizations={quantizations}
            />
          )}

          {activeTab === "COMPARE" && (
            <HardwareComparisonMatrix
              workspaceId={workspaceId}
              quantizations={quantizations}
            />
          )}

          {activeTab === "COST" && (
            <CostCentreView workspaceId={workspaceId} catalog={catalog} />
          )}

          {activeTab === "GATE2" && (
            <Gate2RequestsList
              workspaceId={workspaceId}
              requests={gate2Requests}
              profiles={profiles}
              onRefresh={() => {
                refetchGate2();
                refetchSnapshot();
                refetchBenchmark();
              }}
            />
          )}
        </div>
      )}
    </div>
  );
};
