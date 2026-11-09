import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { ModelZooPage } from "./pages/ModelZooPage";
import { ModelDetailPage } from "./pages/ModelDetailPage";
import { AppZooPage } from "./pages/AppZooPage";
import { AppDetailPage } from "./pages/AppDetailPage";
import { CatalogManagePage } from "./pages/CatalogManagePage";
import { HardwareBadgePill } from "./components/HardwareBadgePill";
import { InstallationSnippetViewer } from "./components/InstallationSnippetViewer";
import * as zooApi from "./api";
import * as regApi from "../artifact-registry/api";
import type {
  AppListingDetail,
  AppListingSummary,
  ModelListingDetail,
  ModelListingSummary,
} from "./types";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    activeWorkspace: { id: "ws-test-123", name: "AI Innovation Lab" },
    activeOrganization: { id: "org-123", name: "Acme Corp" },
    user: { id: "u-publisher", email: "catalog.lead@mizan.org" },
  }),
}));

const mockModelSummaries: ModelListingSummary[] = [
  {
    id: "listing-model-1",
    organization_id: "org-123",
    workspace_id: "ws-test-123",
    model_family_id: "fam-1",
    model_version_id: "ver-1",
    title: "Customer Support Llama 3",
    slug: "customer-support-llama-3",
    description: "Fine-tuned conversational support model with high accuracy.",
    category: "CUSTOMER_SUPPORT",
    tags: ["support", "llama3", "lora"],
    visibility: "ORGANIZATION",
    publication_status: "PUBLISHED",
    distribution_status: "DOWNLOADABLE",
    publication_digest: "pub_digest_1111111111111111111111111111111111111111111111111111111111111111",
    is_featured: true,
    created_at: new Date().toISOString(),
    published_at: new Date().toISOString(),
    model_family_name: "Support LLM Family",
    model_family_slug: "support-llm-family",
    version_tag: "v1.0.0",
    source_model_key: "meta-llama/Llama-3-8B-Instruct",
    final_evaluation_score: 0.88,
  },
];

const mockModelDetail: ModelListingDetail = {
  listing: {
    id: "listing-model-1",
    title: "Customer Support Llama 3",
    slug: "customer-support-llama-3",
    description: "Fine-tuned conversational support model with high accuracy.",
    detailed_description: "Extended instructions on usage, prompting guidelines, and token budget limits.",
    category: "CUSTOMER_SUPPORT",
    tags: ["support", "llama3", "lora"],
    visibility: "ORGANIZATION",
    publication_status: "PUBLISHED",
    distribution_status: "DOWNLOADABLE",
    publication_digest: "pub_digest_1111111111111111111111111111111111111111111111111111111111111111",
    created_at: new Date().toISOString(),
    published_at: new Date().toISOString(),
  },
  model_family: {
    id: "fam-1",
    name: "Support LLM Family",
    slug: "support-llm-family",
    task_type: "TEXT_GENERATION",
  },
  model_version: {
    id: "ver-1",
    version_tag: "v1.0.0",
    source_model_key: "meta-llama/Llama-3-8B-Instruct",
    source_model_revision: "main",
    recipe_key: "LORA_FINETUNE_SFT_V1",
    base_evaluation_score: 0.74,
    final_evaluation_score: 0.88,
    quality_delta: 0.14,
    min_ram_mb: 8192,
    min_vram_mb: 4096,
    target_hardware_key: "LOCAL_CPU",
    release_manifest_digest: "release_manifest_digest_abc1234567890abcdef1234567890abcdef12345678",
  },
  artifacts: [
    {
      id: "art-1",
      artifact_type: "LORA_ADAPTER",
      format: "SAFETENSORS",
      file_size_bytes: 104857600,
      sha256: "sha256_mock_adapter_digest_1234567890abcdef1234567890abcdef12345678",
      is_primary_weights: true,
    },
  ],
  hardware_badges: [
    {
      badge: "TESTED",
      hardware_name: "Local CPU Workstation",
      category: "LOCAL_WORKSTATION",
      evidence_type: "MEASURED",
      measured_throughput_tokens_per_sec: 24.5,
    },
    {
      badge: "ESTIMATED",
      hardware_name: "NVIDIA T4 16GB",
      category: "CLOUD_GPU",
      evidence_type: "M8_CALCULATED",
    },
  ],
  installation_snippets: {
    python_transformers: "from peft import PeftModel\n# Governance manifest pinned",
    llamacpp_cli: "./llama-cli -m model.gguf --lora adapter.bin",
    m13_serving_spec: "# M13 Serving Spec Notice",
  },
  version_history: [
    {
      id: "ver-1",
      version_tag: "v1.0.0",
      status: "APPROVED",
      created_at: new Date().toISOString(),
      release_manifest_digest: "release_manifest_digest_abc1234567890abcdef1234567890abcdef12345678",
    },
  ],
};

