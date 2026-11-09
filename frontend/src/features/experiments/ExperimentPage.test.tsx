import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ExperimentListPage } from "./pages/ExperimentListPage";
import { ExperimentDetailPage } from "./pages/ExperimentDetailPage";
import { ExperimentComparisonPage } from "./pages/ExperimentComparisonPage";
import * as expApi from "./api";
import type { Experiment, ExperimentComparisonResponse } from "./types";

// Mock AuthContext
vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    activeWorkspace: { id: "ws-test-123", name: "AI Research Lab" },
    user: { id: "u-1", email: "fatima@mizan.ae" },
  }),
}));

const mockExperiments: Experiment[] = [
  {
    id: "exp-101",
    organization_id: "org-1",
    workspace_id: "ws-test-123",
    name: "Chunk Size Sensitivity Study",
    slug: "chunk-size-sensitivity-study",
    description: "Evaluates chunk size impacts on groundedness and latency.",
    status: "COMPLETED",
    dataset_id: "ds-1",
    dataset_version_id: "ver-1",
    gate1_approval_id: "g1-app-1",
    dataset_digest: "digest123",
    evaluation_suite_id: "suite-1",
    evaluation_suite_version_id: "sver-1",
    canonical_suite_digest: "suitehash123",
    evaluation_split: "VALIDATION",
    baseline_config: { chunk_size_chars: 500, top_k: 4, provider_name: "mock" },
    configuration_digest: "confighash123",
    total_trials: 3,
    completed_trials: 3,
    failed_trials: 0,
    cancelled_trials: 0,
    started_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
    cancellation_requested_at: null,
    error_message: null,
    created_by: "u-1",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    trials: [
      {
        id: "trial-1",
        organization_id: "org-1",
        workspace_id: "ws-test-123",
        experiment_id: "exp-101",
        trial_number: 1,
        name: "Small Chunks (250/50)",
        status: "COMPLETED",
        configuration_json: JSON.stringify({
          chunk_size_chars: 250,
          chunk_overlap_chars: 50,
          top_k: 4,
          provider_name: "mock",
          model_name: "mock-rag-v1",
        }),
        configuration_digest: "digest-t1",
        evaluation_run_id: "run-1",
        aggregate_score: 88.5,
        score_breakdown: { groundedness: 92.0, faithfulness: 85.0 },
        latency_p50_ms: 120.5,
        latency_p95_ms: 150.0,
        latency_p99_ms: null,
        execution_duration_ms: 450.0,
        error_code: null,
        error_summary: null,
        retry_count: 0,
        queued_at: null,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: "trial-2",
        organization_id: "org-1",
        workspace_id: "ws-test-123",
        experiment_id: "exp-101",
        trial_number: 2,
        name: "Medium Chunks (500/100)",
        status: "COMPLETED",
        configuration_json: JSON.stringify({
          chunk_size_chars: 500,
          chunk_overlap_chars: 100,
          top_k: 4,
          provider_name: "mock",
          model_name: "mock-rag-v1",
        }),
        configuration_digest: "digest-t2",
        evaluation_run_id: "run-2",
        aggregate_score: 94.2,
        score_breakdown: { groundedness: 96.0, faithfulness: 92.4 },
        latency_p50_ms: 145.0,
        latency_p95_ms: 180.0,
        latency_p99_ms: null,
        execution_duration_ms: 510.0,
        error_code: null,
        error_summary: null,
        retry_count: 0,
        queued_at: null,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ],
  },
];

const mockComparison: ExperimentComparisonResponse = {
  experiment_id: "exp-101",
  experiment_name: "Chunk Size Sensitivity Study",
  status: "COMPLETED",
  dataset_version_id: "ver-1",
  evaluation_suite_version_id: "sver-1",
  evaluation_split: "VALIDATION",
  total_trials: 2,
  completed_trials: 2,
  failed_trials: 0,
  trials: [
    {
      trial_id: "trial-1",
      trial_number: 1,
      name: "Small Chunks (250/50)",
      status: "COMPLETED",
      configuration: { chunk_size_chars: 250, top_k: 4, model_name: "mock-rag-v1" },
      configuration_digest: "digest-t1",
      evaluation_run_id: "run-1",
      aggregate_score: 88.5,
      metric_scores: { groundedness: 92.0, faithfulness: 85.0 },
      latency_p50_ms: 120.5,
      latency_p95_ms: 150.0,
      latency_p99_ms: null,
      execution_duration_ms: 450.0,
      error_summary: null,
    },
    {
      trial_id: "trial-2",
      trial_number: 2,
      name: "Medium Chunks (500/100)",
      status: "COMPLETED",
      configuration: { chunk_size_chars: 500, top_k: 4, model_name: "mock-rag-v1" },
      configuration_digest: "digest-t2",
      evaluation_run_id: "run-2",
      aggregate_score: 94.2,
      metric_scores: { groundedness: 96.0, faithfulness: 92.4 },
      latency_p50_ms: 145.0,
      latency_p95_ms: 180.0,
      latency_p99_ms: null,
      execution_duration_ms: 510.0,
      error_summary: null,
    },
  ],
  metric_keys: ["groundedness", "faithfulness"],
  metric_observations: [
    {
      metric_key: "groundedness",
      highest_observed_score: 96.0,
      highest_scoring_trials: [2],
      lowest_observed_score: 92.0,
      mean_observed_score: 94.0,
    },
  ],
  lowest_observed_latency_ms: 120.5,
  lowest_latency_trials: [1],
  compatibility_verified: true,
  compatibility_notes: [],
};

function renderWithClient(ui: React.ReactElement, initialPath = "/") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Milestone 7: Experiment Lab UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders ExperimentListPage and displays existing experiments", async () => {
    vi.spyOn(expApi, "fetchExperiments").mockResolvedValue(mockExperiments);

    renderWithClient(
      <Routes>
        <Route path="/" element={<ExperimentListPage />} />
      </Routes>
    );

    expect(screen.getByText(/Model Experimentation Lab/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Chunk Size Sensitivity Study")).toBeInTheDocument();
      expect(screen.getByText(/chunk-size-sensitivity-study/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Completed/i).length).toBeGreaterThan(0);
    });
  });

  it("filters experiments by search query", async () => {
    vi.spyOn(expApi, "fetchExperiments").mockResolvedValue(mockExperiments);

    renderWithClient(
      <Routes>
        <Route path="/" element={<ExperimentListPage />} />
      </Routes>
    );

    await waitFor(() => {
      expect(screen.getByText("Chunk Size Sensitivity Study")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search experiments/i);
    fireEvent.change(searchInput, { target: { value: "Nonexistent" } });

    await waitFor(() => {
      expect(screen.queryByText("Chunk Size Sensitivity Study")).not.toBeInTheDocument();
    });
  });

  it("renders ExperimentDetailPage with trial matrix and provenance", async () => {
    vi.spyOn(expApi, "fetchExperiment").mockResolvedValue(mockExperiments[0]);

    renderWithClient(
      <Routes>
        <Route path="/experiments/:experimentId" element={<ExperimentDetailPage />} />
      </Routes>,
      "/experiments/exp-101"
    );

    await waitFor(() => {
      expect(screen.getByText("Chunk Size Sensitivity Study")).toBeInTheDocument();
      expect(screen.getByText(/Small Chunks/i)).toBeInTheDocument();
      expect(screen.getByText(/Medium Chunks/i)).toBeInTheDocument();
      expect(screen.getByText("88.5%")).toBeInTheDocument();
      expect(screen.getByText("94.2%")).toBeInTheDocument();
    });
  });

  it("opens trial modal on row click", async () => {
    vi.spyOn(expApi, "fetchExperiment").mockResolvedValue(mockExperiments[0]);

    renderWithClient(
      <Routes>
        <Route path="/experiments/:experimentId" element={<ExperimentDetailPage />} />
      </Routes>,
      "/experiments/exp-101"
    );

    await waitFor(() => {
      expect(screen.getByText(/Small Chunks/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Small Chunks/i));

    await waitFor(() => {
      expect(screen.getByText(/Full Trial Configuration:/i)).toBeInTheDocument();
      expect(screen.getByText(/Evaluated Rubric Breakdown:/i)).toBeInTheDocument();
      expect(screen.getByText("92.0%")).toBeInTheDocument();
    });
  });

  it("renders ExperimentComparisonPage with factual observations and metric matrix", async () => {
    vi.spyOn(expApi, "fetchComparison").mockResolvedValue(mockComparison);

    renderWithClient(
      <Routes>
        <Route
          path="/experiments/:experimentId/comparison"
          element={<ExperimentComparisonPage />}
        />
      </Routes>,
      "/experiments/exp-101/comparison"
    );

    await waitFor(() => {
      expect(screen.getByText(/Factual Trial Comparison Matrix/i)).toBeInTheDocument();
      expect(screen.getByText(/Provenance Consistency Attested/i)).toBeInTheDocument();
      expect(screen.getByText(/Empirical Factual Observations/i)).toBeInTheDocument();
      expect(screen.getByText(/Evaluation Boundary Policy/i)).toBeInTheDocument();
    });
  });
});
