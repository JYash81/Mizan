import React, { useState } from "react";
import { estimateCost } from "../api";
import type { CostEstimateResponse, PricingCatalogEntry } from "../types";

interface Props {
  workspaceId: string;
  catalog: PricingCatalogEntry[];
}

export const CostCentreView: React.FC<Props> = ({ workspaceId, catalog }) => {
  const [provider, setProvider] = useState("local");
  const [instanceType, setInstanceType] = useState("local-i5");
  const [region, setRegion] = useState("local");
  const [durationHours, setDurationHours] = useState<number>(2.0);

  const [estimate, setEstimate] = useState<CostEstimateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync instanceType and region when provider changes
  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider);
    const matches = catalog.filter((c) => c.provider_name === newProvider);
    if (matches.length > 0) {
      setInstanceType(matches[0].instance_type);
      setRegion(matches[0].region);
    }
  };

  const handleEstimate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const res = await estimateCost(workspaceId, {
        provider_name: provider,
        instance_type: instanceType,
        region: region,
        duration_hours: durationHours,
      });
      setEstimate(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to calculate cost.");
    } finally {
      setIsLoading(false);
    }
  };

  const getProvenanceBadge = (prov?: string) => {
    switch (prov) {
      case "OFFICIAL_SOURCE":
        return "bg-emerald-950 text-emerald-300 border-emerald-800";
      case "VENDOR_REFERENCE":
      case "REFERENCE_ONLY":
        return "bg-sky-950 text-sky-300 border-sky-800";
      case "USER_SUPPLIED":
        return "bg-amber-950 text-amber-300 border-amber-800";
      default:
        return "bg-neutral-800 text-neutral-400 border-neutral-700";
    }
  };

  return (
    <div className="space-y-6">
      {/* Non-Negotiable Free-Only Policy Banner */}
      <div className="p-5 rounded-xl border border-emerald-800/80 bg-emerald-950/30 text-emerald-200">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-emerald-900/60 text-emerald-300 text-lg">
            🛡️
          </div>
          <div>
            <h4 className="text-base font-semibold text-emerald-300">
              Free-Only Infrastructure Policy Active ($0.00 Additional Spend)
            </h4>
            <p className="text-xs text-emerald-400/90 mt-1 leading-relaxed">
              Mizan is configured strictly with local and free resources. External billable cloud compute and automated provisioning are disbarred by policy (<code className="text-xs bg-emerald-950/80 px-1 py-0.5 rounded text-emerald-300 font-mono">ALLOW_PAID_COMPUTE=false</code>). All cloud estimates below serve transparent analytical benchmarking and financial planning.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Cost Calculator */}
        <div className="lg:col-span-5 p-6 rounded-xl border border-neutral-800 bg-neutral-900/60 space-y-4">
          <h3 className="text-lg font-medium text-neutral-100">
            Workload Cost Estimator
          </h3>
          <p className="text-xs text-neutral-400">
            Deterministic Decimal arithmetic with billing-unit alignment.
          </p>

          <form onSubmit={handleEstimate} className="space-y-4 text-xs">
            <div>
              <label className="text-neutral-400 block mb-1">Provider</label>
              <select
                value={provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
              >
                {Array.from(new Set(catalog.map((c) => c.provider_name))).map((p) => (
                  <option key={p} value={p}>
                    {p === "local" ? "local (Workstation $0.00)" : p.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-neutral-400 block mb-1">Instance & Rate</label>
              <select
                value={instanceType}
                onChange={(e) => {
                  setInstanceType(e.target.value);
                  const entry = catalog.find((c) => c.instance_type === e.target.value);
                  if (entry) setRegion(entry.region);
                }}
                className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
              >
                {catalog
                  .filter((c) => c.provider_name === provider)
                  .map((c) => (
                    <option key={c.id} value={c.instance_type}>
                      {c.instance_type} (${parseFloat(c.hourly_rate).toFixed(3)}/hr in {c.region})
                    </option>
                  ))}
              </select>
            </div>

            <div>
              <label className="text-neutral-400 block mb-1">
                Workload Duration (Hours)
              </label>
              <input
                type="number"
                value={durationHours}
                onChange={(e) => setDurationHours(Math.max(0.1, parseFloat(e.target.value) || 0.1))}
                step="0.5"
                min="0.1"
                max="1000"
                className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs transition-colors disabled:opacity-50"
            >
              {isLoading ? "Estimating..." : "Calculate Cost"}
            </button>
          </form>

          {error && (
            <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs">
              {error}
            </div>
          )}

          {estimate && (
            <div className="mt-4 p-4 rounded-xl bg-neutral-950 border border-neutral-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-neutral-500">Estimated Total Cost</span>
                <span className="text-xl font-bold font-mono text-emerald-400">
                  ${estimate.total_estimated_cost} {estimate.currency}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs text-neutral-400 pt-2 border-t border-neutral-800">
                <div>
                  <span className="text-neutral-500 block">Billable Hours:</span>
                  <span className="text-neutral-200 font-mono">{estimate.billable_hours} hrs</span>
                </div>
                <div>
                  <span className="text-neutral-500 block">Status:</span>
                  <span className="text-emerald-400 font-medium">{estimate.status}</span>
                </div>
              </div>
              {estimate.warnings.length > 0 && (
                <div className="text-xs text-amber-400 mt-2">
                  {estimate.warnings.map((w, i) => (
                    <p key={i}>&bull; {w}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Pricing Catalog Table */}
        <div className="lg:col-span-7 p-6 rounded-xl border border-neutral-800 bg-neutral-900/60 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-medium text-neutral-100">
                Infrastructure Pricing Catalog
              </h3>
              <p className="text-xs text-neutral-400 mt-0.5">
                Versioned rates with explicit provenance tracking.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left text-neutral-300">
              <thead className="bg-neutral-950/80 text-neutral-400 uppercase tracking-wider border-b border-neutral-800">
                <tr>
                  <th className="py-2.5 px-3">Provider</th>
                  <th className="py-2.5 px-3">Instance Type</th>
                  <th className="py-2.5 px-3">Region</th>
                  <th className="py-2.5 px-3">Hourly Rate</th>
                  <th className="py-2.5 px-3">Provenance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800/60 font-mono">
                {catalog.map((entry) => (
                  <tr key={entry.id} className="hover:bg-neutral-800/30">
                    <td className="py-2.5 px-3 font-medium text-neutral-200 uppercase">
                      {entry.provider_name}
                    </td>
                    <td className="py-2.5 px-3 text-neutral-300 font-sans">
                      {entry.instance_type}
                    </td>
                    <td className="py-2.5 px-3 text-neutral-400">
                      {entry.region}
                    </td>
                    <td className="py-2.5 px-3 text-emerald-400 font-semibold">
                      ${parseFloat(entry.hourly_rate).toFixed(3)}
                    </td>
                    <td className="py-2.5 px-3 font-sans">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded border ${getProvenanceBadge(
                          entry.provenance
                        )}`}
                      >
                        {entry.provenance}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
