# M15 Production Environment Hardening Guide

## 1. Operating System & Host Hardening

### 1.1 Host Infrastructure Requirements
- **Supported Environments:** Dedicated Linux VPS, Bare-Metal Server, or Container Cluster (Docker / Kubernetes) with persistent process support.
- **Ineligible Environments:** Shared PHP/cPanel web hosting (e.g. Hostinger Business Shared Hosting) is strictly **INELIGIBLE** because it lacks Docker support, root daemon privileges, and continuous background Python worker execution.

### 1.2 User & Process Isolation
- Run Mizan under a dedicated non-privileged service user (`mizan`):
  ```bash
  sudo useradd -r -s /bin/false mizan
  ```
- File permissions:
  ```bash
  chmod 750 /opt/mizan
  chmod 700 /opt/mizan/storage/keys
  chmod 600 /opt/mizan/storage/keys/*.pem
  chown -R mizan:mizan /opt/mizan
  ```

---

## 2. Production Environment Variables Checklist

The production startup validator in `app/core/config.py` enforces these constraints at boot time:

```ini
# Core Production Settings
APP_ENV=production
DEBUG=false
SECRET_KEY=<generate-at-least-32-chars-high-entropy-secret>

# HTTPS and Session Cookies
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_NAME=mizan_session

# CORS Configuration (NO WILDCARDS ALLOWED)
CORS_ORIGINS=["https://app.mizan.yourcompany.com"]

# Database Connection (MySQL 8.0+ or PostgreSQL recommended for multi-client scale)
DATABASE_URL=mysql+pymysql://mizan_user:StrongDBPass!@db.internal:3306/mizan_production?charset=utf8mb4

# Storage Configuration
LOCAL_STORAGE_BASE_DIR=/opt/mizan/storage/data_plane
KEY_STORE_DIR=/opt/mizan/storage/keys
```

---

## 3. Reverse Proxy Hardening (NGINX / Caddy)

Place an enterprise reverse proxy in front of Uvicorn:

```nginx
server {
    listen 443 ssl http2;
    server_name app.mizan.yourcompany.com;

    # TLS 1.3 only or modern TLS 1.2
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;

    # Request size limits (25 MB max body size)
    client_max_body_size 25M;

    # Proxy to Uvicorn ASGI server
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

---

## 4. Database Hardening & Preserved Blocker

- Configure MySQL 8.0+ with TLS enabled for remote connections.
- Ensure connection pool size is tuned to host CPU core count (`pool_size=20, max_overflow=10`).
- **Preserved Blocker Notice:** Remote MySQL concurrency verification remains formally preserved as `M2.B1 Step 3 — Remote MySQL Concurrency Verification: BLOCKED` until verified under actual load with multiple concurrent database clients.
