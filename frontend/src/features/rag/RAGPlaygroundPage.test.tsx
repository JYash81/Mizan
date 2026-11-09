import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RAGPlaygroundPage } from "./pages/RAGPlaygroundPage";
import * as ragApi from "./api";

// Mock AuthContext
vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    activeWorkspace: { id: "ws-test-123", name: "AI Research Lab" },
    user: { id: "u-1", email: "fatima@mizan.ae" },
  }),
}));

describe("RAGPlaygroundPage", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    vi.spyOn(ragApi, "fetchProviders").mockResolvedValue([
      {
        provider_name: "mock",
        is_available: true,
        is_free: true,
        status_message: "Mock provider operational (zero cost, offline)",
        cost_per_million_input_cents: 0.0,
        cost_per_million_output_cents: 0.0,
      },
      {
        provider_name: "ollama",
        is_available: false,
        is_free: true,
        status_message: "Ollama daemon is not reachable",
        cost_per_million_input_cents: 0.0,
        cost_per_million_output_cents: 0.0,
      },
      {
        provider_name: "gemini_free",
        is_available: true,
        is_free: true,
        status_message: "Gemini free-tier operational (15 RPM limit)",
        cost_per_million_input_cents: 0.0,
        cost_per_million_output_cents: 0.0,
      },
    ]);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <RAGPlaygroundPage />
      </QueryClientProvider>
    );

  it("renders Free-Only Architecture Banner and provider cards", async () => {
    renderComponent();

    expect(
      screen.getByText(/Free-Only Architecture Mandate/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/ALLOW_PAID_PROVIDERS: false/i)).toBeInTheDocument();
    expect(
      screen.getByText(/AI Provider & RAG Experimentation Console/i)
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("mock")).toBeInTheDocument();
      expect(screen.getByText("ollama")).toBeInTheDocument();
      expect(screen.getByText("gemini_free")).toBeInTheDocument();
    });
  });

  it("allows selecting different registered providers", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("gemini_free")).toBeInTheDocument();
    });

    const geminiCard = screen.getByText("gemini_free").closest("div");
    if (geminiCard) {
      fireEvent.click(geminiCard);
    }

    expect(screen.getByText("Selected")).toBeInTheDocument();
  });

  it("triggers RAG query and displays synthesized answer with citations", async () => {
    const mockQueryResponse = {
      query: "What are budget rules?",
      answer: "According to document records [Doc: doc-1, Chunk: 0]: Corporate budget approvals exceed 50000 AED.",
      citations: [
        {
          citation_marker: "[Doc: doc-1, Chunk: 0]",
          document_id: "doc-1",
          chunk_index: 0,
          score: 0.94,
          snippet: "Corporate budget approvals exceed 50000 AED require Senior Executive sign-off.",
        },
      ],
      retrieved_chunks: [
        {
          chunk_id: "chk-1",
          document_id: "doc-1",
          chunk_index: 0,
          score: 0.94,
          text: "Corporate budget approvals exceed 50000 AED require Senior Executive sign-off.",
          payload: { is_masked: true },
        },
      ],
      metrics: {
        prompt_tokens: 15,
        completion_tokens: 22,
        total_tokens: 37,
        latency_ms: 12.5,
        cost_cents: 0.0,
      },
      provider: {
        name: "mock",
        model: "mock-gpt-mizan-v1",
      },
    };

    vi.spyOn(ragApi, "queryRAG").mockResolvedValue(mockQueryResponse);

    renderComponent();

    const queryButton = screen.getByRole("button", { name: /Execute RAG Query/i });
    fireEvent.click(queryButton);

    await waitFor(() => {
      expect(
        screen.getAllByText(/Corporate budget approvals exceed 50000 AED/i).length
      ).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("[Doc: doc-1, Chunk: 0]")).toBeInTheDocument();
      expect(screen.getByText(/12.5 ms/i)).toBeInTheDocument();
      expect(screen.getByText(/\$0.00 Free/i)).toBeInTheDocument();
    });
  });

  it("triggers deterministic evaluation and displays quality metrics", async () => {
    const mockQueryResponse = {
      query: "What are budget rules?",
      answer: "According to document records [Doc: doc-1, Chunk: 0]: Corporate budget approvals exceed 50000 AED.",
      citations: [
        {
          citation_marker: "[Doc: doc-1, Chunk: 0]",
          document_id: "doc-1",
          chunk_index: 0,
          score: 0.94,
          snippet: "Corporate budget approvals exceed 50000 AED require Senior Executive sign-off.",
        },
      ],
      retrieved_chunks: [
        {
          chunk_id: "chk-1",
          document_id: "doc-1",
          chunk_index: 0,
          score: 0.94,
          text: "Corporate budget approvals exceed 50000 AED require Senior Executive sign-off.",
          payload: { is_masked: true },
        },
      ],
      metrics: {
        prompt_tokens: 15,
        completion_tokens: 22,
        total_tokens: 37,
        latency_ms: 12.5,
        cost_cents: 0.0,
      },
      provider: {
        name: "mock",
        model: "mock-gpt-mizan-v1",
      },
    };

    const mockEvalResponse = {
      query: "What are budget rules?",
      retrieval_recall: 0.85,
      context_relevance: 1.0,
      faithfulness: 0.92,
      citation_completeness: 1.0,
      overall_score: 0.94,
      citations_count: 1,
      retrieved_chunks_count: 1,
      details: {},
    };

    vi.spyOn(ragApi, "queryRAG").mockResolvedValue(mockQueryResponse);
    vi.spyOn(ragApi, "evaluateRAG").mockResolvedValue(mockEvalResponse);

    renderComponent();

    // 1. Run Query
    const queryButton = screen.getByRole("button", { name: /Execute RAG Query/i });
    fireEvent.click(queryButton);

    await waitFor(() => {
      expect(screen.getByText(/Run Deterministic Quality Evaluation/i)).toBeInTheDocument();
    });

    // 2. Run Evaluation
    const evalButton = screen.getByRole("button", {
      name: /Run Deterministic Quality Evaluation/i,
    });
    fireEvent.click(evalButton);

    await waitFor(() => {
      expect(
        screen.getByText(/RAG Quality Benchmark Scorecard/i)
      ).toBeInTheDocument();
      expect(screen.getByText("94.0%")).toBeInTheDocument();
      expect(screen.getByText("85%")).toBeInTheDocument();
    });
  });
});
