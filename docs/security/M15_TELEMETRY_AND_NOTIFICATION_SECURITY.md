# M15 Telemetry, Observability & Notification Security

## 1. Observability Security Principles

Operational monitoring and alerting present critical security risks if unconstrained:
1. **PII and Secret Leakage:** Prompts, completions, and runtime tokens accidentally captured in event logs or traces.
2. **Prometheus Cardinality Explosions:** Dynamic user inputs inserted as metric labels causing denial-of-service in monitoring databases.
3. **Server-Side Request Forgery (SSRF):** Malicious webhook notification URLs targeting internal metadata or localhost services.

---

## 2. Hardened Telemetry Architecture

```mermaid
flowchart LR
    RawEvent[Operational Event] --> PrivacyFilter[Telemetry Privacy Engine]
    PrivacyFilter --> ScrubSecrets[Scrub Bearer Tokens / API Keys]
    PrivacyFilter --> HashPII[Mask Emails, SSNs, IPs]
    ScrubSecrets --> SanitizedEvent[Sanitized Event Journal]

    PromCollector[Prometheus Metric Collector] --> CardinalityFilter[Cardinality Controller]
    CardinalityFilter --> BoundLabels[Sanitize & Bound Label Count <= 20]
    BoundLabels --> MetricScrape[/metrics Endpoint]

    AlertEngine[Incident Alert Engine] --> WebhookValidator[SSRF Webhook Validator]
    WebhookValidator --> RejectPrivate[Reject RFC1918, Loopback, LinkLocal, IMDS]
    WebhookValidator --> DeliverWebhook[HTTPS Outbound Webhook Delivery]
```

---

## 3. Implemented Controls & Test Verification

### 3.1 Telemetry Payload Sanitization & Zero PII
- `assert_no_privacy_violation` and `sanitize_event_payload` scan event dictionaries for patterns matching:
  - Bearer tokens, private keys, API secrets (`sk-...`, `Bearer ...`).
  - Credit card numbers, Social Security Numbers, phone numbers.
  - Raw unmasked prompts and completions.
- Discovered sensitive values are replaced with cryptographic surrogates (`<MASKED_SECRET>`, `<MASKED_PII>`).
- **Evidence:** `backend/tests/security/test_security_advanced.py::test_sec_023_runtime_secret_not_leaked_in_telemetry` and `test_sec_024_telemetry_payload_sanitization`.

### 3.2 Prometheus Cardinality Bounding
- `validate_and_sanitize_labels` enforces strict alphanumeric label keys, maximum label count of 20, and truncation of high-cardinality values.
- Unsanitized characters are stripped to prevent metric spoofing or memory exhaustion.
- **Evidence:** `backend/tests/security/test_security_advanced.py::test_sec_025_prometheus_label_cardinality_control`.

### 3.3 SSRF Defense on Alert Webhooks
- `validate_webhook_url` parses notification targets:
  - Enforces `https://` (or `http://` for explicit dev mode only).
  - Resolves domain to IP and checks against IPv4 and IPv6 blocklists:
    - Loopback: `127.0.0.0/8`, `::1`
    - Private: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
    - Link-Local & Cloud Metadata: `169.254.0.0/16`
    - Multicast / Reserved: `224.0.0.0/4`, `240.0.0.0/4`
  - Blocks DNS rebinding aliases such as `0.0.0.0`, `localhost`, `127.0.0.1.nip.io`.
- **Evidence:** `backend/tests/security/test_security_advanced.py::test_sec_026` and `test_sec_027`.
