import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { OperationsOverviewPage } from "./pages/OperationsOverviewPage";
import * as opsApi from "./api";
import type {
  MetricsSummary,
  OperationalEvent,
  AlertInstance,
  AlertRule,
  AlertSilence,
  ServiceLevelObjective,
  Incident,
  RollbackPolicy,
  RollbackExecutionEvent,
  SiteSummary,
} from "./types";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    currentWorkspace: { id: "ws-test-123", name: "AI Innovation Lab" },
    activeWorkspace: { id: "ws-test-123", name: "AI Innovation Lab" },
    user: { id: "u-operator", email: "operator@mizan.org" },
  }),
}));

const mockSummary: MetricsSummary = {
  site_id: "site-fra",
  active_slot: "SLOT_A",
  readiness_state: "READY",
  requests_total: 1250,
  error_rate_percentage: 0.16,
  latency_p95_ms: 42.5,
  latency_avg_ms: 18.2,
  tokens_per_second: 320.5,
  cpu_usage_percent: 28.4,
  memory_allocated_mb: 2048,
  vram_allocated_mb: 8192,
  firing_alerts_count: 1,
  slo_status: "HEALTHY",
  timestamp: new Date().toISOString(),
};

const mockEvents: OperationalEvent[] = [
  {
    id: "evt-1",
    workspace_id: "ws-test-123",
    customer_site_id: "site-fra",
    event_type: "DEPLOYMENT_ACTIVATION",
    severity: "INFO",
    source_component: "runtime_engine",
    summary: "Active runtime slot switched from SLOT_B to SLOT_A.",
    payload: { action: "switch", previous_slot: "SLOT_B" },
    created_at: new Date().toISOString(),
  },
  {
    id: "evt-2",
    workspace_id: "ws-test-123",
    customer_site_id: "site-fra",
    event_type: "ALERT_FIRED",
    severity: "CRITICAL",
    source_component: "alert_evaluator",
    summary: "Alert rule HighInferenceLatencyP95 triggered.",
    payload: { latency: 520 },
    created_at: new Date().toISOString(),
  },
];

const mockAlertRules: AlertRule[] = [
  {
    id: "rule-p95",
    workspace_id: "ws-test-123",
    name: "HighInferenceLatencyP95",
    description: "Inference latency exceeded threshold.",
    metric_key: "runtime_request_duration_ms",
    condition_operator: ">",
    threshold: 400.0,
    duration_seconds: 60,
    consecutive_breaches: 3,
    severity: "CRITICAL",
    is_enabled: true,
    cooldown_seconds: 300,
    target_slot: "ACTIVE",
    created_at: new Date().toISOString(),
  },
];

