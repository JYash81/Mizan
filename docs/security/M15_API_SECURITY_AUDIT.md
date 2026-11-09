# M15 API Security Audit (OWASP API Security Top 10: 2023)

## 1. Scope & Audit Target

This audit covers all REST API endpoints defined under `/api/v1` across Mizan modules:
- Authentication & Identity (`/api/v1/auth`)
- Organizations & Workspaces (`/api/v1/organizations`, `/api/v1/workspaces`, `/api/v1/invitations`)
- Datasets & Documents (`/api/v1/datasets`, `/api/v1/documents`)
- Sensitive Data Masking & Gate 1 (`/api/v1/masking`, `/api/v1/gate1`)
- AI Providers & RAG (`/api/v1/rag`)
- Evaluation Engine (`/api/v1/evaluations`)
- Experiment Engine (`/api/v1/experiments`)
- Hardware & Gate 2 (`/api/v1/hardware`, `/api/v1/gate2`, `/api/v1/cost`)
- Recommendations Engine (`/api/v1/recommendations`)
- Model Building (`/api/v1/model-building`)
- Artifact Registry & Gate 3 (`/api/v1/artifact-registry`, `/api/v1/gate3`)
- Catalogs & Zoos (`/api/v1/model-zoo`, `/api/v1/app-zoo`)
- Customer Runtime & Site Agent (`/api/v1/customer-runtime`, `/api/v1/site-agent`, `/api/v1/sites`)
- Operations, Telemetry & Rollback (`/api/v1/ops`)
- System (`/api/v1/health`, `/api/v1/ready`, `/api/v1/version`)

---

## 2. API Top 10 Verification Matrix

| OWASP API Risk | Posture | Technical Controls | Test Evidence |
| :--- | :--- | :--- | :--- |
| **API1: Broken Object Level Authorization (BOLA)** | **PASS** | Every resource query filters by both user membership and workspace ID. Accessing another tenant's resource yields 404 (anti-enumeration). | `SEC-002`, `SEC-037`, `SEC-038` |
| **API2: Broken Authentication** | **PASS** | Secure session cookies, Argon2id password hashing, constant-time comparisons, single-use reset/invite tokens. Unauthenticated requests return 401. | `SEC-001`, `SEC-005`, `SEC-007`, `SEC-031` |
| **API3: Broken Object Property Level Authorization** | **PASS** | Pydantic response models explicitly define serializable fields; sensitive database columns (`password_hash`, `session_token`) are never exposed in responses. `model_config = ConfigDict(extra="ignore")` discards client-supplied unauthorized fields. | `SEC-004_mass_assignment_fields_ignored_or_rejected` |
| **API4: Unrestricted Resource Consumption** | **PASS** | File upload size limits (25 MB raw, 250 MB decompressed), zip compression ratio checks (< 100:1), Prometheus label cardinality controls, pagination on all list endpoints (max 100 or 500 items). | `SEC-010`, `SEC-025` |
| **API5: Broken Function Level Authorization (BFLA)** | **PASS** | Hierarchical permissions verified via `has_workspace_permission` and `has_org_permission`. Mutating actions require `ADMIN` or `OWNER` roles. | `SEC-003`, `SEC-038`, `SEC-039` |
| **API6: Unrestricted Access to Sensitive Business Flows** | **PASS** | Model releases require human approval in Gate 3 with cryptographic signing. Creator cannot approve their own release. Release packages cannot be downloaded if status is REVOKED. | `SEC-016`, `SEC-017` |
| **API7: Server Side Request Forgery (SSRF)** | **PASS** | Outbound notification webhooks pass through `validate_webhook_url`, strictly rejecting RFC 1918 private subnets, loopback, link-local, and AWS IMDS. | `SEC-026`, `SEC-027` |
| **API8: Security Misconfiguration** | **PASS** | Production startup validator halts if debug is true, weak secrets, or wildcard CORS. Global middleware adds `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`. | `SEC-033`, `SEC-034`, `SEC-041`, `SEC-042` |
| **API9: Improper Inventory Management** | **PASS** | Deprecated endpoints are explicitly sunset; Swagger `/docs` and OpenAPI JSON are hidden in production to prevent discovery by unauthorized actors. | `SEC-042_production_api_docs_hidden` |
| **API10: Unsafe Consumption of APIs** | **PASS** | AI provider responses and external model metadata are validated against strict Pydantic schemas before persistence; Site Agent commands use cryptographic signatures and UUIDv4 nonces. | `SEC-020`, `SEC-021`, `SEC-022` |
