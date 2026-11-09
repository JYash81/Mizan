import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { RecommendationOverviewPage } from "./pages/RecommendationOverviewPage";
import { RecommendationDetailPage } from "./pages/RecommendationDetailPage";
import * as recApi from "./api";
import type {
  RecommendationRunResponse,
  RecommendationRunSummaryResponse,
  OptimizationProfileResponse,
  ObjectiveDefinition,
} from "./types";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    activeWorkspace: { id: "ws-test-123", name: "AI Research Lab" },
    user: { id: "u-1", email: "engineer@mizan.org" },
  }),
}));

const mockObjectives: ObjectiveDefinition[] = [
  {
    key: "aggregate_score",
    display_name: "Aggregate Rubric Score",
    category: "QUALITY",
    direction: "MAXIMIZE",
    unit: "pts",
    description: "Overall multi-criteria rubric evaluation score (0-100 scale).",
    source_module: "M7_EXPERIMENT",
    source_field: "aggregate_score",
    missing_data_policy: "PRESERVE_UNKNOWN",
    is_mandatory_by_default: true,
    version: "1.0.0",
  },
  {
    key: "latency_p95_ms",
    display_name: "Tail Latency (P95)",
    category: "PERFORMANCE",
    direction: "MINIMIZE",
    unit: "ms",
    description: "95th percentile observed per-query response latency.",
    source_module: "M7_EXPERIMENT",
    source_field: "latency_p95_ms",
    missing_data_policy: "PRESERVE_UNKNOWN",
    is_mandatory_by_default: false,
    version: "1.0.0",
  },
  {
    key: "required_ram_mb",
    display_name: "Peak RAM / VRAM",
    category: "RESOURCE",
    direction: "MINIMIZE",
    unit: "MB",
    description: "Estimated peak system RAM or GPU VRAM required for model inference.",
    source_module: "M8_RESOURCE",
    source_field: "peak_memory_mb",
    missing_data_policy: "PRESERVE_UNKNOWN",
    is_mandatory_by_default: false,
    version: "1.0.0",
  },
];

