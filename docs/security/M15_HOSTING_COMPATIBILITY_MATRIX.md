# M15 Hosting Infrastructure & Hostinger Business Plan Compatibility Matrix

## 1. Executive Summary

This assessment evaluates the hosting capabilities of the user's **Hostinger Business Shared Web Hosting** plan against the architectural requirements of the Mizan platform (Milestones 1–15).

- **Assessment Finding:** Hostinger Business Shared Hosting is **INELIGIBLE** for running the Mizan backend control plane, background workers, vector search, or customer runtime.
- **Supported Surface:** Hostinger Business Shared Hosting can **only** host the compiled static frontend single-page application (`frontend/dist/`).
- **Policy Compliance:** In accordance with the platform's **$0.00 additional spend policy**, no commercial hosting upgrades (VPS, Cloud Compute, or Managed Containers) are assumed or purchased.

---

## 2. Component-by-Component Compatibility Matrix

| Mizan Architectural Component | Hostinger Business (Shared) Capability | Compatibility Status | Technical Justification & Constraints |
| :--- | :--- | :--- | :--- |
| **Static Frontend Web Application** (`frontend/dist`) | Static Web Server (LiteSpeed / Apache) | **COMPATIBLE** | HTML5, JavaScript bundles, CSS, and static assets can be uploaded to `public_html/` and served with client-side routing. |
| **FastAPI ASGI Backend Control Plane** (`backend/app`) | Shared PHP execution environment | **INCOMPATIBLE** | No support for persistent Python ASGI processes (Uvicorn / Gunicorn). Shared hosting environments terminate non-PHP daemons and disallow binding to custom TCP ports. |
| **Background Workers & Job Orchestrator** | Shared cPanel cron limits (max 60–120s runtime) | **INCOMPATIBLE** | Long-running asynchronous tasks (model evaluation, RAG indexing, experiment runners) require persistent worker processes; shared cron kills processes exceeding CPU or execution time limits. |
| **Vector Database Engine** (Embedded Qdrant) | No binary / daemon execution | **INCOMPATIBLE** | Qdrant requires running a dedicated binary or Docker container with continuous memory-mapped storage access, which is prohibited on shared hosting. |
| **MySQL Relational Database** | Shared MySQL (MariaDB 10.x / MySQL 8.x) | **PARTIALLY COMPATIBLE (UNUSABLE)** | Hostinger provides shared MySQL accessible via phpMyAdmin and local PHP, but blocks direct external TCP connections from outside Hostinger's internal network. Cannot be connected to an external FastAPI backend without SSH tunneling or proxying. |
| **Cryptographic Key Management** (`storage/keys`) | Shared filesystem with cPanel users | **INCOMPATIBLE (SECURITY RISK)** | Shared hosting environments share filesystem permissions with other virtual hosts and maintenance scripts; cannot guarantee POSIX `chmod 600` process-level isolation. |
| **Site Agent & Customer Runtime** (`deploy/docker-compose.yml`) | No containerization support | **INCOMPATIBLE** | Customer Runtime and Site Agent require Docker / Docker Compose / Kubernetes and local GPU/CPU hardware for model inference. |
| **Production Monitoring & Metrics** (Prometheus / Grafana) | No persistent scrapers or ports | **INCOMPATIBLE** | Cannot host Prometheus scrapers, OpenTelemetry collectors, or Grafana dashboards. |

---

## 3. Detailed Technical Analysis of Hostinger Shared Hosting Limits

### 3.1 Process Lifespan & CloudLinux LVE Restrictions
Hostinger Business Shared Hosting runs under CloudLinux with Lightweight Virtual Environment (LVE) limits:
- Maximum concurrent processes (NPROC): typically 40–100.
- Maximum execution time: 120 seconds.
- Memory ceiling (PMEM): typically 1024 MB to 2048 MB.
Running a persistent Python web server like Uvicorn violates the ephemeral execution model of shared hosting and results in automated process termination (`kill -9`) by the CloudLinux watchdog.

### 3.2 Port Binding & Network Ingress
Shared hosting assigns port 80/443 exclusively to the web server (LiteSpeed/Apache). Individual users cannot open TCP sockets (e.g. port 8000 for Uvicorn, port 6333 for Qdrant, port 9090 for Prometheus).

### 3.3 Database Network Firewalls
Hostinger MySQL instances bind to `localhost` or private internal network segments. While WordPress or PHP scripts running on the same server can connect, external clients (such as local development workstations or external app servers) receive connection timeouts, preventing remote database concurrency verification.

---

## 4. Required Production Deployment Target

To deploy Mizan outside a local development environment, the following minimal infrastructure is required:

```
+-------------------------------------------------------------------------+
|                  Mizan Minimum Production Target Architecture           |
+-------------------------------------------------------------------------+
| Compute:       Dedicated Linux VPS (e.g. Ubuntu 22.04 LTS / 24.04 LTS)  |
| CPU / RAM:     Minimum 2 vCPU, 4 GB RAM (8 GB RAM recommended for RAG)  |
| Storage:       20 GB+ NVMe SSD storage                                  |
| Engine:        Docker 24+ & Docker Compose v2 (or native Systemd units) |
| Reverse Proxy: NGINX / Caddy with automated Let's Encrypt TLS           |
| DBMS:          MySQL 8.0+ or PostgreSQL 15+                             |
+-------------------------------------------------------------------------+
```

---

## 5. Deployment Recommendation

1. **Do not attempt to deploy the Mizan backend to Hostinger Business Shared Hosting.** It will fail due to process termination and port binding restrictions.
2. **If Hostinger is used:** Deploy only the static frontend build (`frontend/dist`) to Hostinger, and configure `VITE_API_BASE_URL` to point to a dedicated VPS or container running the backend.
3. **Preserve $0 Policy:** Do not purchase VPS instances until commercial deployment is authorized.
