# Mizan Production Deployment Runbook

This is the operational guide for deploying the Mizan control plane (the web UI and
FastAPI API) and, separately, the optional customer runtime/site-agent package. Follow
the gates in order. A gate is a stop condition: do not proceed until it passes.

## 1. Supported production shape

Deploy the components below on a dedicated Linux VPS, server, or Kubernetes cluster.
Do **not** deploy the FastAPI application, database, site agent, or background work on
shared hosting. Static frontend files may be hosted on a CDN or static-site service.

| Component | Where it runs | Public exposure |
| --- | --- | --- |
| React frontend | Static hosting/CDN | `https://app.example.com` |
| FastAPI control plane | VPS/container, behind Nginx/Caddy/managed load balancer | `https://api.example.com` |
| MySQL 8 InnoDB | Managed/private database or dedicated database server | private network only |
| Object storage | Private bucket or private filesystem mount | never public |
| Signing keys | Secret manager or root-owned encrypted volume | never public |
| Customer runtime/site agent | Customer-owned Docker/Kubernetes host | Runtime only if customer requires it; agent has no inbound port |

Use `app.example.com` and `api.example.com` under the same parent domain. This permits
the secure Lax HttpOnly session cookie to work as intended without weakening cookie
policy. Terminate TLS at the reverse proxy and redirect all HTTP traffic to HTTPS.

## 2. Release gates (mandatory)

Before every release, from the repository root on a trusted build machine:

```powershell
cd backend
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m compileall -q app
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip_audit
cd ..\frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm audit --audit-level=low
npm run build
```

Then run the release rehearsals from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\penetration_test_rehearsal.py
.\backend\.venv\Scripts\python.exe .\scripts\disaster_recovery_rehearsal.py
.\backend\.venv\Scripts\python.exe .\scripts\synthetic_key_backup_rehearsal.py
```

Record the commit SHA, package-lock checksum, Python dependency output, and these
results with the release. A failed check means no deployment.

## 3. Required production configuration

Create `backend/.env` only on the server or inject these values through its secret
manager. Never commit it, put it in a frontend build, or paste it into tickets.

```dotenv
APP_NAME=Mizan
APP_ENV=production
APP_VERSION=<release-version>
DEBUG=false
SECRET_KEY=<a unique random secret of at least 32 characters>
DATABASE_URL=mysql+pymysql://<mizan_user>:<url-encoded-password>@<private-mysql-host>:3306/<mizan_db>?charset=utf8mb4
CORS_ORIGINS=https://app.example.com
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=lax
SESSION_COOKIE_DOMAIN=.example.com
STORAGE_BACKEND=<local-or-approved-private-object-storage>
STORAGE_LOCAL_ROOT=/srv/mizan/data
SIGNING_KEYS_DIR=/run/secrets/mizan-signing-keys
DEFAULT_SIGNING_KEY_ID=<production-key-id>
QDRANT_PATH=/srv/mizan/qdrant
FASTEMBED_CACHE_DIR=/srv/mizan/models/fastembed
```

Create the frontend build configuration in `frontend/.env.production` on the build
machine only:

```dotenv
VITE_API_BASE_URL=https://api.example.com/api/v1
```

`VITE_*` values are published into the browser bundle; they must contain no secrets.
Allow only the exact frontend origin in `CORS_ORIGINS`, never `*`. Use unique database
and storage credentials with least privilege. The app account needs access only to its
own schema; it must not have administrative or global privileges.

Generate a new secret rather than choosing one manually:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set signing-key files to the application owner and mode `0600`. Keep the database,
storage, and keys off the public network. Back up encrypted data and key-recovery
materials independently; without both, an encrypted backup may not be recoverable.

## 4. First deployment: control plane

1. Provision a patched Linux host, non-root `mizan` service account, TLS certificate,
   private MySQL 8 InnoDB database, and an off-host encrypted backup destination.
2. Create the database and a least-privilege `mizan_user`; confirm the application host
   can reach MySQL over its private network.
3. Copy the release artifact to `/srv/mizan/app`, create the production `.env`, storage
   directories, and signing-key mount. Ensure the service account owns only its runtime
   directories.
4. Install Python 3.12 and dependencies in a virtual environment:

```bash
cd /srv/mizan/app/backend
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m alembic upgrade head
```

5. Build the frontend on a trusted builder and upload **only** `frontend/dist/` to the
   static host. Do not use the Vite development server in production.

```bash
cd /srv/mizan/app/frontend
npm ci
VITE_API_BASE_URL=https://api.example.com/api/v1 npm run build
```

6. Run FastAPI under a service manager behind a reverse proxy. Example systemd command:

```ini
ExecStart=/srv/mizan/app/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers
```

Use Nginx/Caddy/load-balancer routing from `api.example.com` to `127.0.0.1:8000`.
The proxy must pass `Host` and `X-Forwarded-Proto`, enforce HTTPS, set sane request-body
limits and timeouts, and expose the API process only through the proxy.

## 5. Pre-go-live acceptance checks

Run these from an external network after DNS and TLS are live:

```bash
curl --fail --silent https://api.example.com/api/v1/health
curl --fail --silent https://api.example.com/api/v1/ready
curl --fail --silent https://api.example.com/api/v1/version
curl -I https://api.example.com/api/v1/health
```

Confirm: HTTPS is valid; `/health` and `/ready` return 200; `X-Content-Type-Options`,
`X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and HSTS are present; `/docs`
and `/openapi.json` return 404 in production. From `https://app.example.com`, register a
test user, verify email, log in, create an organization and workspace, upload a benign
test document, verify masking/Gate 1 behavior, log out, and confirm session invalidation.