const mockAppSummaries: AppListingSummary[] = [
  {
    id: "listing-app-1",
    organization_id: "org-123",
    workspace_id: "ws-test-123",
    app_definition_id: "def-1",
    app_version_id: "aver-1",
    title: "Contract Analyzer App",
    slug: "contract-analyzer-app",
    description: "Automated legal clause analysis and risk classification.",
    category: "LEGAL_ANALYSIS",
    tags: ["legal", "contracts", "compliance"],
    visibility: "ORGANIZATION",
    publication_status: "PUBLISHED",
    distribution_status: "METADATA_ONLY",
    publication_digest: "app_pub_digest_22222222222222222222222222222222222222222222222222222222",
    is_featured: false,
    created_at: new Date().toISOString(),
    published_at: new Date().toISOString(),
    app_name: "Contract Analyzer",
    app_key: "contract-analyzer",
    version_tag: "v1.0.0",
    dependency_count: 1,
  },
];

const mockAppDetail: AppListingDetail = {
  listing: {
    id: "listing-app-1",
    title: "Contract Analyzer App",
    slug: "contract-analyzer-app",
    description: "Automated legal clause analysis and risk classification.",
    detailed_description: "Extracts NDA terms and indemnification clauses.",
    category: "LEGAL_ANALYSIS",
    tags: ["legal", "contracts"],
    visibility: "ORGANIZATION",
    publication_status: "PUBLISHED",
    distribution_status: "METADATA_ONLY",
    publication_digest: "app_pub_digest_22222222222222222222222222222222222222222222222222222222",
    created_at: new Date().toISOString(),
    published_at: new Date().toISOString(),
  },
  app_definition: {
    id: "def-1",
    name: "Contract Analyzer",
    app_key: "contract-analyzer",
    category: "LEGAL_ANALYSIS",
  },
  app_version: {
    id: "aver-1",
    version_tag: "v1.0.0",
    manifest_digest: "app_manifest_digest_333333333333333333333333333333333333333333333333",
    license_id: "Apache-2.0",
    capabilities: ["DOCUMENT_RETRIEVAL", "SUMMARIZATION", "CLAUSE_EXTRACTION"],
    supported_input_types: ["PDF", "TXT", "DOCX"],
    supported_output_types: ["JSON", "MARKDOWN"],
    supported_languages: ["en", "ar"],
    min_ram_mb: 8192,
    min_vram_mb: 0,
    target_hardware_key: "LOCAL_CPU",
  },
  dependencies: [
    {
      id: "dep-1",
      model_family_id: "fam-1",
      model_version_id: "ver-1",
      release_manifest_digest: "release_manifest_digest_abc1234567890abcdef1234567890abcdef12345678",
      dependency_role: "PRIMARY_GENERATOR",
      model_family_name: "Support LLM Family",
      model_version_tag: "v1.0.0",
    },
  ],
  hardware_badges: [
    {
      badge: "TESTED",
      hardware_name: "Local CPU Workstation",
      category: "LOCAL_WORKSTATION",
      evidence_type: "MEASURED",
    },
  ],
  installation_snippets: {
    declarative_app_manifest: '{\n  "app_key": "contract-analyzer",\n  "version": "v1.0.0"\n}',
    api_curl_binding: "curl -X POST http://localhost:8000/api/v1/apps/contract-analyzer/execute",
  },
  version_history: [
    {
      id: "aver-1",
      version_tag: "v1.0.0",
      status: "ACTIVE",
      manifest_digest: "app_manifest_digest_333333333333333333333333333333333333333333333333",
      created_at: new Date().toISOString(),
    },
  ],
};

