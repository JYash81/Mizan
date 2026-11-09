# Architecture decision records

## ADR-001: Modular monolith for the foundation

FastAPI is the single business API. Independent microservices, queues, Docker, and GPU workers are deferred because they add operational cost without enabling a Milestone 1 requirement.

## ADR-002: SQLite locally, MySQL/MariaDB in production

SQLAlchemy 2 and Alembic isolate the application from the database vendor. SQLite offers zero-service local development; PyMySQL enables a Hostinger-compatible MySQL/MariaDB URL later. Tests never target the production database.

## ADR-003: Approval gates are backend-owned workflow boundaries

Gate 1 (masked data), Gate 2 (spend), and Gate 3 (release) will be stored and enforced by the backend in future modules. No agent, notebook, or imported artifact can approve itself.

## ADR-004: Colab is manual and isolated

Colab remains a human-run research capability. It receives approved, masked packages only and exports unsigned artifacts for backend validation. It is not a job worker or a production API.

## ADR-005: Storage domains remain separate

Relational metadata, raw customer data, masked datasets, model artifacts, and telemetry will use separate access boundaries. Private object storage is the planned durable store for data and artifacts.

## ADR-006: Opaque, database-backed identity sessions

Milestone 2 uses Argon2id password hashes and opaque HttpOnly session cookies. Only a hash of each random session identifier is persisted. This allows revocation, expiry, device/session listing, and password-reset invalidation without placing a bearer credential in browser storage.

## ADR-007: Explicit organization and workspace authorization

Every future tenant-scoped route will resolve the session, membership, organization, workspace, and required permission server-side. IDs and frontend state are selectors only, never authorization proof.

## ADR-008: Two-Tier Multi-Tenancy (Organizations and Workspaces)

Organizations represent top-level business entities with legal, billing, and membership boundaries. Workspaces represent distinct project environments within an organization. A user must have active organization membership before receiving workspace access. Organization Owners automatically inherit administrative rights over all child workspaces.

## ADR-009: Centralized Declarative RBAC Engine

Permissions are represented as fine-grained string constants (`organization.*`, `workspace.*`) evaluated against role matrices. Handlers declare required permissions via dependency factories (`require_org_permission`, `require_ws_permission`) rather than hardcoding role conditionals in application logic.

## ADR-010: Anti-Enumeration 404 Security Policy for Tenant Resources

When a user attempts to access an organization or workspace where they lack active membership, the system returns an HTTP 404 Not Found rather than 403 Forbidden. This prevents unauthorized attackers from probing and enumerating private tenant IDs across the platform.

## ADR-011: Strict Email-Bound Invitation Tokens

Invitations store SHA-256 digests of high-entropy tokens and are strictly bound to the target email address. Consuming an invitation requires that the authenticated user's email exactly matches the invitation's normalized email address, preventing interception or unauthorized account assignment.

## ADR-012: Decoupled Storage Provider Abstraction & Partitioned Buckets

Storage is abstracted behind an interface (`StorageProvider`) supporting private local filesystem storage in development and S3 / Cloudflare R2 object storage in staging/production. The physical store is partitioned into six discrete logical buckets (`raw_uploads`, `masked_datasets`, `evaluations`, `artifacts`, `releases`, `customer_packages`). Raw customer business data is stored exclusively in `raw_uploads` and is strictly forbidden from entering the Control Plane metadata store.

## ADR-013: Bounded Pure-Python Parsers & Decompression-Bomb Defenses

Document extraction is implemented using pure-Python libraries (`pypdf`, `python-docx`, `openpyxl`, `Pillow`) without calling shell subprocesses. All parsers enforce resource boundaries: 25 MB max upload limits, magic-byte verification (disregarding user-supplied MIME claims), and decompression-bomb mitigation for ZIP-based formats (enforcing maximum 100:1 compression ratio and 100 MB uncompressed ceiling).

## ADR-014: Dataset Version Immutability & Cryptographic Content Hash

Datasets support immutable version snapshots (`v1`, `v2`, ...). Once a dataset version is finalized for experimentation, its state transitions to `READY` and a cumulative SHA-256 digest of all constituent document hashes is computed and permanently recorded. This ensures that downstream Gate 1 approvals and model experimentation runs are cryptographically bound to an exact, tamper-evident dataset snapshot.
