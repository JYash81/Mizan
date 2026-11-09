import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { ArtifactRegistryOverviewPage } from "./pages/ArtifactRegistryOverviewPage";
import { ModelVersionDetailPage } from "./pages/ModelVersionDetailPage";
import * as regApi from "./api";
import type { ModelFamily } from "./types";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    activeWorkspace: { id: "ws-test-123", name: "AI Innovation Lab" },
    user: { id: "u-reviewer", email: "lead.engineer@mizan.org" },
  }),
}));

const mockFamilies: ModelFamily[] = [
  {
    id: "fam-1",
    organization_id: "org-1",
    workspace_id: "ws-test-123",
    name: "Customer Support Assistant",
    slug: "customer-support-assistant",
    description: "Fine-tuned conversational assistant for tier-1 support",
    task_type: "TEXT_GENERATION",
    status: "ACTIVE",
    created_by: "u-creator",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    versions: [
      {
        id: "ver-100",
        family_id: "fam-1",
        version_tag: "v1.0.0",
        description: "Initial LoRA adapter fine-tuned on approved tickets",
        status: "APPROVED",
        source_model_key: "meta-llama/Llama-3-8B-Instruct",
        source_model_revision: "main",
        recipe_key: "LORA_FINETUNE_SFT_V1",
        base_evaluation_score: 0.74,
        final_evaluation_score: 0.85,
        quality_delta: 0.11,
        min_ram_mb: 16384,
        min_vram_mb: 8192,
        target_hardware_key: "NVIDIA_T4_16GB",
        release_manifest_digest: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        created_by: "u-creator",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        is_immutable: true,
        artifacts: [
          {
            id: "art-1",
            artifact_type: "LORA_ADAPTER",
            format: "SAFETENSORS",
            file_size_bytes: 104857600,
            sha256: "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
            storage_reference: "releases/fam-1/v1.0.0/adapter.safetensors",
            is_verified: true,
            is_primary_weights: true,
            created_at: new Date().toISOString(),
          },
        ],
        gate3_approval: {
          id: "g3-app-1",
          model_version_id: "ver-100",
          release_manifest_digest: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          decision: "APPROVED",
          decision_reason: "Evaluation checks and safety guardrails fully satisfied",
          reviewer_user_id: "u-reviewer",
          reviewer_role_snapshot: "LEAD_REVIEWER",
          signature_algorithm: "ED25519",
          signature_purpose: "GATE3_RELEASE_APPROVAL",
          signing_key_id: "key-123",
          approval_signature: "mock-ed25519-sig",
          reviewed_at: new Date().toISOString(),
        },
        provenance_summary: {
          checks: {
            BASE_MODEL_LICENSE: { passed: true, details: { license: "Llama-3-Community" } },
            DATASET_GATE1_DATA_RIGHTS: { passed: true, details: { gate1_id: "gate1-123" } },
            BUILD_MANIFEST_PROVENANCE: { passed: true, details: { recipe: "LORA_FINETUNE_SFT_V1" } },
            EVALUATION_EVIDENCE: { passed: true, details: { delta: 0.11 } },
            HARDWARE_FEASIBILITY: { passed: true, details: { status: "FEASIBLE" } },
          },
          warnings: [],
          blockers: [],
        },
        release_events: [
          {
            id: "evt-1",
            event_type: "VERSION_CREATED",
            triggered_by_user_id: "u-creator",
            message: "Model version v1.0.0 initialized",
            metadata_json: "{}",
            created_at: new Date().toISOString(),
          },
          {
            id: "evt-2",
            event_type: "GATE3_APPROVED",
            triggered_by_user_id: "u-reviewer",
            message: "Gate 3 release approved with Ed25519 digital signature",
            metadata_json: "{}",
            created_at: new Date().toISOString(),
          },
        ],
      },
    ],
  },
];

describe("Milestone 11 Artifact Registry & Gate 3 Frontend", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.clearAllMocks();

    vi.spyOn(regApi, "fetchModelFamilies").mockResolvedValue(mockFamilies);
    vi.spyOn(regApi, "fetchGate3Approvals").mockResolvedValue([]);
    vi.spyOn(regApi, "fetchModelVersion").mockResolvedValue(mockFamilies[0].versions![0]);
  });

  it("renders the Artifact Registry Overview with KPIs and version tables", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/artifact-registry"]}>
          <Routes>
            <Route path="/artifact-registry" element={<ArtifactRegistryOverviewPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(
      await screen.findByText(/Artifact Registry & Release Management/i)
    ).toBeInTheDocument();

    // Check KPIs
    expect(screen.getByText("Model Families")).toBeInTheDocument();
    expect(screen.getByText("Customer Support Assistant")).toBeInTheDocument();
    expect(screen.getByText("v1.0.0")).toBeInTheDocument();
    expect(screen.getByText("meta-llama/Llama-3-8B-Instruct")).toBeInTheDocument();
    expect(screen.getByText("Approved")).toBeInTheDocument();
  });

  it("renders Model Version Detail Page with 5-Pillar Provenance and tabs", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/artifact-registry/ver-100"]}>
          <Routes>
            <Route path="/artifact-registry/:versionId" element={<ModelVersionDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText("v1.0.0")).toBeInTheDocument();
    expect(screen.getByText("Immutable")).toBeInTheDocument();

    // Check 5-Pillars rendered in overview tab
    expect(screen.getByText(/1\. Base Model & License/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. Data Rights & Gate 1/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. Build Manifest & Recipe/i)).toBeInTheDocument();
    expect(screen.getByText(/4\. Evaluation & Quality/i)).toBeInTheDocument();
    expect(screen.getByText(/5\. Hardware Feasibility/i)).toBeInTheDocument();

    // Check Hardware specs
    expect(screen.getByText(/16.0 GB/i)).toBeInTheDocument();
    expect(screen.getByText(/8.0 GB/i)).toBeInTheDocument();
  });

  it("switches to Artifacts and Gate 3 Review Centre tabs seamlessly", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/artifact-registry/ver-100"]}>
          <Routes>
            <Route path="/artifact-registry/:versionId" element={<ModelVersionDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await screen.findByText("v1.0.0");

    // Click Artifacts tab
    const artifactsTab = screen.getByText(/Artifacts \(1\)/i);
    fireEvent.click(artifactsTab);
    expect(screen.getByText("LORA_ADAPTER")).toBeInTheDocument();
    expect(screen.getByText("SAFETENSORS")).toBeInTheDocument();
    expect(screen.getByText("Primary Weights")).toBeInTheDocument();

    // Click Gate 3 Review tab
    const gate3Tab = screen.getByText(/Gate 3 Review Centre/i);
    fireEvent.click(gate3Tab);
    expect(screen.getByText(/Gate 3 Approved & Immutable/i)).toBeInTheDocument();
    expect(screen.getByText(/GATE3_RELEASE_APPROVAL/i)).toBeInTheDocument();
  });
});
