# M15 Security Findings Register

This register documents all vulnerabilities, weaknesses, and security architecture gaps identified, investigated, and remediated during **Milestone 15**.

## Findings Summary

- **Total Findings Registered:** 6
- **Remediated & Verified:** 6 (100%)
- **Open / Deferred (Acceptable Risk):** 0
- **Preserved Operational Blockers:** 1 (`M2.B1 Step 3 — Remote MySQL Concurrency Verification: BLOCKED`)

---

## Findings Matrix

| Finding ID | Title | Severity | Status | Remediated In | Verified By |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-FIND-01** | `hashlib.sha1` flagged by Bandit (B324) in Model Source Catalog | Medium | **RESOLVED** | `backend/app/modules/model_building/model_source_catalog.py` (line 203) | Bandit scan (0 Medium/High issues) |
| **SEC-FIND-02** | Production startup allowed `DEBUG=True` and weak secret key | High | **RESOLVED** | `@model_validator(mode="after")` in `backend/app/core/config.py` | `test_sec_033`, `test_sec_034` |
| **SEC-FIND-03** | Missing HTTP Security Headers on API responses | Medium | **RESOLVED** | Global security middleware in `backend/app/main.py` | `test_sec_041_security_headers_present` |
| **SEC-FIND-04** | Swagger UI and OpenAPI documentation exposed in production | Medium | **RESOLVED** | Route conditioning in `backend/app/main.py` | `test_sec_042_production_api_docs_hidden` |
| **SEC-FIND-05** | Operations API lacked workspace tenant access verification and CSRF | High | **RESOLVED** | `_verify_workspace_ops_access` & `require_csrf` in `operations.py` | `test_sec_037`, `test_sec_038`, `test_sec_039` |
| **SEC-FIND-06** | Pytest dependency vulnerability advisory PYSEC-2026-1845 | Low | **RESOLVED** | Upgraded `pytest` to 9.2.0 in `backend/pyproject.toml` | `pip-audit` (0 vulnerabilities found) |

---

## Detailed Remediation Notes

### SEC-FIND-01: Bandit B324 Remediation
- **Description:** Bandit reported `B324: Use of weak MD5 or SHA1 hash for security` on `hashlib.sha1(repo_id.encode()).hexdigest()`.
- **Root Cause:** SHA-1 was used solely as a deterministic filesystem cache path discriminator, not for cryptographic authentication.
- **Fix:** Added `usedforsecurity=False` to `hashlib.sha1(..., usedforsecurity=False)`.
- **Evidence:** Bandit scan output now passes cleanly with 0 Medium or High issues.

### SEC-FIND-02: Production Startup Validation
- **Description:** Previous configurations permitted starting the FastAPI application with `APP_ENV=production` while retaining `DEBUG=True`, weak default secret keys (`replace-with-local-secret`), or wildcard CORS.
- **Fix:** Implemented automated Pydantic model validation on `Settings` that raises `ValueError` during boot if production security criteria are violated.
- **Evidence:** Tested and verified via `test_sec_033` and `test_sec_034`.

### SEC-FIND-03 & 04: Headers & Documentation
- **Description:** Standard headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`) were not globally injected, and `/docs` was accessible in production.
- **Fix:** Added starlette middleware injecting hardened headers and set `docs_url=None`, `redoc_url=None`, `openapi_url=None` when `app_env == "production"`.
- **Evidence:** Tested and verified via `test_sec_041` and `test_sec_042`.

### SEC-FIND-05: Operations Tenant Isolation
- **Description:** Incidents and rollback endpoints did not verify caller workspace membership with `has_workspace_permission`, allowing potential IDOR cross-tenant access.
- **Fix:** Added `_verify_workspace_ops_access(db, workspace_id, current_user, required_permission)` checking organization and workspace roles, returning 404 for foreign tenants. Added `require_csrf` to mutating routes.
- **Evidence:** Tested and verified via `test_sec_037`, `test_sec_038`, and `test_sec_039`.
