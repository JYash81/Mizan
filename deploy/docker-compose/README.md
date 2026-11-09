# Mizan Customer Runtime & Site Agent — Docker Compose Deployment Runbook

## Overview

The Mizan Customer Runtime enables enterprise customers to host, verify, and run approved Mizan AI applications on customer-controlled infrastructure (on-premises, private cloud, or air-gapped edge servers) with zero outbound telemetry or data leakage.

### Architecture Components

1. **`mizan-customer-runtime`**: Local inference and RAG service running on port 8080.
   - Distinct probes:
     - `/api/v1/runtime/live`: Process liveness probe.
     - `/api/v1/runtime/ready`: Traffic readiness probe (verifies active slot loaded & golden tests passed).
     - `/api/v1/runtime/health`: Diagnostic health metrics.
   - OpenAI-compatible chat completions (`/api/v1/runtime/v1/chat/completions`).
   - Local grounded RAG query (`/api/v1/runtime/v1/rag/query`).
2. **`mizan-site-agent`**: Outbound-only management daemon.
   - Outbound polling: Initiates all traffic outbound to Mizan control plane.
   - Strictly zero exposed inbound ports.
   - Cryptographic verification: Validates Ed25519 signatures, nonces, and Gate 3 attestations.
   - Allowlisted typed commands only (zero arbitrary shell execution).
3. **Persistent Volumes**:
   - `mizan-model-storage`: Immutable model weights and adapter safetensors.
   - `mizan-runtime-data`: Local embeddings, SQLite data, and vector indexes.

---

## 1. Prerequisites

- Docker Engine 24.0+ and Docker Compose v2.20+
- Host machine meeting package hardware minimums (e.g. 8 GB RAM for standard 8B quantized models)
- Inbound firewall closed; only outbound HTTPS/HTTP to control plane required for Site Agent.

---

## 2. Enrollment & Installation

### Step 1: Obtain Single-Use Enrollment Token
In the Mizan Control Plane UI or API, generate an enrollment token for your registered Customer Site:
```bash
POST /api/v1/workspaces/{workspace_id}/sites/{site_id}/enrollment-token
```
Record the resulting `raw_token`.

### Step 2: Enroll Site Agent
Run the agent enrollment preflight:
```bash
docker compose run --rm mizan-site-agent python -m app.modules.runtime.site_agent_enroll \
  --token "<RAW_ENROLLMENT_TOKEN>" \
  --control-plane "https://mizan.corp.local"
```
This generates an Ed25519 keypair locally, submits the public key to the control plane, and establishes the unique cryptographic site identity.

### Step 3: Start Services
```bash
docker compose up -d
```

Verify services are up and healthy:
```bash
docker compose ps
curl http://localhost:8080/api/v1/runtime/live
curl http://localhost:8080/api/v1/runtime/ready
```

---

## 3. Air-Gapped / Disconnected Execution

The Customer Runtime is completely self-sufficient:
- When the control plane or internet is disconnected, the Site Agent gracefully pauses polling without crashing.
- The Customer Runtime continues serving local inference and RAG queries uninterrupted.
- Prompt text and corporate documents never leave customer-owned storage volumes.

---

## 4. Blue/Green Upgrades & Rollbacks

When a new application or model package is approved:
1. **Staging**: Candidate is staged into the inactive slot (Slot B).
2. **Golden Testing**: The Golden Test runner executes 8 acceptance categories against Slot B.
3. **Promotion**: Operator authorizes atomic promotion. Traffic switches to Slot B immediately; Slot A is preserved for rollback.
4. **Rollback**: If any regression is detected, the operator triggers immediate rollback to Slot A via the dashboard or API.

---

## 5. Backup & Disaster Recovery

Backup persistent model weights and database:
```bash
docker compose stop
docker run --rm -v mizan-runtime-data:/source -v $(pwd):/backup alpine tar czf /backup/mizan-data-backup.tar.gz -C /source .
docker run --rm -v mizan-model-storage:/source -v $(pwd):/backup alpine tar czf /backup/mizan-models-backup.tar.gz -C /source .
docker compose start
```