const mockProfiles: OptimizationProfileResponse[] = [
  {
    id: "prof-1",
    organization_id: "org-1",
    workspace_id: "ws-test-123",
    name: "Production Balanced QoS",
    description: "Balanced weights between quality and tail latency",
    objectives: ["aggregate_score", "latency_p95_ms", "required_ram_mb"],
    weights: {
      aggregate_score: 0.5,
      latency_p95_ms: 0.25,
      required_ram_mb: 0.25,
    },
    constraints: {
      min_quality_score: 80.0,
      max_p95_latency_ms: 2000,
      require_gate1_approval: true,
    },
    preferred_hardware_profile: "LOCAL_CPU_I5_8GB",
    budget_currency: "USD",
    version: 1,
    created_by: "u-1",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockRunSummary: RecommendationRunSummaryResponse = {
  id: "rec-run-001",
  organization_id: "org-1",
  workspace_id: "ws-test-123",
  name: "Q4 Sovereign RAG Architecture",
  description: "Evaluate quantized model trade-offs on local CPU",
  status: "COMPLETED",
  algorithm_version: "1.0.0",
  input_digest: "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
  result_digest: "b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef01",
  total_candidates: 3,
  eligible_candidates: 3,
  frontier_candidates: 2,
  created_by: "u-1",
  created_at: new Date().toISOString(),
  completed_at: new Date().toISOString(),
};

const mockRunDetail: RecommendationRunResponse = {
  ...mockRunSummary,
  candidates: [
    {
      id: "cand-1",
      recommendation_run_id: "rec-run-001",
      experiment_id: "exp-1",
      experiment_trial_id: "trial-1",
      candidate_label: "Experiment RAG Alpha - Trial #1 (Q4_K_M)",
      configuration_digest: "digest1111111111",
      evaluation_run_id: "eval-1",
      dataset_id: "ds-1",
      dataset_version_id: "dsv-1",
      evaluation_suite_id: "suite-1",
      evaluation_suite_version_id: "suite-v1",
      evaluation_split: "DEVELOPMENT",
      hardware_profile_key: "LOCAL_CPU_I5_8GB",
      provenance_status: "VERIFIED",
      eligibility_status: "ELIGIBLE",
      exclusion_reasons: [],
      objective_values: {
        aggregate_score: 92.5,
        latency_p95_ms: 1250.0,
        required_ram_mb: 4200.0,
        estimated_cost_usd: 0.0,
      },
      normalized_objective_values: {
        aggregate_score: 0.92,
        latency_p95_ms: 0.85,
        required_ram_mb: 0.9,
      },
      constraint_results: {
        min_quality_score: {
          constraint_key: "min_quality_score",
          passed: true,
          threshold: 75.0,
          actual_value: 92.5,
          reason: "Passed",
        },
      },
      pareto_frontier_member: true,
      dominated_by: [],
      dominates: ["cand-3"],
      weighted_score: 0.885,
      evidence_summary: {
        aggregate_score: "MEASURED",
        latency_p95_ms: "MEASURED",
        required_ram_mb: "ESTIMATED",
        estimated_cost_usd: "MEASURED",
      },
      explanation_text:
        "Candidate is a non-dominated Pareto frontier member with highest measured quality.",
      created_at: new Date().toISOString(),
    },
    {
      id: "cand-2",
      recommendation_run_id: "rec-run-001",
      experiment_id: "exp-1",
      experiment_trial_id: "trial-2",
      candidate_label: "Experiment RAG Alpha - Trial #2 (Q8_0)",
      configuration_digest: "digest2222222222",
      evaluation_run_id: "eval-2",
      dataset_id: "ds-1",
      dataset_version_id: "dsv-1",
      evaluation_suite_id: "suite-1",
      evaluation_suite_version_id: "suite-v1",
      evaluation_split: "DEVELOPMENT",
      hardware_profile_key: "LOCAL_CPU_I5_8GB",
      provenance_status: "VERIFIED",
      eligibility_status: "ELIGIBLE",
      exclusion_reasons: [],
      objective_values: {
        aggregate_score: 95.0,
        latency_p95_ms: 2100.0,
        required_ram_mb: 6400.0,
        estimated_cost_usd: 0.0,
      },
      normalized_objective_values: {
        aggregate_score: 1.0,
        latency_p95_ms: 0.55,
        required_ram_mb: 0.65,
      },
      constraint_results: {},
      pareto_frontier_member: true,
      dominated_by: [],
      dominates: [],
      weighted_score: 0.825,
      evidence_summary: {
        aggregate_score: "MEASURED",
        latency_p95_ms: "MEASURED",
        required_ram_mb: "ESTIMATED",
        estimated_cost_usd: "MEASURED",
      },
      explanation_text: "Candidate remains on Pareto frontier due to highest observed accuracy.",
      created_at: new Date().toISOString(),
    },
    {
      id: "cand-3",
      recommendation_run_id: "rec-run-001",
      experiment_id: "exp-1",
      experiment_trial_id: "trial-3",
      candidate_label: "Experiment RAG Alpha - Trial #3 (FP16 Slow)",
      configuration_digest: "digest3333333333",
      evaluation_run_id: "eval-3",
      dataset_id: "ds-1",
      dataset_version_id: "dsv-1",
      evaluation_suite_id: "suite-1",
      evaluation_suite_version_id: "suite-v1",
      evaluation_split: "DEVELOPMENT",
      hardware_profile_key: "LOCAL_CPU_I5_8GB",
      provenance_status: "VERIFIED",
      eligibility_status: "ELIGIBLE",
      exclusion_reasons: [],
      objective_values: {
        aggregate_score: 88.0,
        latency_p95_ms: 3200.0,
        required_ram_mb: 7800.0,
        estimated_cost_usd: 0.0,
      },
      normalized_objective_values: {
        aggregate_score: 0.75,
        latency_p95_ms: 0.3,
        required_ram_mb: 0.4,
      },
      constraint_results: {},
      pareto_frontier_member: false,
      dominated_by: ["cand-1"],
      dominates: [],
      weighted_score: 0.55,
      evidence_summary: {
        aggregate_score: "MEASURED",
        latency_p95_ms: "MEASURED",
        required_ram_mb: "ESTIMATED",
        estimated_cost_usd: "MEASURED",
      },
      explanation_text: "Candidate is strictly dominated by Trial #1.",
      created_at: new Date().toISOString(),
    },
  ],
  decisions: [
    {
      id: "dec-1",
      recommendation_run_id: "rec-run-001",
      selected_candidate_id: "cand-1",
      decision: "ACCEPTED_FOR_FURTHER_REVIEW",
      decision_reason: "Best balance of quality and latency for local workstation.",
      actor_id: "u-1",
      created_at: new Date().toISOString(),
    },
  ],
  scenarios: [
    {
      id: "sc-1",
      recommendation_run_id: "rec-run-001",
      scenario_name: "Balanced QoS",
      weight_snapshot: {
        aggregate_score: 0.5,
        latency_p95_ms: 0.25,
        required_ram_mb: 0.25,
      },
      ranking_snapshot: [],
      explanation: "Evaluated 3 eligible candidates under Balanced QoS.",
      created_at: new Date().toISOString(),
    },
  ],
};

function renderWithProviders(ui: React.ReactElement, initialPath = "/recommendations") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Recommendation Centre Frontend", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(recApi, "fetchRecommendationRuns").mockResolvedValue({
      items: [mockRunSummary],
      total: 1,
    });
    vi.spyOn(recApi, "fetchRecommendationRun").mockResolvedValue(mockRunDetail);
    vi.spyOn(recApi, "fetchOptimizationProfiles").mockResolvedValue(mockProfiles);
    vi.spyOn(recApi, "fetchObjectives").mockResolvedValue(mockObjectives);
    vi.spyOn(recApi, "fetchPresets").mockResolvedValue({
      BALANCED: { aggregate_score: 0.5, latency_p95_ms: 0.25, required_ram_mb: 0.25 },
    });
    vi.spyOn(recApi, "fetchWorkspaceExperiments").mockResolvedValue({
      items: [
        {
          id: "exp-1",
          name: "Experiment RAG Alpha",
          status: "COMPLETED",
          target_model: "Qwen2.5-1.5B",
          created_at: new Date().toISOString(),
        },
      ],
      total: 1,
    });
    vi.spyOn(recApi, "fetchExperimentDetail").mockResolvedValue({
      id: "exp-1",
      name: "Experiment RAG Alpha",
      trials: [
        {
          id: "trial-1",
          experiment_id: "exp-1",
          trial_number: 1,
          name: "Q4_K_M",
          status: "COMPLETED",
          configuration_digest: "digest111",
          aggregate_score: 92.5,
        },
      ],
    });
    vi.spyOn(recApi, "validateCandidates").mockResolvedValue([
      {
        trial_id: "trial-1",
        experiment_id: "exp-1",
        trial_number: 1,
        candidate_label: "Experiment RAG Alpha - Trial #1",
        trial_status: "COMPLETED",
        configuration_digest: "digest111",
        is_eligible: true,
        exclusion_reasons: [],
        provenance_status: "VERIFIED",
      },
    ]);
  });

  it("renders RecommendationOverviewPage with KPIs, run list, and action buttons", async () => {
    renderWithProviders(<RecommendationOverviewPage />);

    expect(
      screen.getByText("Recommendation Engine & Explainable Optimization Matrix")
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Q4 Sovereign RAG Architecture")).toBeInTheDocument();
    });

    expect(screen.getByText("Candidates Evaluated")).toBeInTheDocument();
    expect(screen.getByText("Frontier Optimal Solutions")).toBeInTheDocument();
    expect(screen.getByText("New Recommendation Run")).toBeInTheDocument();
  });

  it("opens and navigates through RecommendationWizardModal with step progression", async () => {
    renderWithProviders(<RecommendationOverviewPage />);

    await waitFor(() => {
      expect(screen.getByText("New Recommendation Run")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("New Recommendation Run"));

    await waitFor(() => {
      expect(
        screen.getByText(/Step 1 of 8: Identify Decision & Objective/i)
      ).toBeInTheDocument();
    });

    // Enter name
    const nameInput = screen.getByPlaceholderText(/Q4 Sovereign RAG Architecture Decision/i);
    fireEvent.change(nameInput, { target: { value: "Test Run 2026" } });

    // Click Next
    fireEvent.click(screen.getByText("Next"));

    await waitFor(() => {
      expect(
        screen.getByText(/Step 2 of 8: Select Source Experiments/i)
      ).toBeInTheDocument();
    });
  });

  it("renders RecommendationDetailPage with tabs, comparison matrix, and KPI metrics", async () => {
    renderWithProviders(
      <Routes>
        <Route path="/recommendations/:runId" element={<RecommendationDetailPage />} />
      </Routes>,
      "/recommendations/rec-run-001"
    );

    await waitFor(() => {
      expect(screen.getByText("Q4 Sovereign RAG Architecture")).toBeInTheDocument();
    });

    expect(screen.getByText(/Free-Only Policy: \$0.00 Spend Cap Enforced/i)).toBeInTheDocument();
    expect(screen.getByText("Comparison Matrix")).toBeInTheDocument();
    expect(screen.getByText("Pareto Trade-Offs")).toBeInTheDocument();
    expect(screen.getByText("Preferences & Sensitivity")).toBeInTheDocument();

    // Verify candidate rows in comparison matrix
    expect(screen.getByText("Experiment RAG Alpha - Trial #1 (Q4_K_M)")).toBeInTheDocument();
    expect(screen.getByText("Experiment RAG Alpha - Trial #2 (Q8_0)")).toBeInTheDocument();
  });

  it("switches to Pareto Trade-Offs tab and renders chart and dominance list", async () => {
    renderWithProviders(
      <Routes>
        <Route path="/recommendations/:runId" element={<RecommendationDetailPage />} />
      </Routes>,
      "/recommendations/rec-run-001"
    );

    await waitFor(() => {
      expect(screen.getByText("Q4 Sovereign RAG Architecture")).toBeInTheDocument();
    });

    // Click Pareto Trade-Offs Tab
    const paretoTab = screen.getByRole("button", { name: /Pareto Trade-Offs/i });
    fireEvent.click(paretoTab);

    await waitFor(() => {
      expect(screen.getByText(/Pareto Dominance Graph & Non-Dominated Frontier/i)).toBeInTheDocument();
    });

    expect(screen.getByText("Y-Axis Metric")).toBeInTheDocument();
    expect(screen.getByText("X-Axis Metric")).toBeInTheDocument();
  });

  it("opens HumanDecisionModal and records decision", async () => {
    const recordSpy = vi.spyOn(recApi, "recordDecision").mockResolvedValue({
      id: "dec-2",
      recommendation_run_id: "rec-run-001",
      decision: "ACCEPTED_FOR_FURTHER_REVIEW",
      decision_reason: "Approved based on pareto frontier quality.",
      actor_id: "u-1",
      created_at: new Date().toISOString(),
    });

    renderWithProviders(
      <Routes>
        <Route path="/recommendations/:runId" element={<RecommendationDetailPage />} />
      </Routes>,
      "/recommendations/rec-run-001"
    );

    await waitFor(() => {
      expect(screen.getByText("Record Decision")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Record Decision"));

    await waitFor(() => {
      expect(screen.getByText("Record Human Review Decision")).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(
      /State the engineering and business justification for this recommendation decision.../i
    );
    fireEvent.change(textarea, {
      target: { value: "Approved based on pareto frontier quality." },
    });

    const submitButtons = screen.getAllByRole("button", { name: "Record Decision" });
    fireEvent.click(submitButtons[submitButtons.length - 1]);

    await waitFor(() => {
      expect(recordSpy).toHaveBeenCalledWith(
        "ws-test-123",
        "rec-run-001",
        expect.objectContaining({
          decision: "ACCEPTED_FOR_FURTHER_REVIEW",
          decision_reason: "Approved based on pareto frontier quality.",
        })
      );
    });
  });
});
