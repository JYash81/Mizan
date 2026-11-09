import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  Eye,
  Fingerprint,
  Layers,
  Lock,
  Search,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import { apiGet } from "../../../lib/api/client";
import type { Gate1Approval, MaskingRun } from "../types";

export function DataProtectionOverviewPage() {
  const { activeWorkspace } = useAuth();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");

  const workspaceId = activeWorkspace?.id;

  const { data: runs = [], isLoading: runsLoading } = useQuery<MaskingRun[]>({
    queryKey: ["masking-runs", workspaceId],
    queryFn: () =>
      apiGet<MaskingRun[]>(`/workspaces/${workspaceId}/masking-runs`),
    enabled: !!workspaceId,
  });

  const { data: approvals = [] } = useQuery<Gate1Approval[]>({
    queryKey: ["gate1-approvals", workspaceId],
    queryFn: () =>
      apiGet<Gate1Approval[]>(`/workspaces/${workspaceId}/gate1/approvals`),
    enabled: !!workspaceId,
  });

  const totalRuns = runs.length;
  const totalFindings = runs.reduce((acc, r) => acc + (r.findings_count || 0), 0);
  const totalUnresolved = runs.reduce(
    (acc, r) => acc + (r.unresolved_findings_count || 0),
    0
  );
  const totalApproved = approvals.filter((a) => a.decision === "APPROVED").length;

  const filteredRuns = runs.filter(
    (r) =>
      r.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.source_dataset_digest.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6 text-slate-100">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold tracking-wider uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Workshop Data Plane
            </span>
            <span className="text-xs text-slate-400">Step 3 of 12</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <ShieldCheck className="w-7 h-7 text-emerald-400" />
            Sensitive Data Protection & Gate 1 Approvals
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-3xl leading-relaxed">
            Detect and mask personal information (including UAE Emirates IDs, IBANs, and phones)
            within sovereign workshop boundaries. No dataset may enter external AI experimentation
            without explicit, cryptographically verifiable human sign-off.
          </p>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Masking Runs
            </p>
            <p className="text-2xl font-bold text-white mt-1">{totalRuns}</p>
          </div>
          <div className="p-3 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Sensitive Spans Detected
            </p>
            <p className="text-2xl font-bold text-amber-400 mt-1">{totalFindings}</p>
          </div>
          <div className="p-3 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Eye className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Pending Review
            </p>
            <p className="text-2xl font-bold text-rose-400 mt-1">{totalUnresolved}</p>
          </div>
          <div className="p-3 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <ShieldAlert className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Gate 1 Signed Attestations
            </p>
            <p className="text-2xl font-bold text-emerald-400 mt-1">{totalApproved}</p>
          </div>
          <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Fingerprint className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        {/* Search Toolbar */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by Run ID or Digest..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950/60 border border-slate-700/80 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
            />
          </div>
        </div>

        {/* Runs List Table */}
        {runsLoading ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            Loading data protection records...
          </div>
        ) : filteredRuns.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-800/80 flex items-center justify-center mx-auto text-slate-400">
              <Lock className="w-6 h-6" />
            </div>
            <h3 className="text-base font-semibold text-slate-200">No Masking Runs Found</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Upload documents in the Datasets section and finalize a version to trigger
              automated personal data detection and masking.
            </p>
            <button
              onClick={() => navigate("/datasets")}
              className="mt-2 inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
            >
              Go to Datasets
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/40 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4 font-semibold">Run & Dataset Version</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Extraction Coverage</th>
                  <th className="py-3 px-4 font-semibold">Findings</th>
                  <th className="py-3 px-4 font-semibold">Gate 1 Approval</th>
                  <th className="py-3 px-4 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredRuns.map((run) => {
                  const isComplete = run.status === "COMPLETED";
                  const hasOcr = run.extraction_coverage === "OCR_REQUIRED";
                  const approval = approvals.find((a) => a.masking_run_id === run.id);

                  return (
                    <tr
                      key={run.id}
                      className="hover:bg-slate-800/30 transition-colors cursor-pointer"
                      onClick={() => navigate(`/data-protection/${run.id}`)}
                    >
                      <td className="py-3 px-4">
                        <div className="font-mono text-slate-200">{run.id.slice(0, 8)}...</div>
                        <div className="text-[11px] text-slate-400 font-mono truncate max-w-xs" title={run.source_dataset_digest}>
                          Source: {run.source_dataset_digest ? run.source_dataset_digest.slice(0, 16) + "..." : "N/A"}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium ${
                            isComplete
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : "bg-sky-500/10 text-sky-400 border border-sky-500/20"
                          }`}
                        >
                          {isComplete ? (
                            <CheckCircle className="w-3 h-3" />
                          ) : (
                            <AlertCircle className="w-3 h-3" />
                          )}
                          {run.status}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium ${
                            hasOcr
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                              : "bg-slate-800 text-slate-300"
                          }`}
                        >
                          {hasOcr && <AlertTriangle className="w-3 h-3" />}
                          {run.extraction_coverage}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-semibold text-slate-200">
                          {run.findings_count}
                        </span>
                        <span className="text-slate-400 text-[11px] ml-1">
                          ({run.unresolved_findings_count} pending)
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {approval ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                            <Fingerprint className="w-3 h-3" />
                            {approval.decision} ({approval.signature_algorithm})
                          </span>
                        ) : (
                          <span className="text-slate-500 text-[11px] italic">
                            Awaiting Human Review
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/data-protection/${run.id}`);
                          }}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
                        >
                          Review & Approve
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
