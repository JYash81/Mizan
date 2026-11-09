# Invitation Security Specification

**Author:** Application Security Engineer  
**Date:** 2026-11-08  
**Verification Suite:** `backend/tests/test_invitations_api.py`  

---

## 1. Cryptographic Token Lifecycle

1. **High-Entropy Tokens:** Generated using `secrets.token_urlsafe(32)` (256 bits).
2. **Digest-Only Storage:** Raw tokens are never logged or stored in the database. Only their SHA-256 digest (`token_hash`) is indexed and persisted.
3. **Strict Email Binding:**
   When an invitation is accepted, the system validates that:
   $$\text{User.normalized\_email} == \text{Invitation.normalized\_email}$$
   If an authenticated user with a different email address attempts to consume the token, the request is rejected with `400 Bad Request` ("The authenticated user email does not match the invitation email.").
4. **Single-Use Atomic Consumption:**
   Invitation consumption executes via an atomic conditional SQL query:
   ```sql
   UPDATE invitations
   SET status = 'ACCEPTED', accepted_at = :now
   WHERE id = :id AND status = 'PENDING'
   ```
   If concurrent consumers attempt to accept the same invitation, only one transaction receives `rowcount == 1`. Subsequent attempts fail immediately.
5. **Superseding & Expiration:**
   Issuing a new invitation to the same email address automatically revokes any pending invitations in that organization. Invitations expire automatically after 7 days.
