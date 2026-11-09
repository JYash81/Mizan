import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle,
  FileText,
  Fingerprint,
  Plus,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import { apiGet, apiPost } from "../../../lib/api/client";
import { Gate1ApprovalModal } from "../components/Gate1ApprovalModal";
import type {
  DocumentReview,
  Gate1Approval,
  Gate1Verification,
  MaskingRun,
  PiiFinding,
} from "../types";

export function MaskingReviewPage() {
  const { runId } = useParams<{ runId: string }>();
  const { activeWorkspace } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [manualEntity, setManualEntity] = useState("UAE_EMIRATES_ID");
  const [manualStart, setManualStart] = useState("");
  const [manualEnd, setManualEnd] = useState("");
  const [showManualModal, setShowManualModal] = useState(false);

  const workspaceId = activeWorkspace?.id;

  // 1. Fetch Masking Run
  const { data: run, isLoading: runLoading } = useQuery<MaskingRun>({
    queryKey: ["masking-run", workspaceId, runId],
    queryFn: () =>
      apiGet<MaskingRun>(`/workspaces/${workspaceId}/masking-runs/${runId}`),
    enabled: !!workspaceId && !!runId,
  });

  // 2. Fetch Findings
  const { data: findings = [] } = useQuery<PiiFinding[]>({
    queryKey: ["masking-findings", workspaceId, runId],
    queryFn: () =>
      apiGet<PiiFinding[]>(
        `/workspaces/${workspaceId}/masking-runs/${runId}/findings`
      ),
    enabled: !!workspaceId && !!runId,
  });

  // 3. Fetch Gate 1 Approvals for this workspace
  const { data: approvals = [] } = useQuery<Gate1Approval[]>({
    queryKey: ["gate1-approvals", workspaceId],
    queryFn: () =>
      apiGet<Gate1Approval[]>(`/workspaces/${workspaceId}/gate1/approvals`),
    enabled: !!workspaceId,
  });

  const activeApproval = approvals.find((a) => a.masking_run_id === runId);

  // Group findings by document
  const docIds = Array.from(new Set(findings.map((f) => f.document_id)));
  const currentDocId = selectedDocId || (docIds.length > 0 ? docIds[0] : null);

  // 4. Fetch Document Review Content
  const { data: reviewContent, isLoading: contentLoading } = useQuery<DocumentReview>({
    queryKey: ["document-review", workspaceId, runId, currentDocId],
    queryFn: () =>
      apiGet<DocumentReview>(
        `/workspaces/${workspaceId}/masking-runs/${runId}/documents/${currentDocId}/review`
      ),
    enabled: !!workspaceId && !!runId && !!currentDocId,
  });

  // Decision Mutation
  const decisionMutation = useMutation({
    mutationFn: ({
      findingId,
      decisionType,
    }: {
      findingId: string;
      decisionType: string;
    }) =>
      apiPost(
        `/workspaces/${workspaceId}/masking-runs/${runId}/findings/${findingId}/decisions`,
        { decision_type: decisionType }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["masking-findings", workspaceId, runId] });
      queryClient.invalidateQueries({ queryKey: ["masking-run", workspaceId, runId] });
      queryClient.invalidateQueries({
        queryKey: ["document-review", workspaceId, runId, currentDocId],
      });
    },
  });

  // Manual Finding Mutation
  const manualFindingMutation = useMutation({
    mutationFn: (payload: {
      document_id: string;
      entity_type: string;
      start_offset: number;
      end_offset: number;
    }) =>
      apiPost(
        `/workspaces/${workspaceId}/masking-runs/${runId}/findings/manual`,
        payload
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["masking-findings", workspaceId, runId] });
      queryClient.invalidateQueries({ queryKey: ["masking-run", workspaceId, runId] });
      queryClient.invalidateQueries({
        queryKey: ["document-review", workspaceId, runId, currentDocId],
      });
      setShowManualModal(false);
      setManualStart("");
      setManualEnd("");
    },
  });

  // Gate 1 Approval Mutation
  const approveMutation = useMutation({
    mutationFn: (payload: { decision_reason: string; override_coverage_reason?: string }) =>
      apiPost(
        `/workspaces/${workspaceId}/masking-runs/${runId}/gate1/approve`,
        payload
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gate1-approvals", workspaceId] });
      setShowApprovalModal(false);
    },
  });

  // Gate 1 Rejection Mutation
  const rejectMutation = useMutation({
    mutationFn: (payload: { decision_reason: string }) =>
      apiPost(
        `/workspaces/${workspaceId}/masking-runs/${runId}/gate1/reject`,
        payload
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gate1-approvals", workspaceId] });
      setShowApprovalModal(false);
    },
  });

  // Cryptographic Verification Query/Mutation
  const [verificationResult, setVerificationResult] = useState<Gate1Verification | null>(null);
  const verifyMutation = useMutation({
    mutationFn: (approvalId: string) =>
      apiPost<Gate1Verification>(
        `/workspaces/${workspaceId}/gate1/approvals/${approvalId}/verify`,
        {}
      ),
    onSuccess: (data) => {
      setVerificationResult(data);
    },
  });

  if (runLoading || !run) {
    return (
      <div className="max-w-7xl mx-auto p-12 my-6 bg-slate-900 text-slate-200 rounded-2xl border border-slate-800 shadow-xl text-center space-y-3">
        <RefreshCw className="w-6 h-6 animate-spin mx-auto text-emerald-400" />
        <p className="text-sm font-medium">Loading masking review workspace...</p>
      </div>
    );
  }

  const currentFindings = findings.filter((f) => f.document_id === currentDocId);

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6 sm:p-8 my-6 bg-slate-900 text-slate-100 rounded-2xl border border-slate-800 shadow-xl">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <button
            onClick={() => navigate("/data-protection")}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Data Protection Overview
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-emerald-400" />
              Data Protection Review: Run {run.id.slice(0, 8)}
            </h1>
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                run.extraction_coverage === "OCR_REQUIRED"
                  ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                  : "bg-slate-800 text-slate-300"
              }`}
            >
              {run.extraction_coverage}
            </span>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex items-center gap-3">
          {activeApproval ? (
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                <Fingerprint className="w-4 h-4" />
                Gate 1 Approved ({activeApproval.signature_algorithm})
              </span>
              <button
                onClick={() => verifyMutation.mutate(activeApproval.id)}
                disabled={verifyMutation.isPending}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors flex items-center gap-1"
                title="Verify cryptographic Ed25519 signature"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${verifyMutation.isPending ? "animate-spin" : ""}`} />
                Verify Signature
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowApprovalModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors shadow-lg shadow-emerald-950/50"
            >
              <CheckCircle className="w-4 h-4" />
              Gate 1 Human Approval
            </button>
          )}
        </div>
      </div>

      {/* Verification Result Banner */}
      {verificationResult && (
        <div
          className={`p-4 rounded-xl border text-xs flex items-start justify-between gap-3 ${
            verificationResult.is_valid
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
              : "bg-rose-500/10 border-rose-500/30 text-rose-300"
          }`}
        >
          <div className="flex items-start gap-2.5">
            <Fingerprint className="w-4 h-4 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">{verificationResult.verification_message}</p>
              <p className="text-[11px] opacity-80 mt-0.5 font-mono">
                Key ID: {verificationResult.signing_key_id} | Reviewer: {verificationResult.reviewer_role}
              </p>
            </div>
          </div>
          <button
            onClick={() => setVerificationResult(null)}
            className="text-slate-400 hover:text-white"
          >
            ✕
          </button>
        </div>
      )}

      {/* Document Selector Pills if multiple */}
      {docIds.length > 1 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
          <span className="text-slate-400 font-medium shrink-0">Documents:</span>
          {docIds.map((did, idx) => (
            <button
              key={did}
              onClick={() => setSelectedDocId(did)}
              className={`px-3 py-1 rounded-lg border font-mono transition-colors ${
                currentDocId === did
                  ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300"
                  : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              Doc #{idx + 1} ({did.slice(0, 6)})
            </button>
          ))}
        </div>
      )}

      {/* Side-by-Side Review Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Original Extracted Text */}
        <div className="lg:col-span-6 bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden flex flex-col h-[750px]">
          <div className="px-4 py-3 border-b border-slate-800 bg-slate-950/40 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
              <FileText className="w-4 h-4 text-sky-400" />
              <span>Original Extracted Text</span>
              {reviewContent && (
                <span className="text-slate-500 font-normal">
                  ({reviewContent.document_name})
                </span>
              )}
            </div>

            <button
              onClick={() => setShowManualModal(true)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] font-medium text-slate-200 transition-colors"
            >
              <Plus className="w-3 h-3" />
              Add Manual Span
            </button>
          </div>

          <div className="p-4 flex-1 overflow-y-auto font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap select-text bg-slate-950/20">
            {contentLoading ? (
              <div className="text-slate-500 text-center py-12">Loading document text...</div>
            ) : reviewContent?.original_text ? (
              reviewContent.original_text
            ) : (
              <div className="text-slate-500 italic text-center py-12">
                No extractable text found in this document.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Masked Output & Findings Panel */}
        <div className="lg:col-span-6 space-y-4 flex flex-col h-[750px]">
          {/* Masked Output Preview */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden flex flex-col flex-1">
            <div className="px-4 py-3 border-b border-slate-800 bg-slate-950/40 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
                <ShieldCheck className="w-4 h-4" />
                <span>Masked Output Preview</span>
              </div>
              <span className="text-[11px] text-slate-400 font-mono">
                Storage: StorageBucket.MASKED_DATASETS
              </span>
            </div>

            <div className="p-4 flex-1 overflow-y-auto font-mono text-xs text-emerald-300 leading-relaxed whitespace-pre-wrap bg-slate-950/30">
              {contentLoading ? (
                <div className="text-slate-500 text-center py-12">Loading masked preview...</div>
              ) : reviewContent?.masked_preview ? (
                reviewContent.masked_preview
              ) : (
                <div className="text-slate-500 italic text-center py-12">
                  Masked output will appear here once processed.
                </div>
              )}
            </div>
          </div>

          {/* Detections & Disposition Actions */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden h-64 flex flex-col">
            <div className="px-4 py-2.5 border-b border-slate-800 bg-slate-950/40 flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-300">
                Detected Spans ({currentFindings.length})
              </span>
              <span className="text-[11px] text-slate-500">
                Click actions to confirm or mark false positive
              </span>
            </div>

            <div className="p-3 overflow-y-auto space-y-2 flex-1 divide-y divide-slate-800/40">
              {currentFindings.length === 0 ? (
                <div className="text-center py-6 text-slate-500 text-xs">
                  Zero sensitive spans detected in this document.
                </div>
              ) : (
                currentFindings.map((finding) => (
                  <div
                    key={finding.id}
                    className="pt-2 first:pt-0 flex items-center justify-between gap-3 text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-amber-400">
                          {finding.entity_type}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          [{finding.start_offset}:{finding.end_offset}]
                        </span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                          score: {finding.detection_score}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {finding.recognizer_name} | status: {finding.status}
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() =>
                          decisionMutation.mutate({
                            findingId: finding.id,
                            decisionType: "CONFIRMED",
                          })
                        }
                        className="px-2 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-[11px] font-medium border border-emerald-500/20 transition-colors"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={() =>
                          decisionMutation.mutate({
                            findingId: finding.id,
                            decisionType: "FALSE_POSITIVE",
                          })
                        }
                        className="px-2 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-[11px] font-medium border border-rose-500/20 transition-colors"
                      >
                        False Positive
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Manual Finding Modal */}
      {showManualModal && currentDocId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-md w-full p-5 space-y-4 text-slate-100">
            <h3 className="text-sm font-semibold text-white">Add Manual Sensitive Span</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 mb-1">Entity Type</label>
                <select
                  value={manualEntity}
                  onChange={(e) => setManualEntity(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                >
                  <option value="UAE_EMIRATES_ID">UAE_EMIRATES_ID</option>
                  <option value="UAE_IBAN">UAE_IBAN</option>
                  <option value="UAE_PHONE_NUMBER">UAE_PHONE_NUMBER</option>
                  <option value="PERSON">PERSON</option>
                  <option value="EMAIL_ADDRESS">EMAIL_ADDRESS</option>
                  <option value="ORGANIZATION_INTERNAL">ORGANIZATION_INTERNAL</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-300 mb-1">Start Offset</label>
                  <input
                    type="number"
                    value={manualStart}
                    onChange={(e) => setManualStart(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1">End Offset</label>
                  <input
                    type="number"
                    value={manualEnd}
                    onChange={(e) => setManualEnd(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                    placeholder="15"
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowManualModal(false)}
                className="px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  const s = parseInt(manualStart, 10);
                  const e = parseInt(manualEnd, 10);
                  if (isNaN(s) || isNaN(e) || e <= s) return;
                  manualFindingMutation.mutate({
                    document_id: currentDocId,
                    entity_type: manualEntity,
                    start_offset: s,
                    end_offset: e,
                  });
                }}
                disabled={manualFindingMutation.isPending}
                className="px-3 py-1.5 rounded-lg text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-medium"
              >
                Save Span
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Gate 1 Approval Modal */}
      {showApprovalModal && (
        <Gate1ApprovalModal
          run={run}
          isOpen={showApprovalModal}
          onClose={() => setShowApprovalModal(false)}
          onApprove={async (data) => {
            await approveMutation.mutateAsync(data);
          }}
          onReject={async (data) => {
            await rejectMutation.mutateAsync(data);
          }}
          isSubmitting={approveMutation.isPending || rejectMutation.isPending}
        />
      )}
    </div>
  );
}
