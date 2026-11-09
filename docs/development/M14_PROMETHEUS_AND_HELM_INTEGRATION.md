# M14 — Prometheus Scrape Configuration, Helm Charts & Air-Gapped Deployment

This document describes how to configure Prometheus scraping, Grafana dashboards, Docker Compose monitoring profiles, and Kubernetes Helm ServiceMonitors for the Mizan Customer Runtime.

---

## 1. Prometheus Scrape Configuration

The Customer Runtime and Core API expose Prometheus metrics at `/api/v1/ops/metrics/prometheus` and `/metrics`.

### Standard `prometheus.yml` Configuration:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "mizan-customer-runtime"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["runtime:8000"]
        labels:
          environment: "customer-premise"
          service: "customer-runtime"

  - job_name: "mizan-backend-ops"
    metrics_path: "/api/v1/ops/metrics/prometheus"
    static_configs:
      - targets: ["backend:8000"]
        labels:
          environment: "core-platform"
          service: "mizan-core"
```

---

## 2. Docker Compose Monitoring Profile

Milestone 14 introduces an optional `--profile monitoring` configuration in `deploy/docker-compose/docker-compose.yml`:

```bash
# Launch Customer Runtime with self-hosted Prometheus and Grafana
docker compose --profile monitoring up -d
```

### Components:
- **Prometheus** (`prom/prometheus:v2.51.0`): Collects and aggregates metrics with a 15-day local retention window.
- **Grafana OSS** (`grafana/grafana-oss:10.4.0`): Pre-configured dashboards on port `3000` with anonymous viewer access enabled.
- **Zero Cloud Egress**: Entire observability stack runs completely on local Docker bridge networks.

---

## 3. Kubernetes / Helm Deployment with Prometheus Operator

The Helm chart in `deploy/helm/mizan-customer-runtime` provides native Kubernetes observability support:

### `values.yaml` Configuration:
```yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 15s
    scrapeTimeout: 10s
    labels:
      release: prometheus-stack
```

### Pod Annotations:
When `monitoring.serviceMonitor.enabled: false`, standard pod annotations enable discovery by generic Prometheus collectors:
```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/path: "/metrics"
  prometheus.io/port: "8000"
```

### Air-Gapped Operation:
All container images can be loaded from local tar archives into private enterprise registries without requiring internet access.
