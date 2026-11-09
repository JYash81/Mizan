import React, { useState } from "react";
import { authorizeGate2, createGate2Request, decideGate2Request, revokeGate2Request } from "../api";
import type { FinancialAuthorizationResponse, Gate2ApprovalRequest, HardwareProfile } from "../types";

interface Props {
  workspaceId: string;
  requests: Gate2ApprovalRequest[];
  profiles: HardwareProfile[];
  onRefresh: () => void;
}

export const Gate2RequestsList: React.FC<Props> = ({
  workspaceId,
  requests,
  profiles,
  onRefresh,
}) => {
  const [showNewModal, setShowNewModal] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<Gate2ApprovalRequest | null>(null);
  const [actionType, setActionType] = useState<"DECIDE" | "REVOKE" | "TEST_AUTH" | null>(null);

  // New Request Form State
  const [title, setTitle] = useState("Local Evaluation Workload");
  const [purpose, setPurpose] = useState("Run automated benchmark and evaluation suite");
  const [workloadType, setWorkloadType] = useState("EXPERIMENT_EVALUATION");
  const [hardwareKey, setHardwareKey] = useState("LOCAL_CPU_I5_8GB");
  const [provider, setProvider] = useState("local");
  const [instanceType, setInstanceType] = useState("local-i5");
  const [region, setRegion] = useState("local");
  const [duration, setDuration] = useState<number>(2.0);
  const [maxBudget, setMaxBudget] = useState<string>("0.00");

  // Decision state
  const [decision, setDecision] = useState<"APPROVE" | "REJECT">("APPROVE");
  const [decisionReason, setDecisionReason] = useState("");
  const [revocationReason, setRevocationReason] = useState("");

  // Authorization test state
  const [authResult, setAuthResult] = useState<FinancialAuthorizationResponse | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      await createGate2Request(workspaceId, {
        title,
        purpose,
        workload_type: workloadType,
        hardware_profile_key: hardwareKey,
        provider_name: provider,
        instance_type: instanceType,
        region,
        estimated_duration_hours: duration,
        max_duration_hours: duration * 1.5,
        max_authorized_budget: maxBudget,
      });
      setShowNewModal(false);
      onRefresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create Gate 2 request.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDecide = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRequest) return;
    setIsLoading(true);
    setError(null);
    try {
      await decideGate2Request(workspaceId, selectedRequest.id, {
        decision,
        decision_reason: decisionReason,
      });
      setActionType(null);
      setSelectedRequest(null);
      onRefresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to decide request.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRevoke = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRequest) return;
    setIsLoading(true);
    setError(null);
    try {
      await revokeGate2Request(workspaceId, selectedRequest.id, {
        revocation_reason: revocationReason,
      });
      setActionType(null);
      setSelectedRequest(null);
      onRefresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to revoke request.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestAuth = async (req: Gate2ApprovalRequest) => {
    setSelectedRequest(req);
    setActionType("TEST_AUTH");
    setIsLoading(true);
    setError(null);
    try {
      const res = await authorizeGate2(workspaceId, {
        approval_request_id: req.id,
      });
      setAuthResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authorization check failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return "bg-emerald-950/80 text-emerald-300 border-emerald-700";
      case "PENDING_APPROVAL":
        return "bg-amber-950/80 text-amber-300 border-amber-700";
      case "BLOCKED_BY_POLICY":
        return "bg-rose-950/80 text-rose-300 border-rose-700";
      case "REJECTED":
      case "REVOKED":
        return "bg-neutral-800 text-neutral-400 border-neutral-700";
      default:
        return "bg-neutral-800 text-neutral-400 border-neutral-700";
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-xl font-semibold text-neutral-100">
            Gate 2 Financial Approval & Governance
          </h2>
          <p className="text-sm text-neutral-400 mt-1">
            Explicit budget ceilings, canonical proposal bindings, and Ed25519 digital attestation.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowNewModal(true)}
          className="px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors"
        >
          + Request Financial Approval
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-sm">
          {error}
        </div>
      )}

      {/* Requests Table */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 overflow-hidden">
        {requests.length === 0 ? (
          <div className="p-12 text-center text-sm text-neutral-500">
            No Gate 2 financial approval requests recorded in this workspace.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left text-neutral-300">
              <thead className="bg-neutral-950/80 text-neutral-400 uppercase tracking-wider border-b border-neutral-800">
                <tr>
                  <th className="py-3 px-4">Title & Workload</th>
                  <th className="py-3 px-4">Hardware Profile</th>
                  <th className="py-3 px-4">Duration & Cost</th>
                  <th className="py-3 px-4">Budget Cap</th>
                  <th className="py-3 px-4">Digest & Attestation</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800/60">
                {requests.map((r) => (
                  <tr key={r.id} className="hover:bg-neutral-800/30">
                    <td className="py-3 px-4">
                      <div className="font-medium text-neutral-100">{r.title}</div>
                      <div className="text-[11px] text-neutral-500 font-mono mt-0.5">
                        {r.workload_type}
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <span className="font-medium text-neutral-200">{r.hardware_profile_key}</span>
                      <span className="text-neutral-500 block text-[11px]">
                        {r.provider_name} ({r.instance_type})
                      </span>
                    </td>

                    <td className="py-3 px-4 font-mono">
                      <span className="text-neutral-200">{r.estimated_duration_hours}h</span>
                      <span className="text-neutral-500 block text-[11px]">
                        Est: ${parseFloat(r.estimated_total_cost).toFixed(2)}
                      </span>
                    </td>

                    <td className="py-3 px-4 font-mono font-semibold text-emerald-400">
                      ${parseFloat(r.max_authorized_budget).toFixed(2)}
                    </td>

                    <td className="py-3 px-4 font-mono text-[11px]">
                      <span className="text-neutral-400" title={r.proposal_digest}>
                        {r.proposal_digest.substring(0, 10)}...
                      </span>
                      {r.approval_signature && (
                        <span className="text-purple-400 block text-[10px]">
                          Ed25519 Signed
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-4">
                      <span
                        className={`text-[10px] px-2.5 py-0.5 rounded-full border font-semibold ${getStatusBadge(
                          r.status
                        )}`}
                      >
                        {r.status}
                      </span>
                    </td>

                    <td className="py-3 px-4 text-right space-x-2">
                      {r.status === "PENDING_APPROVAL" && (
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedRequest(r);
                            setActionType("DECIDE");
                            setDecision("APPROVE");
                            setDecisionReason("Approved for experimentation.");
                          }}
                          className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs transition-colors"
                        >
                          Review & Decide
                        </button>
                      )}

                      {r.status === "APPROVED" && (
                        <>
                          <button
                            type="button"
                            onClick={() => handleTestAuth(r)}
                            className="px-2 py-1 rounded bg-purple-950 hover:bg-purple-900 border border-purple-800 text-purple-300 text-xs transition-colors"
                            title="Verify signature and global cost policy check"
                          >
                            Authorize Execution
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedRequest(r);
                              setActionType("REVOKE");
                              setRevocationReason("Revoked by administrator");
                            }}
                            className="px-2 py-1 rounded bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs transition-colors"
                          >
                            Revoke
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* New Request Modal */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-lg p-6 rounded-2xl bg-neutral-900 border border-neutral-800 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold text-neutral-100">
              New Gate 2 Financial Approval Request
            </h3>
            <p className="text-xs text-neutral-400">
              Submit an infrastructure workload proposal to create a deterministic cryptographic digest.
            </p>

            <form onSubmit={handleCreate} className="space-y-3.5 text-xs">
              <div>
                <label className="text-neutral-400 block mb-1">Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>

              <div>
                <label className="text-neutral-400 block mb-1">Business Purpose</label>
                <textarea
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-neutral-400 block mb-1">Hardware Profile</label>
                  <select
                    value={hardwareKey}
                    onChange={(e) => {
                      setHardwareKey(e.target.value);
                      if (e.target.value === "LOCAL_CPU_I5_8GB") {
                        setProvider("local");
                        setInstanceType("local-i5");
                        setRegion("local");
                        setMaxBudget("0.00");
                      } else if (e.target.value === "NVIDIA_T4_16GB") {
                        setProvider("gcp");
                        setInstanceType("n1-standard-4-t4-16gb");
                        setRegion("us-central1");
                        setMaxBudget("5.00");
                      } else if (e.target.value === "NVIDIA_A100_40GB") {
                        setProvider("gcp");
                        setInstanceType("a2-highgpu-1g-a100-40gb");
                        setRegion("us-central1");
                        setMaxBudget("50.00");
                      }
                    }}
                    className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
                  >
                    {profiles.map((p) => (
                      <option key={p.profile_key} value={p.profile_key}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-neutral-400 block mb-1">Estimated Duration (Hrs)</label>
                  <input
                    type="number"
                    value={duration}
                    onChange={(e) => setDuration(parseFloat(e.target.value) || 0.5)}
                    step="0.5"
                    min="0.5"
                    className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-neutral-400 block mb-1">Max Authorized Budget ($)</label>
                  <input
                    type="text"
                    value={maxBudget}
                    onChange={(e) => setMaxBudget(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500 font-mono"
                    required
                  />
                </div>
                <div>
                  <label className="text-neutral-400 block mb-1">Workload Type</label>
                  <input
                    type="text"
                    value={workloadType}
                    onChange={(e) => setWorkloadType(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500 font-mono"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-neutral-800">
                <button
                  type="button"
                  onClick={() => setShowNewModal(false)}
                  className="px-4 py-2 rounded-lg border border-neutral-700 text-neutral-300 hover:bg-neutral-800 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs disabled:opacity-50"
                >
                  {isLoading ? "Submitting..." : "Submit Proposal"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Decision Modal */}
      {actionType === "DECIDE" && selectedRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-md p-6 rounded-2xl bg-neutral-900 border border-neutral-800 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold text-neutral-100">
              Review & Sign Gate 2 Request
            </h3>
            <p className="text-xs text-neutral-400">
              Approval digitally signs the proposal digest using the platform Ed25519 key.
            </p>

            <form onSubmit={handleDecide} className="space-y-4 text-xs">
              <div>
                <label className="text-neutral-400 block mb-1">Decision</label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 text-neutral-200">
                    <input
                      type="radio"
                      name="decision"
                      value="APPROVE"
                      checked={decision === "APPROVE"}
                      onChange={() => setDecision("APPROVE")}
                    />
                    Approve (Digital Sign)
                  </label>
                  <label className="flex items-center gap-2 text-neutral-200">
                    <input
                      type="radio"
                      name="decision"
                      value="REJECT"
                      checked={decision === "REJECT"}
                      onChange={() => setDecision("REJECT")}
                    />
                    Reject
                  </label>
                </div>
              </div>

              <div>
                <label className="text-neutral-400 block mb-1">Justification Reason</label>
                <textarea
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-neutral-800">
                <button
                  type="button"
                  onClick={() => setActionType(null)}
                  className="px-4 py-2 rounded-lg border border-neutral-700 text-neutral-300 hover:bg-neutral-800 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs disabled:opacity-50"
                >
                  {isLoading ? "Signing..." : "Confirm Decision"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Revocation Modal */}
      {actionType === "REVOKE" && selectedRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-md p-6 rounded-2xl bg-neutral-900 border border-neutral-800 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold text-neutral-100">
              Revoke Gate 2 Financial Approval
            </h3>
            <form onSubmit={handleRevoke} className="space-y-4 text-xs">
              <div>
                <label className="text-neutral-400 block mb-1">Revocation Reason</label>
                <textarea
                  value={revocationReason}
                  onChange={(e) => setRevocationReason(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 focus:outline-none focus:border-rose-500"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-neutral-800">
                <button
                  type="button"
                  onClick={() => setActionType(null)}
                  className="px-4 py-2 rounded-lg border border-neutral-700 text-neutral-300 hover:bg-neutral-800 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs disabled:opacity-50"
                >
                  {isLoading ? "Revoking..." : "Revoke Approval"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Authorization Check Result Modal */}
      {actionType === "TEST_AUTH" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-md p-6 rounded-2xl bg-neutral-900 border border-neutral-800 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold text-neutral-100">
              Execution Readiness Check
            </h3>
            {authResult ? (
              <div className="space-y-3 text-xs">
                <div
                  className={`p-4 rounded-xl border ${
                    authResult.authorized
                      ? "bg-emerald-950/40 border-emerald-700 text-emerald-300"
                      : "bg-rose-950/40 border-rose-700 text-rose-300"
                  }`}
                >
                  <span className="font-semibold text-sm block">
                    {authResult.authorized ? "Execution Authorized" : "Execution Blocked"}
                  </span>
                  <p className="mt-1 leading-relaxed">{authResult.reason}</p>
                </div>

                <div className="grid grid-cols-2 gap-2 text-neutral-400 p-3 rounded-lg bg-neutral-950 border border-neutral-800">
                  <div>
                    <span className="text-neutral-500 block">Digest Match:</span>
                    <span className={authResult.proposal_digest_match ? "text-emerald-400" : "text-rose-400"}>
                      {authResult.proposal_digest_match ? "Verified" : "Tampered"}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">Ed25519 Signature:</span>
                    <span className={authResult.signature_valid ? "text-emerald-400" : "text-rose-400"}>
                      {authResult.signature_valid ? "Valid" : "Invalid"}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">Policy Allowed:</span>
                    <span className={authResult.policy_allowed ? "text-emerald-400" : "text-rose-400"}>
                      {authResult.policy_allowed ? "Permitted" : "Disallowed by Policy"}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block">Status:</span>
                    <span className="text-neutral-200">{authResult.status}</span>
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setActionType(null);
                      setAuthResult(null);
                    }}
                    className="px-4 py-2 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs"
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-neutral-400">
                Evaluating authorization...
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
