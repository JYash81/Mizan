import { useState } from "react";
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Lock,
  KeyRound,
  RotateCcw,
  UserCheck,
} from "lucide-react";
import type { ModelVersion } from "../types";
import { submitGate3Decision, revokeModelRelease, verifyGate3Signature } from "../api";

interface Gate3ReviewCardProps {
  version: ModelVersion;
  workspaceId: string;
  currentUserId: string;
  onRefresh: () => void;
}

export function Gate3ReviewCard({
  version,
  workspaceId,
  currentUserId,
  onRefresh,
}: Gate3ReviewCardProps) {
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [signatureVerified, setSignatureVerified] = useState<boolean | null>(null);

  const approval = version.gate3_approval;
  const isCreator = currentUserId === version.created_by;
  const isPending = version.status === "PENDING_REVIEW";
  const isApproved = version.status === "APPROVED";
  const isRevoked = version.status === "REVOKED";
  const isRejected = version.status === "REJECTED";

  const handleDecision = async (decision: "APPROVED" | "REJECTED") => {
    setIsSubmitting(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await submitGate3Decision(workspaceId, version.id, {
        decision,
        decision_reason: reason || undefined,
        enforce_separation_of_duties: true,
      });
      setSuccessMsg(`Gate 3 Decision submitted: ${decision}`);
      onRefresh();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit Gate 3 decision";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevoke = async () => {
    const revReason = prompt("Enter the required compliance reason for revoking this release:");
    if (!revReason || revReason.trim().length < 5) {
      alert("Revocation reason must be at least 5 characters.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await revokeModelRelease(workspaceId, version.id, {
        revocation_reason: revReason,
      });
      setSuccessMsg("Release successfully revoked.");
      onRefresh();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to revoke release";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifySig = async () => {
    try {
      const res = await verifyGate3Signature(workspaceId, version.id);
      setSignatureVerified(res.is_valid);
    } catch {
      setSignatureVerified(false);
    }
  };

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h3 className="text-lg font-semibold tracking-tight text-foreground flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-500" />
            Gate 3 Human Release Approval Centre
          </h3>
          <p className="text-sm text-muted-foreground mt-0.5">
            Multi-stakeholder authorization, separation of duties enforcement, and Ed25519 digital attestation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isApproved && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Gate 3 Approved & Immutable
            </span>
          )}
          {isRevoked && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
              <XCircle className="w-3.5 h-3.5" />
              Release Revoked
            </span>
          )}
          {isPending && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
              <AlertTriangle className="w-3.5 h-3.5" />
              Pending Human Review
            </span>
          )}
          {isRejected && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
              <XCircle className="w-3.5 h-3.5" />
              Gate 3 Rejected
            </span>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-600 dark:text-red-400 font-medium">
          {error}
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
          {successMsg}
        </div>
      )}

      {/* Separation of Duties Notice */}
      {isPending && isCreator && (
        <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-700 dark:text-amber-300 space-y-1">
            <span className="font-semibold block">Separation of Duties Active:</span>
            You are recorded as the creator of this release candidate ({version.version_tag}). Under Mizan governance policy, an independent Workspace Owner or Admin must perform Gate 3 review and sign the attestation.
          </div>
        </div>
      )}

      {/* Review Checklist */}
      <div className="space-y-3">
        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Approval Preconditions Checklist
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div className="p-3 rounded-lg border border-border bg-secondary/30 flex items-center justify-between">
            <span className="text-foreground">1. Finalized Release Manifest</span>
            {version.release_manifest_digest ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            ) : (
              <XCircle className="w-4 h-4 text-red-500" />
            )}
          </div>
          <div className="p-3 rounded-lg border border-border bg-secondary/30 flex items-center justify-between">
            <span className="text-foreground">2. At Least 1 Verified Artifact</span>
            {(version.artifacts?.length || 0) > 0 ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            ) : (
              <XCircle className="w-4 h-4 text-red-500" />
            )}
          </div>
          <div className="p-3 rounded-lg border border-border bg-secondary/30 flex items-center justify-between">
            <span className="text-foreground">3. 5-Pillar Provenance Pass</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="p-3 rounded-lg border border-border bg-secondary/30 flex items-center justify-between">
            <span className="text-foreground">4. Ed25519 Signing Infrastructure</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
        </div>
      </div>

      {/* Existing Approval Details (if Approved or Revoked) */}
      {approval && (
        <div className="p-4 rounded-lg bg-secondary/40 border border-border space-y-3 text-xs">
          <div className="font-semibold text-foreground flex items-center gap-2">
            <KeyRound className="w-4 h-4 text-primary" />
            Cryptographic Ed25519 Attestation Record
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-muted-foreground">
            <div>
              <span className="font-medium text-foreground">Reviewer:</span> {approval.reviewer_user_id} ({approval.reviewer_role_snapshot})
            </div>
            <div>
              <span className="font-medium text-foreground">Reviewed At:</span> {new Date(approval.reviewed_at).toLocaleString()}
            </div>
            <div>
              <span className="font-medium text-foreground">Signing Key ID:</span> <code>{approval.signing_key_id}</code>
            </div>
            <div>
              <span className="font-medium text-foreground">Signature Purpose:</span> <code>{approval.signature_purpose}</code>
            </div>
            <div className="sm:col-span-2">
              <span className="font-medium text-foreground">Digital Signature:</span>{" "}
              <code className="text-xs font-mono break-all">{approval.approval_signature}</code>
            </div>
            {approval.decision_reason && (
              <div className="sm:col-span-2">
                <span className="font-medium text-foreground">Reviewer Reason:</span> {approval.decision_reason}
              </div>
            )}
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleVerifySig}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-secondary text-foreground border border-border text-xs font-medium hover:bg-secondary/80 transition-colors"
            >
              <UserCheck className="w-3.5 h-3.5" />
              Verify Digital Signature
            </button>
            {signatureVerified !== null && (
              <span
                className={`text-xs font-medium flex items-center gap-1 ${
                  signatureVerified ? "text-emerald-500" : "text-red-500"
                }`}
              >
                {signatureVerified ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Signature Cryptographically Valid
                  </>
                ) : (
                  <>
                    <XCircle className="w-3.5 h-3.5" />
                    Signature Verification Failed
                  </>
                )}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Revocation Details (if revoked) */}
      {version.revocations && version.revocations.length > 0 && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 space-y-2 text-xs">
          <div className="font-semibold text-red-600 dark:text-red-400 flex items-center gap-2">
            <RotateCcw className="w-4 h-4" />
            Revocation Audit Record
          </div>
          {version.revocations.map((rev) => (
            <div key={rev.id} className="text-red-700 dark:text-red-300 space-y-0.5">
              <div>
                <span className="font-medium">Revoked By:</span> {rev.revoked_by_user_id} ({rev.revoked_by_role_snapshot}) on{" "}
                {new Date(rev.revoked_at).toLocaleString()}
              </div>
              <div>
                <span className="font-medium">Reason:</span> {rev.revocation_reason}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Actions Section */}
      {isPending && (
        <div className="space-y-4 pt-2 border-t border-border">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">
              Reviewer Notes / Compliance Justification
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Record governance rationale, compliance checks, or rejection grounds..."
              className="w-full h-20 p-3 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary outline-none"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleDecision("APPROVED")}
              disabled={isSubmitting || (isCreator && true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
            >
              <CheckCircle2 className="w-4 h-4" />
              Sign & Approve Gate 3 Release
            </button>
            <button
              onClick={() => handleDecision("REJECTED")}
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600/10 text-red-600 dark:text-red-400 border border-red-500/20 text-xs font-semibold hover:bg-red-500/20 transition-colors disabled:opacity-50"
            >
              <XCircle className="w-4 h-4" />
              Reject Release Candidate
            </button>
          </div>
        </div>
      )}

      {isApproved && (
        <div className="pt-2 border-t border-border flex items-center justify-between">
          <div className="text-xs text-muted-foreground flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-emerald-500" />
            Release is locked and immutable for production use.
          </div>
          <button
            onClick={handleRevoke}
            disabled={isSubmitting}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 text-xs font-medium hover:bg-red-500/20 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Revoke Release...
          </button>
        </div>
      )}
    </div>
  );
}