Run the formal MySQL release gate before admitting multiple customers: ten concurrent
single-use-token attempts must yield exactly one winner, invitation and unique-slug races
must preserve data integrity, no tenant data may leak under concurrent load, and Alembic
migration upgrade/downgrade must complete. See
`docs/security/M15_MYSQL_CONCURRENCY_VERIFICATION.md`. This gate is currently unverified
on this workstation and is a no-exception requirement for a multi-client launch.

## 6. Operating the application

An organization owner signs in, creates an organization and workspace, adds members,
and works within the selected workspace. The normal governed flow is:

1. Create or import a dataset and documents.
2. Review PII masking and approve the dataset at Gate 1.
3. Define hardware and cost constraints; approve the resource plan at Gate 2.
4. Run evaluations/experiments and inspect comparisons and recommendations.
5. Build or import a model; register an immutable artifact and approve it at Gate 3.
6. Publish an approved model/application to the catalog or deploy it to an enrolled
   customer site.
7. Watch runtime readiness, incidents, alerts, and rollout status; use the governed
   rollback action if a candidate becomes unhealthy.

Use the API reference documents in `docs/api/` for endpoint-level details and
`docs/development/M14_OPERATOR_RUNBOOK.md` for operations/alerting procedures.

## 7. Customer runtime and site-agent deployment

The files under `deploy/docker-compose/` and `deploy/helm/` are for a customer-controlled
runtime host, not the public control plane. Before using them, install Docker/Compose or
Kubernetes/Helm on that host, set a non-default Grafana password if monitoring is enabled,
set `MIZAN_CONTROL_PLANE_URL`, `MIZAN_CUSTOMER_SITE_ID`, and `MIZAN_SITE_AGENT_ID`, then
enroll with a single-use token. Follow `deploy/docker-compose/README.md` exactly.

Build and run validation on a Docker-capable staging host:

```bash
cd deploy/docker-compose
docker compose build --no-cache
docker compose config
docker compose up -d
docker compose ps
curl --fail http://localhost:8080/api/v1/runtime/live
curl --fail http://localhost:8080/api/v1/runtime/ready
docker compose down
```

Do not expose the site agent. The runtime's ingress must be restricted to the customer
network. Back up its persistent volumes before upgrades and use blue/green promotion plus
golden tests before switching traffic.

## 8. Release, rollback, and incident rules

- Take and verify an encrypted database/storage backup before every migration.
- Migrate first, then deploy the new API, wait for `/ready`, then deploy the static UI.
- Use a maintenance window for non-backward-compatible schema changes. Keep the previous
  release artifact available until the observation period completes.
- If health, error rate, SLO, tenant isolation, or Gate controls regress: stop rollout,
  route traffic to the previous healthy release, and restore only from a verified backup
  when rollback is not sufficient. Preserve logs and evidence before remediation.
- Rotate exposed secrets immediately; revoke affected sessions/tokens/site-agent keys;
  investigate audit events; and document the incident. Do not copy production data into
  development or test systems.
- Test restoration on a clean, isolated host at least quarterly and after key-management
  changes. Test a full user workflow after every release.

## 9. Monitoring and ownership

Monitor API availability/readiness, MySQL availability and replication/backups, disk and
object-storage capacity, runtime slot readiness, error rate, latency, authentication
failures, alert delivery, certificate expiry, and backup completion. Restrict Prometheus
and Grafana to the operator network; change every default credential before exposure.

Assign named owners for: release approval, database administration, secret/key custody,
backup recovery, security incident response, customer support, and 24/7 operational
escalation. A production system without those owners is not ready to go live.