describe("Milestone 12: Model Zoo and App Zoo Frontend", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.clearAllMocks();

    vi.spyOn(zooApi, "discoverModels").mockResolvedValue({
      items: mockModelSummaries,
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });

    vi.spyOn(zooApi, "getModelDetail").mockResolvedValue(mockModelDetail);

    vi.spyOn(zooApi, "discoverApps").mockResolvedValue({
      items: mockAppSummaries,
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });

    vi.spyOn(zooApi, "getAppDetail").mockResolvedValue(mockAppDetail);

    vi.spyOn(zooApi, "fetchWorkspaceModelListings").mockResolvedValue(mockModelSummaries);
    vi.spyOn(zooApi, "fetchWorkspaceAppListings").mockResolvedValue(mockAppSummaries);
    vi.spyOn(zooApi, "fetchWorkspaceAppDefinitions").mockResolvedValue([]);
    vi.spyOn(regApi, "fetchModelFamilies").mockResolvedValue([]);
  });

  it("renders the Model Zoo discovery page with search and model cards", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/zoo/models"]}>
          <Routes>
            <Route path="/zoo/models" element={<ModelZooPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText("Model Zoo")).toBeInTheDocument();
    expect(await screen.findByText("Customer Support Llama 3")).toBeInTheDocument();
    expect(screen.getByText(/Gate 3 Approved/i)).toBeInTheDocument();
    expect(screen.getByText("v1.0.0")).toBeInTheDocument();
  });

  it("renders the Model Detail page with specs, hardware badges, and installation guide", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/zoo/models/listing-model-1"]}>
          <Routes>
            <Route path="/zoo/models/:listingId" element={<ModelDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText("Customer Support Llama 3")).toBeInTheDocument();
    expect(screen.getByText("meta-llama/Llama-3-8B-Instruct")).toBeInTheDocument();
    expect(screen.getByText("LORA_FINETUNE_SFT_V1")).toBeInTheDocument();

    // Switch to Hardware Matrix tab
    const hwTab = screen.getByText(/Hardware Matrix/i);
    fireEvent.click(hwTab);
    expect(screen.getByText("TESTED")).toBeInTheDocument();
    expect(screen.getByText(/Local CPU Workstation/i)).toBeInTheDocument();

    // Switch to Installation Guides tab
    const installTab = screen.getByText(/Installation Guides/i);
    fireEvent.click(installTab);
    expect(screen.getByText(/Python \(Transformers\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Deterministic installation specification/i)).toBeInTheDocument();
  });

  it("renders the App Zoo discovery page with app cards", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/zoo/apps"]}>
          <Routes>
            <Route path="/zoo/apps" element={<AppZooPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText("App Zoo")).toBeInTheDocument();
    expect(await screen.findByText("Contract Analyzer App")).toBeInTheDocument();
    expect(screen.getByText(/Declarative Manifest/i)).toBeInTheDocument();
  });

  it("renders the App Detail page with capabilities and bound model releases", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/zoo/apps/listing-app-1"]}>
          <Routes>
            <Route path="/zoo/apps/:listingId" element={<AppDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText("Contract Analyzer App")).toBeInTheDocument();
    expect(screen.getByText("CLAUSE_EXTRACTION")).toBeInTheDocument();
    expect(screen.getByText("DOCUMENT_RETRIEVAL")).toBeInTheDocument();

    // Switch to Bound Models tab
    const modelsTab = screen.getByText(/Bound Models \(1\)/i);
    fireEvent.click(modelsTab);
    expect(screen.getByText("Support LLM Family")).toBeInTheDocument();
    expect(screen.getByText("PRIMARY_GENERATOR")).toBeInTheDocument();
  });

  it("renders the Catalog Publisher Hub management dashboard", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/zoo/manage"]}>
          <Routes>
            <Route path="/zoo/manage" element={<CatalogManagePage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText("Catalog Publisher Hub")).toBeInTheDocument();
    expect(await screen.findByText("Customer Support Llama 3")).toBeInTheDocument();
    expect(screen.getByText("PUBLISHED")).toBeInTheDocument();
  });

  it("correctly renders HardwareBadgePill semantics for all 4 badge states", () => {
    const { rerender } = render(<HardwareBadgePill badge="TESTED" hardwareName="MacBook Pro M3" />);
    expect(screen.getByText("TESTED")).toBeInTheDocument();
    expect(screen.getByText(/MacBook Pro M3/i)).toBeInTheDocument();

    rerender(<HardwareBadgePill badge="ESTIMATED" hardwareName="A100 80GB" />);
    expect(screen.getByText("ESTIMATED")).toBeInTheDocument();

    rerender(<HardwareBadgePill badge="INCOMPATIBLE" hardwareName="Raspberry Pi" />);
    expect(screen.getByText("INCOMPATIBLE")).toBeInTheDocument();

    rerender(<HardwareBadgePill badge="UNKNOWN" hardwareName="Custom ASIC" />);
    expect(screen.getByText("UNKNOWN")).toBeInTheDocument();
  });

  it("InstallationSnippetViewer enforces safety callout and supports snippet copy", () => {
    render(
      <InstallationSnippetViewer
        snippets={{
          python_transformers: "import torch\nprint('hello')",
          llamacpp_cli: "./llama-cli -m model.gguf",
        }}
      />
    );

    expect(
      screen.getByText(/Deterministic installation specification pinned to release manifest digest/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Copy/i)).toBeInTheDocument();
  });
});
