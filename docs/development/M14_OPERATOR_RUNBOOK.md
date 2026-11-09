# M14 — Operator Runbook: Monitoring, Alert Triage, Incident Response & Rollback

This runbook guides platform operators in managing alerts, investigating incidents, handling SLO error budget burn down, and executing or validating Blue/Green slot rollbacks.

---

## 1. High-Priority Alert Response Procedures

### Alert: `HighRequestErrorRate` (Severity: CRITICAL)
- **Condition**: Error rate exceeds 5.0% for 3 consecutive evaluation cycles.
- **Triage Steps**:
  1. Open the **Operations Centre** (`/operations`) and navigate to the **Alert Centre** tab.
  2. Inspect the **Operational Event Journal** in the Overview tab for recent changes or slot activations.
  3. Check the active slot name (`SLOT_A` vs `SLOT_B`) and verify golden test health.
  4. If errors began immediately following a slot transition, proceed to **Manual Rollback**.

### Alert: `HighInferenceLatencyP95` (Severity: CRITICAL)
- **Condition**: p95 inference latency exceeds 2,000ms for 3 consecutive evaluation cycles.
- **Triage Steps**:
  1. Inspect accelerator VRAM allocation and CPU utilization in the Overview gauges.
  2. Verify if batch size or sequence lengths have increased.
  3. If degradation is sustained and impacts SLO error budgets, initiate a slot rollback to the previous release.

### Alert: `SiteAgentHeartbeatMissing` (Severity: CRITICAL)
- **Condition**: No heartbeat received from an enrolled site for >300 seconds.
- **Triage Steps**:
  1. Verify site network connectivity or firewall changes.
  2. Inspect Site Agent container logs (`docker logs mizan-site-agent`).
  3. Check if edge host underwent scheduled maintenance.

---

## 2. Managing Alert Silences

During planned maintenance or database upgrades, operators can temporarily silence alert notifications:
1. Navigate to **Alert Centre** -> **Silences**.
2. Define a duration window (e.g., 60 minutes) and enter a mandatory justification.
3. Silenced alerts continue evaluation in the database for historical auditability, but outbound webhook notifications are suppressed.

---

## 3. Incident Lifecycle Triage

When an incident is opened:
1. **Assign Lead**: Set `assigned_to` to the responding engineer.
2. **Status Transition**: Update status from `OPEN` to `INVESTIGATING`.
3. **Log Notes**: Add timestamped investigative notes via `/api/v1/ops/incidents/{id}/notes` or the Operations Centre UI.
4. **Mitigation**: Update status to `MITIGATING` once a corrective action (e.g. rollback, scale-up) is executed.
5. **Resolution**: Once metrics recover and SLO indicators return to healthy, transition to `RESOLVED` and document root cause before marking `CLOSED`.

---

## 4. Blue/Green Rollback Execution

### Policy Modes:
- **`MANUAL_ONLY` (Default)**: Autonomous slot switching is disabled. Operators must click **Execute Rollback** in the Operations Centre.
- **`AUTOMATIC`**: The platform switches slots autonomously upon sustained breach.

### Manual Rollback Procedure:
1. Go to **Operations Centre** -> **Automated Rollback**.
2. Verify target slot eligibility status (must show `eligible: true`).
3. Enter justification (e.g., `Emergency rollback for INC-0004 due to sustained 12% error rate`).
4. Click **Execute Rollback**.
5. The system performs the atomic slot transition, re-runs golden tests, records a `RollbackExecutionEvent`, and appends the action to the incident audit trail.
