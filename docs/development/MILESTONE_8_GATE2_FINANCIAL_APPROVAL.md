# Milestone 8: Gate 2 Financial Approval Workflow

## 1. Overview and Purpose

Gate 2 enforces financial governance in Mizan. No external or paid infrastructure workload can be scheduled or provisioned without explicit, cryptographically attested human authorization.

---

## 2. Gate 2 Lifecycle State Machine

A Gate 2 approval request traverses the following lifecycle:

```
[DRAFT] -> [PENDING_APPROVAL] 
                |--> [APPROVED] (Cryptographically signed with Ed25519)
                |       |--> [REVOKED] (Admin or approver revokes approval)
                |       |--> [EXPIRED] (7-day validity deadline passed)
                |       +--> [BLOCKED_BY_POLICY] (Enforced if allow_paid_compute=False)
                +--> [REJECTED] (Approver rejects request)
```

---

## 3. Cryptographic Binding and Attestation

### 3.1 Proposal Digest
When a proposal is submitted, a canonical JSON dictionary is constructed:
- Tenant: `organization_id`, `workspace_id`
- Workload: `title`, `purpose`, `workload_type`
- Hardware: `hardware_profile_key`, `provider_name`, `instance_type`, `region`
- Bounds: `estimated_duration_hours`, `max_duration_hours`, `max_authorized_budget`
- Costs: `estimated_compute_cost`, `estimated_storage_cost`, `estimated_total_cost`, `currency`
- Versioning: `pricing_catalog_version`

The canonical string is sorted alphabetically with compact separators (`,`, `:`) and hashed via SHA-256 to generate `proposal_digest`.

### 3.2 Ed25519 Attestation
Upon approval, an attestation payload is constructed:
- Binds `approval_id`, `proposal_id`, `proposal_digest`, `approver_id`, `approver_role_snapshot`, `max_authorized_budget`, `signed_at`.
- Signed using the platform Ed25519 private key (`signing_service.sign_payload`).
- Generates `approval_signature` (hex string) and stores `signing_key_id`.

---

## 4. Fail-Closed Security Policy Invariant

Before any workload runs, the executor calls `FinancialAuthorizationService.authorize_execution`:

1. **Existence & Expiration Check**: Verifies request exists and has not passed its `expires_at` timestamp.
2. **Revocation Check**: Verifies request has not been revoked.
3. **State Check**: Status must be `APPROVED`.
4. **Anti-Tampering Check**: Recomputes SHA-256 hash of `proposal_payload_json` and verifies exact match with `proposal_digest`.
5. **Signature Authenticity**: Verifies Ed25519 signature against `signed_payload` using `signing_key_id`.
6. **Budget Cap**: Re-checks that actual execution cost $\le \text{max\_authorized\_budget}$.
7. **MANDATORY POLICY OVERRIDE**:
   If `settings.allow_paid_compute` is `False`, and the workload involves billable or external compute:
   The request is **STRICTLY BLOCKED** with status `BLOCKED_BY_POLICY`.
   *A human signature never bypasses the global no-spend infrastructure policy.*
