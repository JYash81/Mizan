# M15 — Comprehensive System Threat Model (STRIDE Methodology)

**Audit Date:** 2026-11-09  
**Methodology:** STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)  
**Standard:** OWASP Threat Modeling Guide / NIST SP 800-218  

---

## 1. Executive Summary & Threat Landscape

Mizan operates as an enterprise AI platform handling sensitive corporate documents, PII detection, model fine-tuning recipes, and customer runtime inference. The threat model evaluates threats against all six STRIDE categories across the control plane, customer data plane, and on-premise customer runtime.

---

## 2. STRIDE Threat Analysis Matrix

| Threat ID | Category | Target Asset / Boundary | Threat Scenario | Impact | Likelihood | Risk Rating | Architectural Mitigation & Verification |
|---|---|---|---|---|---|---|---|
| **THR-01** | Spoofing | Identity / Sessions | Adversary steals or predicts session cookie to impersonate an organization admin. | High | Low | **MEDIUM** | 256-bit cryptographically random session IDs, Argon2id password hashing, HttpOnly & SameSite=Lax/Strict cookie flags, session inactivity timeout (30 min). |
| **THR-02** | Spoofing | Site Agent Identity | Malicious edge agent connects using a forged identity to access release packages. | Critical | Low | **HIGH** | Single-use high-entropy enrollment tokens (SHA-256 digest), Ed25519 public key pinning per customer site, outbound-only authentication. |
| **THR-03** | Tampering | Dataset / Gate 1 | Adversary modifies dataset after PII masking to inject unmasked data into model training. | Critical | Low | **HIGH** | Gate 1 signs the exact SHA-256 canonical digest of the masked dataset. Any change invalidates the cryptographic signature (`FAIL_CLOSED`). |
| **THR-04** | Tampering | Release Manifest / Gate 3 | Adversary alters model weights or configuration in a release manifest. | Critical | Low | **HIGH** | Release manifest computes SHA-256 of all artifacts and is signed by Gate 3 human approvers with dedicated Ed25519 purpose `GATE3_RELEASE_APPROVAL`. |
| **THR-05** | Tampering | Site Agent Commands | Attacker intercepts or modifies commands dispatched to on-premise runtime. | Critical | Low | **HIGH** | All commands are signed with `SITE_AGENT_COMMAND` signature purpose, carry a unique single-use nonce, and expire after 300 seconds. |
| **THR-06** | Repudiation | Governance Approvals | Approver claims they did not authorize an external export or model deployment. | High | Low | **MEDIUM** | Immutable audit records in `audit_events`, Ed25519 digital signatures with timestamp and role snapshot, separation of duties. |
| **THR-07** | Information Disclosure | Multi-Tenant Data | Tenant A attempts to access Tenant B documents, datasets, or evaluation results. | Critical | Medium | **CRITICAL** | Mandatory tenant isolation in database queries (`organization_id` & `workspace_id`); 404 anti-enumeration responses prevent ID discovery. |
| **THR-08** | Information Disclosure | Telemetry / Metrics | Confidential prompts or customer documents leak into Prometheus `/metrics` or operational event logs. | High | Medium | **HIGH** | `telemetry_privacy.py` sanitizes payloads, drops forbidden keys (`prompt`, `messages`, `api_key`), redacts tokens/emails, restricts Prometheus label cardinality. |
| **THR-09** | Information Disclosure | Vector Database (Qdrant) | User retrieves vector embeddings belonging to another workspace. | High | Low | **HIGH** | Strict metadata payload filtering on `workspace_id` in all similarity searches; isolated collection names. |
| **THR-10** | Denial of Service | Document Ingestion | Adversary uploads a ZIP decompression bomb or deeply nested archive. | High | Medium | **HIGH** | Maximum upload size bounded to 25 MB; 100:1 maximum decompression ratio enforced; pure-Python bounded parsers reject malformed files safely. |
| **THR-11** | Denial of Service | Evaluation Engine | Adversary launches unbounded combinatorial experiment trials to exhaust CPU/memory. | Medium | Medium | **MEDIUM** | Strict trial bounds (min 3, max 9 unique trials); sequential execution runner (concurrency = 1); timeout bounds on LLM provider calls. |
| **THR-12** | Elevation of Privilege | RBAC Roles | Workspace Member attempts to trigger Gate 3 approval or modify rollback policy. | Critical | Low | **HIGH** | Declarative RBAC permission checks (`require_permission(WorkspacePermission.OPERATIONS_MANAGE)`); server-side enforcement on all state-mutating endpoints. |
| **THR-13** | Elevation of Privilege | Separation of Duties | Developer who staged a model artifact attempts to approve Gate 3 release. | High | Low | **HIGH** | `SeparationOfDutiesValidator` verifies `creator_id != approver_id`; multi-stakeholder role requirements enforced. |
| **THR-14** | Elevation of Privilege | Webhook SSRF | Operator configures a malicious webhook targeting AWS metadata service (`169.254.169.254`) or localhost. | Critical | Medium | **CRITICAL** | `NotificationRouter` validates target IP, blocking 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16; 0 redirects allowed. |
| **THR-15** | Tampering | Automated Rollback | Flapping system restores a revoked, vulnerable model version during incident recovery. | Critical | Low | **HIGH** | `RollbackEligibilityValidator` verifies target slot has active Gate 3 signature, checks for active `Gate3Revocation` (strictly aborts if revoked), re-runs golden tests. |

---

## 3. High-Priority Threat Remediation Focus

The following threats are designated as **Top Priority** for Milestone 15 verification and regression testing:
1. **THR-07 (Cross-Tenant Data Exposure)**: Verified via automated cross-tenant security test scenarios across all M1–M14 endpoints.
2. **THR-14 (Webhook SSRF Egress Exploitation)**: Verified via comprehensive IP filter and synthetic DNS test cases.
3. **THR-03, THR-04, THR-13 (Governance Gate & Separation of Duties Bypasses)**: Verified via cryptographic tampering and self-approval test cases.
4. **THR-08 (Telemetry Privacy Leakage)**: Verified via multiline regex and sensitive payload injection tests.
5. **THR-15 (Revoked Model Rollback Exploitation)**: Verified via post-revocation slot transition tests.
