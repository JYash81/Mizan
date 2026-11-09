import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { ModelBuildingOverviewPage } from "./pages/ModelBuildingOverviewPage";
import { ModelBuildingDetailPage } from "./pages/ModelBuildingDetailPage";
import * as mbApi from "./api";
import type {
  ModelSource,
  ModelBuildRecipe,
  ModelBuildRun,
  BuildPreflightResponse,
} from "./types";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    activeWorkspace: { id: "ws-test-123", name: "AI Engineering Lab" },
    user: { id: "u-1", email: "engineer@mizan.org" },
  }),
}));

const mockModels: ModelSource[] = [
  {
    id: "m-tiny",
    model_key: "mizan-test/tiny-llama-35m",
    name: "Tiny Llama 35M (Mizan Test Model)",
    description: "Miniature test model designed for rapid local CPU smoke tests",
    source_repository: "HuggingFace",
    immutable_revision: "rev-35m-abc",
    architecture: "LlamaForCausalLM",
    parameter_count_millions: 35.0,
    context_length: 2048,
    license_id: "Apache-2.0",
    license_status: "APPROVED",
    commercial_use_allowed: true,
    is_gated: false,
    access_status: "OPEN",
    requires_custom_code: false,
    estimated_download_bytes: 70000000,
    is_active: true,
    source_metadata: { num_layers: 8, hidden_size: 512 },
    created_at: new Date().toISOString(),
  },
  {
    id: "m-smollm",
    model_key: "HuggingFaceTB/SmolLM2-135M",
    name: "SmolLM2 135M",
    description: "Compact high-performance small language model",
    source_repository: "HuggingFace",
    immutable_revision: "rev-135m-def",
    architecture: "LlamaForCausalLM",
    parameter_count_millions: 135.0,
    context_length: 2048,
    license_id: "Apache-2.0",
    license_status: "APPROVED",
    commercial_use_allowed: true,
    is_gated: false,
    access_status: "OPEN",
    requires_custom_code: false,
    estimated_download_bytes: 270000000,
    is_active: true,
    source_metadata: { num_layers: 16, hidden_size: 1024 },
    created_at: new Date().toISOString(),
  },
];

const mockRecipes: ModelBuildRecipe[] = [
  {
    id: "r-smoke",
    recipe_key: "SMOKE_TEST_CPU",
    recipe_version: "1.0.0",
    recipe_type: "SMOKE_TEST",
    name: "Deterministic CPU Smoke Test (Local)",
    description: "Safe lightweight local CPU execution with $0 spend",
    supported_architectures: ["LlamaForCausalLM"],
    supported_runtimes: ["CPU"],
    configuration_schema: {},
    default_config: { learning_rate: 0.0002, max_steps: 4 },
    dependency_lock: { torch: "2.5.1" },
    resource_requirements: { requires_gpu: false, max_parameter_count_millions: 150.0 },
    is_executable_locally: true,
    is_active: true,
  },
  {
    id: "r-lora",
    recipe_key: "LORA_COLAB_FREE",
    recipe_version: "1.0.0",
    recipe_type: "LORA_FINETUNE",
    name: "LoRA Adapter Fine-Tuning (Colab Free T4)",
    description: "Parameter-efficient LoRA adapter training in Google Colab Free",
    supported_architectures: ["LlamaForCausalLM"],
    supported_runtimes: ["COLAB_FREE_T4"],
    configuration_schema: {},
    default_config: { learning_rate: 0.0002, epochs: 3, lora_rank: 16 },
    dependency_lock: { torch: "2.5.1", peft: "0.13.2" },
    resource_requirements: { requires_gpu: true, max_parameter_count_millions: 3000.0 },
    is_executable_locally: false,
    is_active: true,
  },
];

const mockPreflight: BuildPreflightResponse = {
  model_key: "mizan-test/tiny-llama-35m",
  recipe_key: "SMOKE_TEST_CPU",
  execution_mode: "LOCAL_SMOKE_TEST",
  target_hardware_profile: "LOCAL_CPU_I5_8GB",
  hardware_name: "Local Workstation (Intel Core i5, 8 GB RAM)",
  weight_memory_mb: 70.0,
  kv_cache_mb: 8.0,
  peak_memory_mb: 256.0,
  download_size_mb: 67.0,
  total_disk_required_mb: 2200.0,
  feasibility_status: "FEASIBLE_ESTIMATE",
  is_feasible: true,
  block_reasons: [],
  evidence_type: "ESTIMATED",
};

