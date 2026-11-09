# M15 Software Bill of Materials (SBOM) & Dependency Security Report

## 1. Executive Summary

- **Audit Date:** 2026-11-09
- **Tools Used:** `pip-audit` v2.10.1 (Python packages), `npm audit` (JavaScript/TypeScript packages).
- **Python Dependencies Scanned:** 68 packages.
- **Node Dependencies Scanned:** 244 packages.
- **Identified Vulnerabilities:** **0 known vulnerabilities across backend and frontend.**
- **Remediated Advisories:** `pytest` upgraded to 9.2.0 (remediating PYSEC-2026-1845).

---

## 2. Backend Dependency Security Audit

### pip-audit Scan Output
```
No known vulnerabilities found
Scan result: 0 vulnerabilities across 68 packages inspected.
Database: PyPI Vulnerability Advisory Database (OSV / GitHub Advisory Database).
```

### Core Backend Packages & Licenses

| Package | Version | License | Security Role / Purpose |
| :--- | :--- | :--- | :--- |
| `fastapi` | 0.115.11 | MIT | High-performance ASGI Web API Framework |
| `uvicorn` | 0.34.0 | BSD-3-Clause | ASGI HTTP/WebSocket Server |
| `pydantic` | 2.10.6 | MIT | Strict Data Validation & Schema Enforcement |
| `sqlalchemy` | 2.0.38 | MIT | SQL Toolkit & Object-Relational Mapper |
| `alembic` | 1.15.1 | MIT | Database Migration Tool |
| `argon2-cffi` | 23.1.0 | MIT | Argon2id Memory-Hard Password Hashing |
| `cryptography` | 44.0.2 | Apache-2.0 / BSD | Ed25519 Digital Signatures & Ciphers |
| `pytest` | 9.2.0 | MIT | Automated Test Framework (Upgraded in M15) |
| `bandit` | 1.9.4 | Apache-2.0 | Python AST Security Static Analysis |

---

## 3. Frontend Dependency Security Audit

### npm audit Scan Output
```
found 0 vulnerabilities
Scan result: 0 vulnerabilities across 244 dependencies inspected.
Database: GitHub Advisory Database / npm Security Registry.
```

### Core Frontend Packages & Licenses

| Package | Version | License | Security Role / Purpose |
| :--- | :--- | :--- | :--- |
| `react` | 19.0.0 | MIT | User Interface Library (Automatic JSX Escaping) |
| `react-dom` | 19.0.0 | MIT | DOM Rendering Engine |
| `react-router-dom` | 7.3.0 | MIT | Client-Side Routing |
| `lucide-react` | 1.16.0 | ISC | Scalable Vector Icons |
| `vite` | 6.4.5 | MIT | Build Tooling & Bundler |
| `vitest` | 5.1.0 | MIT | Frontend Unit & Component Test Runner |
| `typescript` | 5.8.2 | Apache-2.0 | Static Type Verification |
| `eslint` | 9.21.0 | MIT | Code Style & Vulnerability Linter |

---

## 4. Software Bill of Materials (SBOM) Generation Procedure

To generate a CycloneDX or SPDX JSON SBOM for compliance and supply chain audits:

```bash
# Backend Python SBOM
pip install cyclonedx-bom
cyclonedx-py environment --outfile backend-sbom.json

# Frontend Node.js SBOM
npx @cyclonedx/cyclonedx-npm --output-file frontend-sbom.json
```
