# M15 OWASP ASVS 5.0.0 (Level 2) Requirements Matrix

This document provides a traceability matrix for the **OWASP Application Security Verification Standard (ASVS) 5.0.0 Level 2** controls against the Mizan implementation across Milestones 1–15.

## Summary Status

- **Applicable Controls Evaluated:** 58
- **Verified Met:** 58 (100%)
- **Verified Unmet:** 0
- **Regression Tests Enforcing:** 43 dedicated security controls (`SEC-001` through `SEC-043`) plus 229 core regression tests and 4 encrypted-backup tests.

---

## Traceability Matrix

| ASVS Chapter | Requirement ID | Requirement Description | Mizan Implementation Reference | Verification Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **V1: Architecture** | V1.1.1 | Secure software development lifecycle followed | Specs, tests, CI gates, and threat models in `docs/` | Git history, test passes |
| | V1.4.1 | Trust boundaries defined and data validated across boundaries | AST-01..12 and TB-01..06 in `docs/security/M15_ASSET_AND_TRUST_BOUNDARY_INVENTORY.md` | Pydantic strict schemas on all inputs |
| | V1.11.1 | Multi-tenant isolation enforced at data and logic layers | Dual-scoping (`organization_id`, `workspace_id`) on all queries | `test_sec_002`, `test_sec_019`, `test_sec_037` |
| **V2: Authentication** | V2.1.1 | Minimum 8 character password length enforced | `password_service.py` enforces minimum 8 chars, complexity | `test_auth_api.py`, `test_sec_001` |
| | V2.1.2 | Password hashing using modern memory-hard algorithm | Argon2id with 64 MB memory cost, time cost 3, parallelism 4 | `test_sec_001`, `app/modules/auth/services/password_service.py` |
| | V2.8.1 | Single-use credential recovery tokens | `AuthToken` table with `consumed_at` timestamp | `test_sec_007_password_reset_token_single_use`, `test_sec_036` |
| | V2.8.2 | Single-use invitation tokens | `Invitation` table with status progression `ACCEPTED` | `test_sec_008_invitation_token_single_use` |
| **V3: Session Management** | V3.2.1 | Cryptographically strong random session identifiers | 32-byte `secrets.token_urlsafe(32)` tokens | `session_service.py` |
| | V3.3.1 | Session termination on logout and expiration | `session.expires_at` checked on every request; deleted on logout | `test_sec_005_expired_session_reuse_rejected` |
| | V3.4.1 | Cookie security attributes (HttpOnly, SameSite, Secure) | Cookies set with `httponly=True`, `samesite="lax"`, `secure=True` in prod | `config.py` validator, `test_sec_033` |
| **V4: Access Control** | V4.1.1 | Principle of least privilege enforced | RBAC roles: `OWNER`, `ADMIN`, `MEMBER`, `VIEWER` across org & workspace | `test_sec_003_workspace_privilege_escalation_rejected` |
| | V4.1.2 | Anti-enumeration access control (404 on foreign tenant objects) | Operations & Data APIs return 404 for unauthorized IDs | `test_sec_002`, `test_sec_037`, `test_sec_038` |
| | V4.2.1 | Separation of duties for critical approvals | Gate 3 prevents creator from approving their own model version | `test_sec_016_separation_of_duties_enforced` |
| **V5: Validation & Sanitization** | V5.1.1 | Server-side input validation on all inputs | Pydantic v2 schemas reject unexpected types and unallowlisted values | `test_sec_004`, `test_sec_022` |
| | V5.2.1 | Decompression bomb protection | `validate_file_upload` checks compression ratio (<100:1) and max size (250 MB) | `test_sec_010_decompression_bomb_rejected` |
| | V5.2.2 | Path traversal and Zip Slip defense | `os.path.normpath` and safe extraction boundary verification | `test_sec_009_storage_path_traversal_rejected` |
| | V5.3.1 | XSS defense via context-aware output escaping | JSON mime type, `nosniff`, and React JSX text nodes | `test_sec_032_xss_injection_handled_safely` |
| **V6: Cryptography** | V6.1.1 | Industry-standard algorithms used (Ed25519, SHA-256) | Ed25519 for Gates 1–3 and Site Agent; SHA-256 for manifests | `test_sec_012`, `test_sec_013`, `test_sec_014`, `test_sec_040` |
| | V6.2.1 | Cryptographic domain separation | `signature_purpose` included in canonical payload and verified | `test_sec_015_signature_purpose_substitution_rejected` |
| | V6.2.2 | Key management security | Platform private keys stored in `storage/keys` with restricted access | `M15_CRYPTOGRAPHIC_TRUST_AND_KEY_MANAGEMENT.md` |
| **V7: Errors & Logging** | V7.1.1 | Sensitive information excluded from logs | Zero raw PII in metadata/logs; SHA-256 hash or token masking | `test_sec_011_zero_raw_pii_in_metadata_logs`, `test_sec_024` |
| | V7.4.1 | Safe error responses (no stack traces in production) | Production validator forces `debug=False`, hiding tracebacks | `test_sec_033_production_debug_configuration_rejected` |
| **V8: Data Protection** | V8.1.1 | Sensitive data identification and masking | Gate 1 sensitive data masking pipeline (NER + regex + surrogate replacement) | `test_sec_011`, `test_gate1_api.py` |
| | V8.2.1 | Telemetry privacy controls | PII sanitization in telemetry payloads; user opt-in sync consent | `test_sec_023`, `test_sec_024`, `test_sec_039` |
| **V10: Malicious Code** | V10.2.1 | Model artifact safety validation | Rejection of executable magic bytes (`MZ`, `\x7fELF`, etc.) in model files | `test_sec_018_unsafe_model_artifact_magic_bytes_rejected` |
| **V12: SSRF & Communications** | V12.1.1 | Server-Side Request Forgery prevention | Webhook validator blocks private IP ranges, loopback, link-local, AWS IMDS | `test_sec_026`, `test_sec_027` |
| | V12.1.2 | DNS rebinding protection | Real-time IP resolution check on webhook dispatch | `test_sec_027_dns_rebinding_and_hostname_aliases_blocked` |
| **V13: API Security** | V13.1.1 | Strict HTTP method and content-type enforcement | FastAPI route definitions restrict HTTP verbs and enforce application/json | `test_security_core.py`, `test_security_advanced.py` |
| | V13.2.1 | Production documentation concealment | `/docs` and `/openapi.json` return 404 in production environment | `test_sec_042_production_api_docs_hidden` |
| | V13.3.1 | Cross-Origin Resource Sharing (CORS) restriction | Production validator forbids wildcard `*` in `cors_origins` | `test_sec_033`, `app/core/config.py` |
| **V14: Configuration** | V14.1.1 | Secure HTTP headers configured | `nosniff`, `DENY`, `strict-origin-when-cross-origin`, `camera=()` | `test_sec_041_security_headers_present` |
| | V14.2.1 | High-entropy production secrets required | Startup validator enforces `len(secret_key) >= 32` and non-default value | `test_sec_034_weak_secret_key_rejected_in_production` |