const mockRuns: ModelBuildRun[] = [
  {
    id: "run-101",
    organization_id: "org-1",
    workspace_id: "ws-test-123",
    created_by: "u-1",
    name: "Tiny Llama Local Smoke Test",
    description: "Local CPU deterministic validation",
    status: "COMPLETED",
    execution_mode: "LOCAL_SMOKE_TEST",
    source_model_id: "m-tiny",
    source_revision: "rev-35m-abc",
    recipe_id: "r-smoke",
    recipe_key: "SMOKE_TEST_CPU",
    manifest_digest: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    training_config: { learning_rate: 0.0002, max_steps: 4 },
    build_manifest: { model_key: "mizan-test/tiny-llama-35m" },
    preflight_snapshot: mockPreflight as unknown as Record<string, unknown>,
    warnings: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    checkpoints: [
      {
        id: "chk-1",
        build_run_id: "run-101",
        checkpoint_number: 1,
        step_number: 4,
        epoch: 1.0,
        storage_reference: "artifacts/checkpoints/chk-1.pt",
        sha256: "chksha123",
        configuration_digest: "cfg123",
        metrics: { train_loss: 0.42 },
        created_at: new Date().toISOString(),
      },
    ],
    staged_artifacts: [
      {
        id: "art-1",
        build_run_id: "run-101",
        artifact_type: "LORA_ADAPTER",
        format: "SAFETENSORS",
        storage_reference: "artifacts/staged/adapter_run-101.safetensors",
        file_size_bytes: 2048576,
        sha256: "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        source_model_key: "mizan-test/tiny-llama-35m",
        source_model_revision: "rev-35m-abc",
        manifest_digest: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        verification_status: "VERIFIED",
        verification_details: { format: "SAFETENSORS", verified: true },
        is_staged_for_m11: true,
        created_at: new Date().toISOString(),
      },
    ],
    evaluation_links: [
      {
        id: "eval-link-1",
        build_run_id: "run-101",
        staged_artifact_id: "art-1",
        evaluation_run_id: "eval-run-99",
        model_role: "FINE_TUNED_MODEL",
        evaluation_suite_id: "suite-1",
        evaluation_split: "VALIDATION",
        overall_score: 0.85,
        quality_delta: 0.05,
        latency_delta_ms: -12.0,
        memory_delta_mb: 2.0,
        comparison_summary: {
          overall_score: 0.85,
          base_score: 0.80,
          quality_delta: 0.05,
          is_regression: false,
        },
        created_at: new Date().toISOString(),
      },
      {
        id: "eval-link-2",
        build_run_id: "run-101",
        staged_artifact_id: "art-1",
        evaluation_run_id: "eval-run-100",
        model_role: "QUANTIZED_MODEL",
        evaluation_suite_id: "suite-1",
        evaluation_split: "VALIDATION",
        overall_score: 0.74,
        quality_delta: -0.06,
        comparison_summary: {
          overall_score: 0.74,
          base_score: 0.80,
          quality_delta: -0.06,
          is_regression: true,
        },
        created_at: new Date().toISOString(),
      },
    ],
  },
];

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/workspaces/ws-test-123/model-building"]}>
        <Routes>
          <Route
            path="/workspaces/:workspaceId/model-building"
            element={ui}
          />
          <Route
            path="/workspaces/:workspaceId/model-building/:runId"
            element={<ModelBuildingDetailPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Milestone 10: Model Building & Colab Lab Frontend", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(mbApi, "fetchBuildRuns").mockResolvedValue(mockRuns);
    vi.spyOn(mbApi, "fetchModelSources").mockResolvedValue(mockModels);
    vi.spyOn(mbApi, "fetchBuildRecipes").mockResolvedValue(mockRecipes);
    vi.spyOn(mbApi, "fetchExternalAuthorizations").mockResolvedValue([]);
    vi.spyOn(mbApi, "runBuildPreflight").mockResolvedValue(mockPreflight);
    vi.spyOn(mbApi, "fetchBuildRun").mockResolvedValue(mockRuns[0]);
    vi.spyOn(mbApi, "executeLocalSmokeTest").mockResolvedValue({
      ...mockRuns[0],
      status: "COMPLETED",
    });
  });

  it("renders the Model Building overview page with stats, run table, and action buttons", async () => {
    renderWithClient(<ModelBuildingOverviewPage />);

    expect(await screen.findByText("Model Building & Colab Lab")).toBeInTheDocument();
    expect(screen.getByText("Total Build Runs")).toBeInTheDocument();
    expect(screen.getByText("Completed Builds")).toBeInTheDocument();
    expect(screen.getByText("Staged Model Artifacts")).toBeInTheDocument();

    // Verify table row rendered
    expect(screen.getByText("Tiny Llama Local Smoke Test")).toBeInTheDocument();
    expect(screen.getByText("SMOKE_TEST_CPU")).toBeInTheDocument();
    expect(screen.getByText("LOCAL_SMOKE_TEST")).toBeInTheDocument();
  });

  it("opens the Model Build Wizard and navigates through model selection and preflight", async () => {
    renderWithClient(<ModelBuildingOverviewPage />);

    const newBuildBtn = await screen.findByTestId("open-build-wizard-btn");
    fireEvent.click(newBuildBtn);

    // Step 1: Model Selection
    expect(await screen.findByText("New Model Build & Adaptation Run")).toBeInTheDocument();
    expect(screen.getByText("Tiny Llama 35M (Mizan Test Model)")).toBeInTheDocument();
    expect(screen.getByText("SmolLM2 135M")).toBeInTheDocument();

    // Move to Step 2
    fireEvent.click(screen.getByText("Next"));
    expect(await screen.findByText("Deterministic CPU Smoke Test (Local)")).toBeInTheDocument();
    expect(screen.getByText("LoRA Adapter Fine-Tuning (Colab Free T4)")).toBeInTheDocument();

    // Move to Step 3
    fireEvent.click(screen.getByText("Next"));
    expect(await screen.findByText("Hyperparameters for Deterministic CPU Smoke Test (Local)")).toBeInTheDocument();

    // Move to Step 4 (Preflight check)
    fireEvent.click(screen.getByText("Next"));
    expect(await screen.findByTestId("preflight-status-feasible")).toBeInTheDocument();
    expect(screen.getByText("FEASIBLE ESTIMATE")).toBeInTheDocument();
    expect(screen.getByText("Peak Working RAM")).toBeInTheDocument();
  });

  it("renders detail page with tabs: Staged Artifacts, Evaluation Regressions, and Checkpoints", async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/workspaces/ws-test-123/model-building/run-101"]}>
          <Routes>
            <Route
              path="/workspaces/:workspaceId/model-building/:runId"
              element={<ModelBuildingDetailPage />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Check title and execution mode
    expect(await screen.findByText("Tiny Llama Local Smoke Test")).toBeInTheDocument();

    // Check Staged Artifacts Tab (default active)
    expect(await screen.findByTestId("staged-artifact-card")).toBeInTheDocument();
    expect(screen.getByText("LORA_ADAPTER")).toBeInTheDocument();
    expect(screen.getByText("SAFETENSORS")).toBeInTheDocument();
    expect(screen.getByText("Staged for M11")).toBeInTheDocument();

    // Switch to Evaluation Tab
    const evalTab = screen.getByTestId("tab-evaluations");
    fireEvent.click(evalTab);

    // Verify both Quality Gain and Quality Regression are rendered visibly
    expect(await screen.findByTestId("evaluation-gain-badge")).toBeInTheDocument();
    expect(screen.getByText("Quality Gain (+5.0%)")).toBeInTheDocument();

    expect(screen.getByTestId("evaluation-regression-badge")).toBeInTheDocument();
    expect(screen.getByText("Quality Regression (-6.0%)")).toBeInTheDocument();
    expect(
      screen.getByText(/Quality loss observed post-quantization\/adaptation/)
    ).toBeInTheDocument();

    // Switch to Checkpoints Tab
    const chkTab = screen.getByTestId("tab-checkpoints");
    fireEvent.click(chkTab);
    expect(await screen.findByText("Checkpoint History")).toBeInTheDocument();
    expect(screen.getByText(/Checkpoint #1/)).toBeInTheDocument();

    // Switch to Manifest & Preflight Tab
    const manifestTab = screen.getByTestId("tab-manifest");
    fireEvent.click(manifestTab);
    expect(await screen.findByText("Canonical Build Manifest (RFC 8785)")).toBeInTheDocument();
    expect(screen.getByText(/e3b0c44298fc/)).toBeInTheDocument();
  });
});
