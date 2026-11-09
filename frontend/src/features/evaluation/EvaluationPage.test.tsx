import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { EvaluationOverviewPage } from "./pages/EvaluationOverviewPage";
import { EvaluationSuiteDetailPage } from "./pages/EvaluationSuiteDetailPage";
import { EvaluationRunPage } from "./pages/EvaluationRunPage";
import * as evalApi from "./api";
import type { EvaluationCase, EvaluationRun, EvaluationSuite } from "./types";

// Mock AuthContext
vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    activeWorkspace: { id: "ws-test-123", name: "AI Research Lab" },
    user: { id: "u-1", email: "fatima@mizan.ae" },
  }),
}));

const mockSuites: EvaluationSuite[] = [
  {
    id: "suite-101",
    organization_id: "org-1",
    workspace_id: "ws-test-123",
    name: "Corporate Credit Policies 2026",
    slug: "corporate-credit-policies-2026",
    description: "Evaluates credit risk assessment and approval limits",
    domain: "Banking & Compliance",
    language: "en",
    status: "READY",
    source_dataset_id: "ds-1",
    source_dataset_version_id: "ver-1",
    gate1_approval_id: "g1-app-1",
    case_count: 12,
    total_cases: 12,
    active_version: 1,
    created_by: "u-1",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockCases: EvaluationCase[] = [
  {
    id: "case-1",
    organization_id: "org-1",
    workspace_id: "ws-test-123",
    suite_id: "suite-101",
    suite_version_id: "ver-101",
    case_type: "generated",
    category: "NUMERICAL",
    difficulty: "MEDIUM",
    split: "VALIDATION",
    language: "en",
    question: "What is the maximum overdraft limit for retail accounts?",
    expected_answer: "The maximum overdraft limit is 15,000 AED upon salary transfer.",
    is_unanswerable: false,
    source_document_ids: ["doc-1"],
    source_chunk_ids: ["chunk-1"],
    ground_truth_status: "HUMAN_VERIFIED",
    generation_method: "rule_based",
    reviewer_notes: "Checked against retail credit policy 2026",
    created_by: "u-1",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "case-2",
    organization_id: "org-1",
    workspace_id: "ws-test-123",
    suite_id: "suite-101",
    suite_version_id: null,
    case_type: "manual",
    category: "UNANSWERABLE",
    difficulty: "HARD",
    split: "HOLDOUT",
    language: "en",
    question: "What is the cryptocurrency margin trading rate?",
    expected_answer: "The provided documents do not contain information regarding cryptocurrency margin trading.",
    is_unanswerable: true,
    source_document_ids: [],
    source_chunk_ids: [],
    ground_truth_status: "NEEDS_REVIEW",
    generation_method: "manual_curation",
    reviewer_notes: null,
    created_by: "u-1",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockRuns: EvaluationRun[] = [
  {
    id: "run-999",
    organization_id: "org-1",
    workspace_id: "ws-test-123",
    suite_id: "suite-101",
    suite_version_id: "ver-101",
    rubric_id: "rub-1",
    rubric_version: 1,
    target_type: "MOCK_LLM",
    target_name: "Mizan Free Local Baseline",
    provider_name: "mock",
    model_name: "mock-generator-v1",
    status: "COMPLETED",
    total_cases: 12,
    completed_cases: 12,
    passed_cases: 11,
    failed_cases: 1,
    overall_score: 91.5,
    score_breakdown: {
      exact_match: 85.0,
      token_f1: 94.2,
      keyword_coverage: 92.0,
      retrieval_quality: 90.0,
      context_relevance: 95.0,
      faithfulness: 96.0,
      groundedness: 98.0,
      citation_verification: 90.0,
      appropriate_abstention: 100.0,
      safety: 100.0,
      compliance: 95.0,
    },
    metric_summary: {
      exact_match: 85.0,
      token_f1: 94.2,
      groundedness: 98.0,
      safety: 100.0,
    },
    error_message: null,
    latency_p50_ms: 120.0,
    latency_p95_ms: 210.0,
    latency_p99_ms: 250.0,
    execution_duration_ms: 1450.0,
    started_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
    created_by: "u-1",
    created_at: new Date().toISOString(),
    case_results: [
      {
        id: "cr-1",
        run_id: "run-999",
        case_id: "case-1",
        actual_answer: "The maximum overdraft limit is 15,000 AED upon salary transfer.",
        actual_answer_digest: "sha256-abc...",
        overall_case_score: 95.0,
        status: "COMPLETED",
        retrieved_chunks: [{ text: "Retail overdraft limits cannot exceed 15,000 AED." }],
        citations: [{ citation_marker: "1", document_id: "doc-1", chunk_index: 0 }],
        latency_ms: 115.0,
        created_at: new Date().toISOString(),
        metrics: [
          {
            id: "m-1",
            case_result_id: "cr-1",
            metric_key: "exact_match",
            raw_score: 1.0,
            normalized_score: 100.0,
            score_scale: "ZERO_TO_ONE",
            status: "COMPLETED",
            evaluator_version: "1.0.0",
            details: {},
            created_at: new Date().toISOString(),
          },
        ],
      },
    ],
  },
];

describe("Evaluation Centre Frontend", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    vi.spyOn(evalApi, "fetchSuites").mockResolvedValue(mockSuites);
    vi.spyOn(evalApi, "fetchSuite").mockResolvedValue(mockSuites[0]);
    vi.spyOn(evalApi, "fetchCases").mockResolvedValue(mockCases);
    vi.spyOn(evalApi, "fetchSuiteVersions").mockResolvedValue([
      {
        id: "ver-101",
        suite_id: "suite-101",
        version_number: 1,
        canonical_digest_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        case_count: 12,
        rubric_id: "rub-1",
        rubric_version: 1,
        created_by: "u-1",
        created_at: new Date().toISOString(),
      },
    ]);
    vi.spyOn(evalApi, "fetchRuns").mockResolvedValue(mockRuns);
    vi.spyOn(evalApi, "fetchRun").mockResolvedValue(mockRuns[0]);
  });

  it("renders EvaluationOverviewPage with KPIs, suites and launch actions", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <EvaluationOverviewPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(screen.getByText("Evaluation Centre")).toBeInTheDocument();
    expect(screen.getByText(/Gate 1 Guarded/i)).toBeInTheDocument();
    expect(screen.getByText("New Evaluation Suite")).toBeInTheDocument();
    expect(screen.getByText("Run Benchmark")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Corporate Credit Policies 2026")).toBeInTheDocument();
      expect(screen.getByText(/Banking & Compliance/i)).toBeInTheDocument();
      expect(screen.getByText(/12 Cases/i)).toBeInTheDocument();
    });

    // Switch to Benchmark Runs tab
    fireEvent.click(screen.getByRole("button", { name: /Benchmark Runs/i }));

    await waitFor(() => {
      expect(screen.getByText("Mizan Free Local Baseline")).toBeInTheDocument();
      expect(screen.getByText("91.5%")).toBeInTheDocument();
    });
  });

  it("renders EvaluationSuiteDetailPage with version banner, case list, and review drawer", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/evaluation/suites/suite-101"]}>
          <Routes>
            <Route
              path="/evaluation/suites/:suiteId"
              element={<EvaluationSuiteDetailPage />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Corporate Credit Policies 2026")).toBeInTheDocument();
      expect(screen.getByText(/Version 1 Attested/i)).toBeInTheDocument();
      expect(screen.getByText(/e3b0c44298fc/i)).toBeInTheDocument();
    });

    // Check cases
    expect(screen.getByText("What is the maximum overdraft limit for retail accounts?")).toBeInTheDocument();
    expect(screen.getByText("What is the cryptocurrency margin trading rate?")).toBeInTheDocument();

    // Open review modal
    const reviewButtons = screen.getAllByRole("button", { name: /Review/i });
    fireEvent.click(reviewButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Review Examination Case")).toBeInTheDocument();
      expect(screen.getByText("Review Action")).toBeInTheDocument();
    });
  });

  it("renders EvaluationRunPage with 91.5% score, 11-metric scorecard, and drilldown", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/evaluation/runs/run-999"]}>
          <Routes>
            <Route path="/evaluation/runs/:runId" element={<EvaluationRunPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Mizan Free Local Baseline")).toBeInTheDocument();
      expect(screen.getByText("91.5%")).toBeInTheDocument();
      expect(screen.getByText("Production Ready")).toBeInTheDocument();
      expect(screen.getByText(/0 Leaks/i)).toBeInTheDocument();
    });

    // Check 11-metric breakdown cards
    expect(screen.getByText("Groundedness")).toBeInTheDocument();
    expect(screen.getByText("Faithfulness")).toBeInTheDocument();
    expect(screen.getByText("Appropriate Abstention")).toBeInTheDocument();

    // Check export buttons
    expect(screen.getByText("JSON Report")).toBeInTheDocument();
    expect(screen.getByText("Markdown")).toBeInTheDocument();
    expect(screen.getByText("CSV")).toBeInTheDocument();
  });
});
