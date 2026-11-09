# M14 — Service Level Objectives (SLOs) & Error Budget Calculation

This document specifies the mathematics, rolling evaluation windows, error budget burn down, and missing-telemetry handling implemented in the Mizan SLO subsystem (`app.modules.slo`).

---

## 1. Mathematical SLI & Error Budget Formulations

### Service Level Indicator (SLI)
The SLI represents the percentage of successful requests or events over a defined rolling evaluation window:

$$SLI = \frac{\text{Good Events}}{\text{Total Valid Events}} \times 100\%$$

Where:
- **Good Events**: Successful inference requests (e.g., HTTP status class `2xx`, latency $\le 500\text{ ms}$).
- **Total Valid Events**: All valid incoming inference requests (`2xx` + `4xx` + `5xx`). Note that synthetic health check probes are segregated from customer traffic.

### Error Budget
For a target objective percentage $T$ (e.g., $99.5\%$):

$$\text{Error Budget} = 100\% - T = 0.5\%$$

### Remaining Error Budget Ratio
The percentage of the error budget remaining before SLO breach:

$$\text{Error Budget Remaining} = \max\left(0, 1.0 - \frac{1.0 - \frac{\text{Good Events}}{\text{Total Events}}}{1.0 - \frac{T}{100}}\right) \times 100\%$$

### Multi-Window Burn Rate
The rate at which the error budget is being consumed relative to standard pacing:

$$\text{Burn Rate} = \frac{1.0 - \frac{\text{Good Events}}{\text{Total Events}}}{1.0 - \frac{T}{100}}$$

- $\text{Burn Rate} = 1.0$: Consuming the error budget exactly at the allowed rate over the rolling period (e.g., 30 days).
- $\text{Burn Rate} > 14.4$: Emergency consumption rate (would exhaust 30-day budget in under 48 hours).

---

## 2. Invariant: Missing Telemetry Handling

A fundamental reliability invariant in Mizan is:
> **Absence of telemetry data must never be interpreted as 100% availability.**

When calculating an SLI snapshot for a given window:
- If `total_events == 0` or data is missing due to disconnected agents:
  - `has_sufficient_data = False`
  - `current_sli = 0.0`
  - `error_budget_remaining = 0.0`
  - Status is flagged as `INSUFFICIENT_DATA` or `UNKNOWN`.

This prevents false complacency when monitoring collectors or edge sites experience network partitions.
