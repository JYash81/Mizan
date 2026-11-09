# M14 — Telemetry Privacy, Redaction & SSRF Security Specifications

This document defines the technical specifications, forbidden keys, regex patterns, and security guardrails implemented in Milestone 14 to prevent PII leakage and SSRF attacks.

---

## 1. Zero-Prompt & Zero-Document Leakage Guarantee

Mizan's telemetry subsystem is architected with strict boundary isolation between control plane metrics and inference payload content.

### Payload Sanitization Rules (`telemetry_privacy.py`):

1. **Forbidden Key Stripping**:
   Any key in an event payload matching any of the following substrings is stripped or sanitized:
   - `prompt`
   - `messages`
   - `completion`
   - `output_text`
   - `input_text`
   - `document_text`
   - `raw_query`
   - `context_chunk`
   - `chunk_content`
   - `api_key`
   - `secret`
   - `password`
   - `token`
   - `authorization`
   - `private_key`

2. **Regex Masking**:
   All string values in payloads are scanned and scrubbed:
   - **Bearer Tokens**: `Bearer [A-Za-z0-9\-_=.]+` -> `Bearer [REDACTED_TOKEN]`
   - **Emails**: `[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+` -> `[REDACTED_EMAIL]`
   - **Private Keys**: `-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----` -> `[REDACTED_PRIVATE_KEY]`

3. **Label Cardinality Budgeting**:
   Prometheus and OpenTelemetry metric labels must come from an explicit allowlist. Any arbitrary labels (such as customer IDs, raw request paths, or query parameters) are stripped before metrics are aggregated.

---

## 2. Server-Side Request Forgery (SSRF) Protection for Webhooks

Operators may configure webhook notification endpoints for alerting. Because webhooks trigger outbound HTTP requests from the backend, Mizan implements strict SSRF filters (`NotificationRouter`):

### IP Address & Hostname Restrictions:
Outbound requests are rejected if the target URL resolves to:
- **Loopback**: `127.0.0.0/8`, `::1`, `localhost`
- **Private RFC 1918**:
  - `10.0.0.0/8`
  - `172.16.0.0/12`
  - `192.168.0.0/16`
- **Link-Local & Cloud Metadata Endpoints**:
  - `169.254.0.0/16` (Specifically blocks AWS/GCP/Azure instance metadata at `169.254.169.254`)
  - `fe80::/10`
- **Carrier-Grade NAT**: `100.64.0.0/10`

### Transport Restrictions:
- Allowed schemes: `http://` and `https://` only (no `file://`, `gopher://`, `ftp://`).
- DNS resolution is performed before socket opening; resolved IP is verified against blocked CIDR blocks.
- Max redirects: 0 (redirect following is disabled to prevent DNS rebinding bypasses).
- Connect timeout: 5.0 seconds; read timeout: 10.0 seconds.
