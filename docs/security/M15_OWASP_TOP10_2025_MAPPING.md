# M15 OWASP Top 10 (2025/2026) Mapping

This document maps the **OWASP Top 10 Web Application Security Risks** against the Mizan platform architecture and implementation.

---

## 1. Summary Matrix

| OWASP Risk Category | Mizan Risk Posture | Key Mitigations Implemented | Regression Test |
| :--- | :--- | :--- | :--- |
| **A01: Broken Access Control** | **DEFENDED** | Dual-key multi-tenancy scoping, anti-enumeration 404 responses, strict role hierarchy (`OWNER` > `ADMIN` > `MEMBER` > `VIEWER`). Separation of duties on Gate 3 approvals. | `SEC-002`, `SEC-003`, `SEC-016`, `SEC-037`, `SEC-038` |
| **A02: Cryptographic Failures** | **DEFENDED** | Argon2id for password storage; Ed25519 asymmetric signing for Gates 1–3 and Site Agent commands; SHA-256 for release packages; explicit `signature_purpose` preventing cross-gate confusion. | `SEC-007`, `SEC-012`, `SEC-013`, `SEC-014`, `SEC-015`, `SEC-040` |
| **A03: Injection** | **DEFENDED** | SQLAlchemy ORM parameterized statements protect all SQL queries; Pydantic v2 schemas reject non-conforming inputs; Site Agent command execution uses strict allowlists (no arbitrary bash execution). | `SEC-004`, `SEC-022`, Penetration Rehearsal SQLI-1..4 |
| **A04: Insecure Design** | **DEFENDED** | Threat-modeled boundaries (TB-01..TB-06); three-tiered human approval gates (Gate 1, Gate 2, Gate 3); immutable release versions; golden test verification before activation. | `SEC-012`, `SEC-013`, `SEC-014`, `SEC-016`, `SEC-028`, `SEC-029` |
| **A05: Security Misconfiguration** | **DEFENDED** | Startup configuration validator in `app/core/config.py` halts boot if `DEBUG=True`, weak `secret_key`, wildcard CORS, or insecure cookies in production; API documentation hidden in prod. | `SEC-033`, `SEC-034`, `SEC-041`, `SEC-042` |
| **A06: Vulnerable and Outdated Components** | **DEFENDED** | Continuous automated dependency audits (`pip-audit`, `npm audit`). Pytest upgraded to 9.2.0 (fixing advisory PYSEC-2026-1845). Zero reported vulnerabilities. | Phase 0 verification, `M15_DEPENDENCY_AND_SBOM_REPORT.md` |
| **A07: Identification and Authentication Failures** | **DEFENDED** | Memory-hard Argon2id hashing; single-use reset and invitation tokens; brute-force rate limiting; secure session cookie flags (`HttpOnly`, `SameSite=Lax`, `Secure`). | `SEC-001`, `SEC-005`, `SEC-007`, `SEC-008`, `SEC-036` |
| **A08: Software and Data Integrity Failures** | **DEFENDED** | Model artifacts and datasets cryptographically signed with Ed25519; release manifests digest-checked; revoked versions aborted from runtime installation or rollback. | `SEC-014`, `SEC-017`, `SEC-018`, `SEC-029` |
| **A09: Security Logging and Monitoring Failures** | **DEFENDED** | Audit logging across all auth, workspace, gate, and operations actions; bounded metric label cardinality; PII scrubbing from logs and telemetry payloads. | `SEC-011`, `SEC-023`, `SEC-024`, `SEC-025` |
| **A10: Server-Side Request Forgery (SSRF)** | **DEFENDED** | Comprehensive SSRF validation on notification webhooks; blocks private IPv4/IPv6 ranges, loopback (`127.0.0.0/8`, `::1`), link-local (`169.254.0.0/16`), and DNS rebinding aliases. | `SEC-026`, `SEC-027` |
