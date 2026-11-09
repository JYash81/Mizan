# Milestone 2 Block 1 — Step 4 Report

**Component:** Secure One-Time Token Service (`token_service.py`)  
**Date:** 2026-11-08  
**Status:** IMPLEMENTED and UNIT_TESTED  

---

## 1. Implemented Capabilities

- **High-Entropy Token Issuance:** Tokens are generated using `secrets.token_urlsafe(32)` providing 256 bits of cryptographic entropy.
- **Digest-Only Persistence:** Raw tokens are never logged, never stored in the database, and hidden from string representation (`repr=False`). Only their SHA-256 digests (`token_hash`) are persisted.
- **Configurable Lifespans:** Default token lifetimes are centralized in Pydantic `Settings`:
  - `email_verification_token_hours`: 24 hours
  - `password_reset_token_minutes`: 15 minutes
  - Per-issuance override supported via `expires_in_minutes`.
- **Purpose Scoping:** Enforces strict purpose isolation between `EMAIL_VERIFICATION` and `PASSWORD_RESET`. A token generated for one purpose can never be validated or consumed for another.
- **Atomic Single-Use Consumption:** Token consumption executes via an atomic conditional SQL `UPDATE` statement (`WHERE id = :id AND consumed_at IS NULL AND revoked_at IS NULL AND expires_at > :now`). Race conditions and replay attacks are impossible.
- **Automatic Superseding & Revocation:** Issuing a new token for an active user and purpose automatically revokes any previous unconsumed tokens. Explicit single-token and user-wide revocation are provided.
- **Retention & Cleanup:** `cleanup_expired_tokens` safely purges records older than `token_retention_days` (default: 30 days).

---

## 2. Verification Evidence

- **Unit & Security Tests:** `backend/tests/test_token_service.py` added with 10 comprehensive test cases covering:
  - Cryptographic randomness and SHA-256 digest validation.
  - Secret protection in `repr`.
  - Default and custom expiration windows.
  - Read-only validation rejection on invalid string, purpose mismatch, expiration, and revocation.
  - Atomic single-use consumption guarantee (second consumption attempt fails).
  - Preemption of superseded active tokens upon new issuance.
  - User-wide revocation filtered by purpose.
  - Foreign key and non-existent user handling.
  - Retention cleanup.
- **Linter Status:** `ruff check .` and `ruff format .` clean with 0 warnings/errors.
- **Test Suite Result:** `pytest` — 32 passed (1 upstream FastAPI/Starlette deprecation warning).

---

## 3. Deferred / Next Immediate Step

- Step 5: Implement authentication dependencies (`get_current_principal`, `get_current_active_user`, `require_csrf`) and centralized audit service (`audit_service.py`).
- HTTP API endpoints for registration, login, logout, verification, and recovery remain deferred to subsequent steps.
