# Milestone 13 — Site Agent & Cryptographic Protocol Architecture

## 1. Zero-Trust Outbound Polling Model

Traditional management agents that open inbound ports on customer networks introduce serious firewall, ingress, and security risks.

The **Mizan Site Agent** operates on a strict **zero-trust, outbound-only** model:
- **No Inbound Ports**: The Site Agent container exposes zero listening ports (`EXPOSE` is completely omitted).
- **Outbound Heartbeat**: The agent polls the central control plane via HTTPS at regular intervals (default: 30 seconds).
- **Graceful Offline Tolerance**: If the control plane or WAN connection drops, the agent logs a warning and waits. Local runtime execution is completely unaffected.

---

## 2. Enrollment Lifecycle & Cryptographic Identity

### Step 1: High-Entropy Token Generation
1. Workspace Administrator generates an enrollment token in the control plane:
   - Token contains 256 bits of cryptographically secure random entropy (`secrets.token_urlsafe(32)`).
   - Only the SHA-256 digest of the raw token is persisted in the database (`SiteEnrollmentToken`).
   - The token has a strict expiration window (default: 60 minutes) and is single-use.

### Step 2: Agent Enrollment
1. The Site Agent generates an Ed25519 keypair locally on customer premises. The private key never leaves the customer environment.
2. The agent submits an enrollment payload:
   ```json
   {
     "token": "<RAW_ENROLLMENT_TOKEN>",
     "public_key_pem": "-----BEGIN PUBLIC KEY-----\n...",
     "key_id": "agent-key-01",
     "protocol_version": "1.0.0",
     "platform_info": { "memory_mb": 16384, "arch": "x86_64" }
   }
   ```
3. Control Plane:
   - Hashes `token` and verifies match against `SiteEnrollmentToken`.
   - Validates `token.consumed_at is None` and `token.expires_at >= now`.
   - Immediately sets `token.consumed_at = now`, permanently invalidating the token.
   - Computes SHA-256 fingerprint of the agent's public key.
   - Enrolls `SiteAgentIdentity` and sets `CustomerSite.status = ACTIVE`.

---

## 3. Cryptographically Signed Commands & Replay Protection

Control plane commands dispatched to a customer site agent are signed with Ed25519 using a dedicated signature purpose:
- **Purpose**: `SITE_AGENT_COMMAND`
- **Allowlisted Command Types**:
  1. `FETCH_APPROVED_PACKAGE`
  2. `VERIFY_PACKAGE`
  3. `STAGE_PACKAGE`
  4. `REPORT_RUNTIME_STATUS`
  5. `REQUEST_GOLDEN_TEST`
  6. `SYNC_APPROVED_METADATA`

### Anti-Tamper & Anti-Replay Invariants
Every dispatched command contains:
- `command_id`: Unique identifier.
- `customer_site_id`: Bound to the specific customer site.
- `payload_digest`: SHA-256 hash of canonical compact payload.
- `nonce`: 256-bit unique cryptographic nonce (`secrets.token_hex(32)`).
- `expires_at`: Expiration timestamp (e.g. 2 hours).
- `signature`: Ed25519 digital signature over the canonical envelope.

### Verification at Consumption
When the Site Agent consumes and acknowledges a command:
1. Verifies command is unexpired (`expires_at >= now`). Expired commands raise `ExpiredCommandError` (HTTP 410).
2. Verifies status is not already `CONSUMED`. Replayed nonces raise `ReplayedNonceError` (HTTP 409).
3. Verifies Ed25519 digital signature using the control plane's public key.
4. Executes the hardcoded typed handler. **Strict Invariant: Zero arbitrary shell execution (`subprocess`, `os.system`, `shutil`) is ever invoked.**
5. Records status as `CONSUMED`.