const mockAlertInstances: AlertInstance[] = [
  {
    id: "inst-1",
    rule_id: "rule-p95",
    customer_site_id: "site-fra",
    fingerprint: "fp-latency-1-abcdef123456",
    status: "FIRING",
    current_value: 520.0,
    breach_count: 3,
    fired_at: new Date().toISOString(),
    acknowledged_at: null,
    acknowledged_by: null,
    resolved_at: null,
    labels: { slot: "SLOT_A" },
    annotations: {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockSilences: AlertSilence[] = [];

const mockSlos: ServiceLevelObjective[] = [
  {
    id: "slo-availability",
    workspace_id: "ws-test-123",
    name: "Runtime Availability SLO",
    description: "Successful requests over total requests >= 99.5%",
    metric_key: "runtime_requests_total",
    good_events_definition: "status_class == '2xx'",
    target_percentage: 99.5,
    rolling_window_days: 30,
    is_enabled: true,
    created_at: new Date().toISOString(),
  },
];

const mockIncidents: Incident[] = [
  {
    id: "inc-1",
    workspace_id: "ws-test-123",
    incident_number: 1,
    title: "Sustained p95 Latency Degradation in SLOT_A",
    description: "Latency has degraded past 500ms following model update.",
    severity: "SEV1",
    status: "INVESTIGATING",
    customer_site_id: "site-fra",
    runtime_application_id: "runtime-app-01",
    primary_alert_id: "inst-1",
    assigned_to: "u-operator",
    created_by: "u-operator",
    resolved_at: null,
    closed_at: null,
    events: [
      {
        id: "ev-inc-1",
        incident_id: "inc-1",
        event_type: "CREATED",
        description: "Incident opened automatically from alert.",
        actor_id: null,
        created_at: new Date().toISOString(),
      },
    ],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockPolicies: RollbackPolicy[] = [
  {
    id: "pol-1",
    workspace_id: "ws-test-123",
    runtime_application_id: "runtime-app-01",
    mode: "MANUAL_ONLY",
    evaluation_window_seconds: 300,
    error_rate_threshold_percentage: 5.0,
    latency_p95_threshold_ms: 1000.0,
    cooldown_seconds: 600,
    max_automatic_attempts_per_release: 3,
    require_golden_test_pass: true,
    require_gate3_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockRollbackHistory: RollbackExecutionEvent[] = [
  {
    id: "rb-evt-1",
    runtime_application_id: "runtime-app-01",
    from_slot_name: "SLOT_B",
    to_slot_name: "SLOT_A",
    from_model_version_id: "mv-2",
    to_model_version_id: "mv-1",
    trigger_type: "MANUAL",
    trigger_reason: "Post-activation p95 latency regression",
    verification_passed: true,
    golden_test_run_id: "run-golden-1",
    status: "SUCCESS",
    error_detail: null,
    executed_by: "u-operator",
    created_at: new Date().toISOString(),
  },
];

const mockSites: SiteSummary[] = [
  {
    site_id: "site-fra",
    site_key: "fra-edge-01",
    site_name: "Frankfurt Edge Datacenter",
    status: "ACTIVE",
    agent_enrolled: true,
    agent_alive: true,
    applications_count: 1,
    firing_alerts_count: 0,
    sync_consent: true,
  },
];

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("OperationsOverviewPage (Milestone 14)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(opsApi, "getMetricsSummary").mockResolvedValue(mockSummary);
    vi.spyOn(opsApi, "listOperationalEvents").mockResolvedValue(mockEvents);
    vi.spyOn(opsApi, "listAlertInstances").mockResolvedValue(mockAlertInstances);
    vi.spyOn(opsApi, "listAlertRules").mockResolvedValue(mockAlertRules);
    vi.spyOn(opsApi, "listAlertSilences").mockResolvedValue(mockSilences);
    vi.spyOn(opsApi, "listSlos").mockResolvedValue(mockSlos);
    vi.spyOn(opsApi, "listIncidents").mockResolvedValue(mockIncidents);
    vi.spyOn(opsApi, "listRollbackPolicies").mockResolvedValue(mockPolicies);
    vi.spyOn(opsApi, "listRollbackHistory").mockResolvedValue(mockRollbackHistory);
    vi.spyOn(opsApi, "listSiteSummaries").mockResolvedValue(mockSites);
    vi.spyOn(opsApi, "acknowledgeAlert").mockResolvedValue({
      ...mockAlertInstances[0],
      status: "ACKNOWLEDGED",
    });
    vi.spyOn(opsApi, "updateRollbackPolicy").mockResolvedValue(mockPolicies[0]);
    vi.spyOn(opsApi, "triggerRollback").mockResolvedValue(mockRollbackHistory[0]);
  });

  it("renders header and core operational KPIs in the Overview tab", async () => {
    renderWithClient(<OperationsOverviewPage />);

    expect(screen.getByText("Operations Centre")).toBeInTheDocument();
    expect(screen.getByText("Live Monitoring")).toBeInTheDocument();
    expect(await screen.findByText("42.5 ms")).toBeInTheDocument();
    expect(screen.getByText(/1,?250/)).toBeInTheDocument();
    expect(screen.getByText("Active runtime slot switched from SLOT_B to SLOT_A.")).toBeInTheDocument();
  });

  it("navigates to Alert Centre tab and shows active alert instances and rules", async () => {
    renderWithClient(<OperationsOverviewPage />);

    const alertsTabButton = screen.getByRole("button", { name: /Alert Centre/i });
    fireEvent.click(alertsTabButton);

    expect(await screen.findByText(/Active Alert Instances/i)).toBeInTheDocument();
    expect(await screen.findByText("HighInferenceLatencyP95")).toBeInTheDocument();
    expect(screen.getByText("FIRING")).toBeInTheDocument();
    expect(screen.getByText("Acknowledge")).toBeInTheDocument();
  });

  it("navigates to SLOs & Error Budgets tab and displays target and remaining budget", async () => {
    renderWithClient(<OperationsOverviewPage />);

    const slosTabButton = screen.getByRole("button", { name: /SLOs & Error Budgets/i });
    fireEvent.click(slosTabButton);

    expect(await screen.findByText(/Service Level Objectives & Error Budget Burn Down/i)).toBeInTheDocument();
    expect(await screen.findByText("Runtime Availability SLO")).toBeInTheDocument();
    expect(screen.getByText(/Target: 99.5%/i)).toBeInTheDocument();
    expect(screen.getByText(/85% Remaining/i)).toBeInTheDocument();
  });

  it("navigates to Incidents tab and shows incident details", async () => {
    renderWithClient(<OperationsOverviewPage />);

    const incidentsTabButton = screen.getByRole("button", { name: /Incidents/i });
    fireEvent.click(incidentsTabButton);

    expect(await screen.findByText(/Operational Incidents/i)).toBeInTheDocument();
    expect(screen.getByText("INC-1")).toBeInTheDocument();
    expect(screen.getByText("Sustained p95 Latency Degradation in SLOT_A")).toBeInTheDocument();
    expect(screen.getByText("INVESTIGATING")).toBeInTheDocument();
    expect(screen.getByText("SEV1")).toBeInTheDocument();
  });

  it("navigates to Automated Rollback tab, displays policy modes, and executes rollback", async () => {
    renderWithClient(<OperationsOverviewPage />);

    const rollbackTabButton = screen.getByRole("button", { name: /Automated Rollback/i });
    fireEvent.click(rollbackTabButton);

    expect(await screen.findByText("Rollback Policy Configuration")).toBeInTheDocument();
    expect(await screen.findByText("MANUAL_ONLY")).toBeInTheDocument();

    const reasonInput = screen.getByPlaceholderText(/Rollback justification \/ incident reference.../i);
    fireEvent.change(reasonInput, { target: { value: "Operator initiated emergency test" } });

    const triggerButton = screen.getByRole("button", { name: /Execute Rollback/i });
    fireEvent.click(triggerButton);

    await waitFor(() => {
      expect(opsApi.triggerRollback).toHaveBeenCalledWith("runtime-app-01", "Operator initiated emergency test");
    });
  });
});
