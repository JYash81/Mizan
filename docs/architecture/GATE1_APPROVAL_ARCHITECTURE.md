# Mizan Gate 1 Human Approval Architecture & Cryptographic Attestation

**Authoritative Baseline:** Mizan High-Level Design (`docs/reference/mizan_hld.png`)  
**Milestone:** 4 — Data Protection, Masking & Gate 1 Human Approval  
**Status:** ACTIVE  
**Updated:** 2026-11-08  

---

## 1. Gate 1 in the Mizan Workflow

In the authoritative 12-step Mizan architecture, **GATE 1 — A person approves the masked sample** is the first mandatory human-in-the-loop checkpoint:

```
[Step 1: Describe Need]
       │
       ▼
[Step 2: Upload Files to Workshop]
       │
       ▼
[Step 3: Mask Personal Data]
       │
       ▼
 ╔══════════════════════════════════════════════════════════════════════╗
 ║                GATE 1 — HUMAN APPROVAL ATTESTATION                   ║
 ║  Designated DPO or AI Lead inspects detections, reviews unmasked    ║
 ║  snippets, adjusts findings, and executes a cryptographically       ║
 ║  signed approval attestation.                                       ║
 ╚══════════════════════════════════════════════════════════════════════╝
       │
       ▼ Approved Masked Dataset Released
[Step 4: Build the Exam & Evaluation Benchmark]
       │
       ▼
[Step 5 & 6: Shortlist & Run Experiments (Gate 2)]
```

---

## 2. Gate 1 Approval Prerequisites

A dataset version cannot receive Gate 1 approval until all of the following conditions are strictly satisfied:
1. **Source Dataset Version Finalized:** The source dataset version must be frozen in `READY` status with an immutable SHA-256 digest.
2. **Extraction Coverage Verified:** Zero documents in `OCR_REQUIRED` or `EXTRACTION_FAILED` status without an explicit authorized exclusion reason.
3. **Completed Masking Run:** A valid `MaskingRun` exists in `COMPLETED` status.
4. **Unresolved Findings Handled:** All detected findings have a defined disposition (`CONFIRMED`, `FALSE_POSITIVE`, or accepted under policy).
5. **Masked Output Exists & Matches Digest:** The physical masked artifact in `StorageBucket.MASKED_DATASETS` is verified against the recorded `masked_output_digest`.
6. **Authorized Reviewer:** The reviewer must possess the `workspace.datasets.masking.approve` permission.

---

## 3. Cryptographic Approval Attestation (Ed25519)

### Platform-Signed Attestation
When an authorized human approves a dataset version in the Web Console:
- The human reviewer makes the policy and data-protection decision.
- The Mizan platform generates an immutable **Approval Attestation** cryptographically signed using an **Ed25519** digital private key.
- The attestation permanently records:
  - Reviewer's authenticated user ID.
  - Reviewer's role snapshot at the moment of approval.
  - Organization ID and Workspace ID.
  - Dataset ID and Dataset Version ID.
  - Exact source dataset content digest.
  - Exact masked output artifact digest.
  - Findings digest.
  - Review reason and UTC timestamp.

### Canonical JSON Payload Specification
To guarantee deterministic cryptographic signature verification across platforms, the signed payload is serialized using strict canonical JSON formatting:
```json
{
  "approval_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "canonical_version": "1.0",
  "dataset_id": "e4b2d56a-1123-4567-89ab-cdef01234567",
  "decision": "APPROVED",
  "decision_reason": "All UAE Emirates IDs and IBANs verified and masked.",
  "findings_digest": "3c4d5e6f...",
  "masked_output_digest": "7a8b9c0d...",
  "masking_run_id": "m1n2o3p4...",
  "organization_id": "o1p2q3r4...",
  "reviewed_at": "2026-11-08T18:30:00Z",
  "reviewer_role_snapshot": "OWNER",
  "reviewer_user_id": "u1v2w3x4...",
  "schema_version": "2026-11-08",
  "source_dataset_digest": "1a2b3c4d...",
  "source_dataset_version_id": "v1w2x3y4...",
  "workspace_id": "w1x2y3z4..."
}
```
* **Serialization Invariants:**
  - Alphabetically sorted dictionary keys.
  - Compact separators (`","` and `":"`, no unnecessary whitespace).
  - Explicit UTF-8 encoding.
  - ISO 8601 UTC timestamps ending in `"Z"`.

---

## 4. Verification and Invalidation

### Verification Engine (`verify_gate1_approval`)
Any downstream subsystem (e.g. Exam Builder or Experiment Orchestrator) validates an approval through `verify_gate1_approval()`:
1. Reconstructs the canonical JSON payload from the database record.
2. Retrieves the registered Ed25519 public key corresponding to `signing_key_id`.
3. Verifies the cryptographic digital signature against the canonical bytes.
4. Reads the physical masked artifact from `StorageBucket.MASKED_DATASETS` and verifies its SHA-256 digest matches `masked_output_digest`.
5. Confirms `approval_status == 'APPROVED'`.

### Tamper Resistance & Invalidation Triggers
An approval is immediately rejected or invalidated if:
* The source dataset version is modified or deleted.
* The masked artifact in storage is altered or replaced.
* Any field in the canonical payload is tampered with (signature verification fails).
* The signing key is revoked.
* An authorized reviewer explicitly revokes the approval (`INVALIDATED`).

---

## 5. Reusable Centralized Guard (`require_gate1_approval`)

Future milestones (Milestone 5 RAG and Milestone 7 Experiments) invoke `require_gate1_approval(workspace_id, dataset_version_id)`:
* **Fail-Closed Principle:** If Gate 1 approval is missing, unverified, or tampered, the operation aborts with HTTP 403 Forbidden.
* **Audit Trail:** Every verification attempt and failure is logged in the immutable audit trail.
