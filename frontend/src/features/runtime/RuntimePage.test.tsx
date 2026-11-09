import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { SitesPage } from "./pages/SitesPage";
import { RuntimeDashboardPage } from "./pages/RuntimeDashboardPage";
import { SlotCard } from "./components/SlotCard";
import { GoldenTestResultsCard } from "./components/GoldenTestResultsCard";
import * as runtimeApi from "./api";
import type { CustomerSite, RuntimeSlot, GoldenTestRun } from "./types";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    currentWorkspace: { id: "ws-test-123", name: "AI Innovation Lab" },
    activeWorkspace: { id: "ws-test-123", name: "AI Innovation Lab" },
    user: { id: "u-operator", email: "operator@mizan.org" },
  }),
}));

const mockSites: CustomerSite[] = [
  {
    id: "site-1",
    organization_id: "org-1",
    workspace_id: "ws-test-123",
    site_key: "site-fra-datacenter",
    site_name: "Frankfurt Edge Datacenter",
    description: "Air-gapped on-premise Kubernetes cluster.",
    status: "ACTIVE",
    created_by: "u-operator",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    agent_enrolled: true,
    active_runtime_version: "1.0.0",
    last_heartbeat_at: new Date().toISOString(),
  },
];

const mockSlots: RuntimeSlot[] = [
  {
    id: "slot-a",
    runtime_application_id: "app-1",
    slot_name: "SLOT_A",
    app_version_id: "app-ver-1",
    model_version_id: "model-ver-1",
    release_manifest_digest: "11112222333344445555666677778888",
    status: "ACTIVE",
    readiness_state: "READY",
    golden_test_status: "PASSED",
    last_golden_test_run_id: "run-1",
    engine_adapter_key: "MOCK_ENGINE",
    configuration_snapshot: {},
    staged_at: new Date().toISOString(),
    activated_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "slot-b",
    runtime_application_id: "app-1",
    slot_name: "SLOT_B",
    app_version_id: "app-ver-2",
    model_version_id: "model-ver-2",
    release_manifest_digest: "99998888777766665555444433332222",
    status: "STAGED",
    readiness_state: "READY",
    golden_test_status: "PASSED",
    last_golden_test_run_id: "run-2",
    engine_adapter_key: "MOCK_ENGINE",
    configuration_snapshot: {},
    staged_at: new Date().toISOString(),
    activated_at: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockGoldenRun: GoldenTestRun = {
  id: "run-2",
  runtime_slot_id: "slot-b",
  suite_id: "suite-1",
  suite_digest: "suite_digest_abcdef123456",
  runtime_version: "1.0.0",
  outcome: "PASSED",
  total_cases: 8,
  passed_cases: 8,
  failed_cases: 0,
  duration_ms: 48.5,
  results_summary: {
    cases: [
      { case_id: "TC-001", category: "startup", mandatory: true, passed: true, error_code: null },
      { case_id: "TC-002", category: "model_loading", mandatory: true, passed: true, error_code: null },
      { case_id: "TC-003", category: "inference_smoke", mandatory: true, passed: true, error_code: null },
      { case_id: "TC-004", category: "output_schema", mandatory: true, passed: true, error_code: null },
      { case_id: "TC-005", category: "rag_retrieval_citations", mandatory: true, passed: true, error_code: null },
      { case_id: "TC-006", category: "safety_abstention", mandatory: true, passed: true, error_code: null },
      { case_id: "TC-007", category: "offline_path", mandatory: true, passed: true, error_code: null },
      { case_id: "TC-008", category: "resource_limits", mandatory: false, passed: true, error_code: null },
    ],
  },
  started_at: new Date().toISOString(),
  completed_at: new Date().toISOString(),
};

describe("Customer Runtime & Site Agent Frontend Suite", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.clearAllMocks();
  });

  const renderWithProviders = (ui: React.ReactElement, initialPath = "/") => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[initialPath]}>
          {ui}
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  it("renders customer deployment sites list properly", async () => {
    vi.spyOn(runtimeApi, "listCustomerSites").mockResolvedValue(mockSites);

    renderWithProviders(<SitesPage />);

    expect(await screen.findByText("Frankfurt Edge Datacenter")).toBeInTheDocument();
    expect(screen.getByText("site-fra-datacenter")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Enrolled")).toBeInTheDocument();
  });

  it("renders Blue/Green slot cards with traffic serving and staged states", () => {
    const onRun = vi.fn();
    const onActivate = vi.fn();

    renderWithProviders(
      <div className="grid grid-cols-2 gap-4">
        <SlotCard slot={mockSlots[0]} isActive={true} onRunGoldenTests={onRun} onActivate={onActivate} />
        <SlotCard slot={mockSlots[1]} isActive={false} onRunGoldenTests={onRun} onActivate={onActivate} />
      </div>
    );

    expect(screen.getByText("Slot A (Blue)")).toBeInTheDocument();
    expect(screen.getByText("Slot B (Green)")).toBeInTheDocument();
    expect(screen.getByText("Active Serving")).toBeInTheDocument();
    expect(screen.getByText("Staged Candidate")).toBeInTheDocument();
    expect(screen.getByText("Promote to Active")).toBeInTheDocument();
  });

  it("renders 8 Golden Acceptance test categories with privacy guarantee", () => {
    renderWithProviders(<GoldenTestResultsCard run={mockGoldenRun} />);

    expect(screen.getByText("Golden Acceptance Test Suite")).toBeInTheDocument();
    expect(screen.getByText(/Privacy Guaranteed/i)).toBeInTheDocument();
    expect(screen.getByText("Deterministic Inference Smoke Test")).toBeInTheDocument();
    expect(screen.getByText("Safety Policy & Guardrail Abstention")).toBeInTheDocument();
    expect(screen.getByText("Zero External Network / Offline Isolation")).toBeInTheDocument();
    expect(screen.getAllByText("PASSED").length).toBeGreaterThan(0);
  });

  it("renders the Runtime Dashboard and executes offline chat completion test", async () => {
    vi.spyOn(runtimeApi, "getApplicationSlots").mockResolvedValue(mockSlots);
    vi.spyOn(runtimeApi, "getRuntimeHealth").mockResolvedValue({
      status: "healthy",
      uptime_seconds: 3600,
      active_slot: "SLOT_A",
      readiness: "READY",
      engine: "MOCK_ENGINE",
      offline_mode: true,
      memory_allocated_mb: 256,
    });
    vi.spyOn(runtimeApi, "listActivationEvents").mockResolvedValue([]);
    vi.spyOn(runtimeApi, "executeChatCompletion").mockResolvedValue({
      id: "chat-1",
      object: "chat.completion",
      created: 1234567,
      model: "mock-model",
      choices: [{ index: 0, message: { role: "assistant", content: "Local offline answer generated." }, finish_reason: "stop" }],
      usage: { prompt_tokens: 5, completion_tokens: 5, total_tokens: 10 },
      offline_executed: true,
    });

    renderWithProviders(<RuntimeDashboardPage />);

    expect(await screen.findByText("Customer Runtime Console")).toBeInTheDocument();
    expect(screen.getByText(/Offline Execution Active/i)).toBeInTheDocument();
    expect(await screen.findByText("Slot A (Blue)")).toBeInTheDocument();

    // Fill chat prompt
    const promptInput = screen.getByPlaceholderText(/Ask a question or try safety checks/i);
    fireEvent.change(promptInput, { target: { value: "Test prompt message" } });

    const sendBtn = screen.getByText("Send Query");
    fireEvent.click(sendBtn);

    expect(await screen.findByText("Local offline answer generated.")).toBeInTheDocument();
  });
});
