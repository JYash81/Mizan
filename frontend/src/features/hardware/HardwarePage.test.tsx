import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { HardwareCentrePage } from "./pages/HardwareCentrePage";
import * as hwApi from "./api";
import type {
  BenchmarkRun,
  Gate2ApprovalRequest,
  HardwareProfile,
  LocalHardwareSnapshot,
  PricingCatalogEntry,
  QuantizationFormat,
} from "./types";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    activeWorkspace: { id: "ws-test-123", name: "AI Research Lab" },
    user: { id: "u-1", email: "admin@mizan.org" },
  }),
}));

const mockProfiles: HardwareProfile[] = [
  {
    id: "p-1",
    profile_key: "LOCAL_CPU_I5_8GB",
    name: "Local Developer PC (Intel Core i5, 8 GB RAM)",
    category: "LOCAL_WORKSTATION",
    evidence_type: "MEASURED",
    cpu_model: "Intel Core i5-6500",
    system_ram_mb: 8109,
    available_ram_mb: 5037,
    gpu_vram_mb: 0,
    supported_numeric_precisions: ["FP32", "INT8"],
    supported_runtimes: ["ollama", "onnx"],
    supported_quantizations: ["Q4_K_M", "Q8_0"],
    supports_cpu_inference: true,
    supports_gpu_inference: false,
    supports_fine_tuning: false,
    is_reference: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "p-2",
    profile_key: "REFERENCE_CPU_2VCPU_4GB",
    name: "Reference Cloud CPU (2 vCPU, 4 GB RAM)",
    category: "CLOUD_CPU",
    evidence_type: "VENDOR_REFERENCE",
    cpu_model: "Generic Cloud 2 vCPU",
    system_ram_mb: 4096,
    available_ram_mb: 3072,
    gpu_vram_mb: 0,
    supported_numeric_precisions: ["FP32", "INT8"],
    supported_runtimes: ["ollama"],
    supported_quantizations: ["Q4_K_M", "Q8_0"],
    supports_cpu_inference: true,
    supports_gpu_inference: false,
    supports_fine_tuning: false,
    is_reference: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "p-3",
    profile_key: "NVIDIA_T4_16GB",
    name: "NVIDIA T4 Tensor Core (16 GB VRAM)",
    category: "CLOUD_GPU",
    evidence_type: "VENDOR_REFERENCE",
    cpu_model: "Cloud 4 vCPU",
    system_ram_mb: 15360,
    available_ram_mb: 14336,
    gpu_model: "Tesla T4",
    gpu_vram_mb: 16384,
    supported_numeric_precisions: ["FP16", "INT8"],
    supported_runtimes: ["vllm", "transformers"],
    supported_quantizations: ["FP16", "Q8_0", "Q4_K_M", "AWQ"],
    supports_cpu_inference: true,
    supports_gpu_inference: true,
    supports_fine_tuning: true,
    is_reference: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "p-4",
    profile_key: "NVIDIA_A100_40GB",
    name: "NVIDIA A100 Tensor Core (40 GB VRAM)",
    category: "CLOUD_GPU",
    evidence_type: "VENDOR_REFERENCE",
    cpu_model: "High-Memory Host 12 vCPU",
    system_ram_mb: 87040,
    available_ram_mb: 81920,
    gpu_model: "A100-PCIE-40GB",
    gpu_vram_mb: 40960,
    supported_numeric_precisions: ["FP32", "FP16", "BF16"],
    supported_runtimes: ["vllm", "tgi"],
    supported_quantizations: ["FP16", "Q8_0", "Q4_K_M", "AWQ"],
    supports_cpu_inference: true,
    supports_gpu_inference: true,
    supports_fine_tuning: true,
    is_reference: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockSnapshot: LocalHardwareSnapshot = {
  id: "snap-1",
  workspace_id: "ws-test-123",
  user_id: "u-1",
  cpu_model: "Intel Core i5-6500 @ 3.20GHz",
  physical_cores: 4,
  logical_cores: 4,
  system_ram_mb: 8109,
  available_ram_mb: 5037,
  os_name: "Windows",
  os_release: "10",
  architecture: "AMD64",
  has_nvidia_gpu: false,
  evidence_type: "MEASURED",
  created_at: new Date().toISOString(),
};

const mockBenchmark: BenchmarkRun = {
  id: "bench-1",
  benchmark_name: "Safe CPU Bounded Benchmark",
  duration_ms: 125.4,
  operations_per_second: 54000000.0,
  ram_before_mb: 8109,
  ram_after_mb: 8109,
  evidence_type: "MEASURED",
  status: "COMPLETED",
  limitations: "Bounded scalar CPU arithmetic test.",
  started_at: new Date().toISOString(),
  completed_at: new Date().toISOString(),
  created_at: new Date().toISOString(),
};

const mockQuantizations: QuantizationFormat[] = [
  {
    id: "FP16",
    format_key: "FP16",
    format_family: "FLOAT",
    nominal_bits: 16.0,
    effective_reference_bits: 16.0,
    runtime_requirements: ["pytorch"],
    supported_hardware: ["CPU", "GPU"],
    calculation_assumptions: "16 bits/param",
    limitations: "Large footprint",
    source_reference: "IEEE 754",
    registry_version: "1.0.0",
  },
  {
    id: "Q4_K_M",
    format_key: "Q4_K_M",
    format_family: "GGUF",
    nominal_bits: 4.0,
    effective_reference_bits: 4.9,
    runtime_requirements: ["llama.cpp"],
    supported_hardware: ["CPU", "GPU"],
    calculation_assumptions: "4.9 bits/param average",
    limitations: "Small perplexity delta",
    source_reference: "llama.cpp",
    registry_version: "1.0.0",
  },
];

const mockCatalog: PricingCatalogEntry[] = [
  {
    id: "price-1",
    provider_name: "local",
    resource_type: "WORKSTATION",
    instance_type: "local-i5",
    region: "local",
    currency: "USD",
    hourly_rate: "0.00",
    billing_unit_seconds: 3600,
    provenance: "OFFICIAL_SOURCE",
    effective_from: new Date().toISOString(),
    is_verified: true,
    catalog_version: "2026.1",
  },
  {
    id: "price-2",
    provider_name: "gcp",
    resource_type: "GPU_VM",
    instance_type: "n1-standard-4-t4-16gb",
    region: "us-central1",
    currency: "USD",
    hourly_rate: "0.526",
    billing_unit_seconds: 3600,
    provenance: "REFERENCE_ONLY",
    effective_from: new Date().toISOString(),
    is_verified: true,
    catalog_version: "2026.1",
  },
];

const mockGate2Requests: Gate2ApprovalRequest[] = [
  {
    id: "g2-req-1",
    organization_id: "org-1",
    workspace_id: "ws-test-123",
    requester_id: "u-1",
    title: "Test Workload Evaluation",
    purpose: "Evaluate model on local hardware",
    workload_type: "EXPERIMENT_EVALUATION",
    hardware_profile_key: "LOCAL_CPU_I5_8GB",
    provider_name: "local",
    instance_type: "local-i5",
    region: "local",
    estimated_duration_hours: 2.0,
    max_duration_hours: 3.0,
    estimated_compute_cost: "0.00",
    estimated_storage_cost: "0.00",
    estimated_total_cost: "0.00",
    max_authorized_budget: "0.00",
    currency: "USD",
    proposal_digest: "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
    proposal_payload_json: "{}",
    pricing_snapshot_json: "{}",
    pricing_catalog_version: "2026.1",
    status: "APPROVED",
    approval_signature: "sig12345",
    expires_at: new Date(Date.now() + 86400000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    events: [],
  },
];

describe("Hardware & Gate 2 Centre Frontend Page", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.clearAllMocks();

    vi.spyOn(hwApi, "fetchHardwareProfiles").mockResolvedValue(mockProfiles);
    vi.spyOn(hwApi, "fetchLatestHardwareSnapshot").mockResolvedValue(mockSnapshot);
    vi.spyOn(hwApi, "fetchLatestBenchmark").mockResolvedValue(mockBenchmark);
    vi.spyOn(hwApi, "fetchQuantizations").mockResolvedValue(mockQuantizations);
    vi.spyOn(hwApi, "fetchPricingCatalog").mockResolvedValue(mockCatalog);
    vi.spyOn(hwApi, "fetchGate2Requests").mockResolvedValue(mockGate2Requests);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <HardwareCentrePage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it("renders page header and reference hardware profile cards", async () => {
    renderComponent();

    expect(
      screen.getByText(/Hardware Knowledge Base & Gate 2 Financial Centre/i)
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getByText(/Local Developer PC \(Intel Core i5, 8 GB RAM\)/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/NVIDIA T4 Tensor Core \(16 GB VRAM\)/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/NVIDIA A100 Tensor Core \(40 GB VRAM\)/i)
      ).toBeInTheDocument();
    });
  });

  it("switches to Local & Benchmark tab and displays host inspection info", async () => {
    renderComponent();

    const localTab = screen.getByRole("button", { name: /Local & Benchmark/i });
    fireEvent.click(localTab);

    await waitFor(() => {
      expect(screen.getByText(/Host Workstation Inspection/i)).toBeInTheDocument();
      expect(screen.getByText(/Safe Opt-In CPU Compute Benchmark/i)).toBeInTheDocument();
      expect(screen.getByText(/Intel Core i5-6500 @ 3.20GHz/i)).toBeInTheDocument();
    });
  });

  it("switches to Cost & Pricing tab and shows Free-Only Policy banner and catalog", async () => {
    renderComponent();

    const costTab = screen.getByRole("button", { name: /Cost & Pricing/i });
    fireEvent.click(costTab);

    await waitFor(() => {
      expect(
        screen.getByText(/Free-Only Infrastructure Policy Active \(\$0\.00 Additional Spend\)/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/Infrastructure Pricing Catalog/i)).toBeInTheDocument();
      expect(screen.getByText(/n1-standard-4-t4-16gb/i)).toBeInTheDocument();
    });
  });

  it("switches to Gate 2 Approvals tab and displays financial approval requests", async () => {
    renderComponent();

    const gate2Tab = screen.getByRole("button", { name: /Gate 2 Approvals/i });
    fireEvent.click(gate2Tab);

    await waitFor(() => {
      expect(
        screen.getByText(/Gate 2 Financial Approval & Governance/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/Test Workload Evaluation/i)).toBeInTheDocument();
      expect(screen.getByText("APPROVED")).toBeInTheDocument();
    });
  });

  it("keeps the estimator default and every built-in model preset valid", async () => {
    renderComponent();
    fireEvent.click(screen.getByRole("button", { name: /Resource Estimator/i }));

    const defaultParameterInput = (await screen.findByDisplayValue("8000")) as HTMLInputElement;
    expect(defaultParameterInput).toHaveAttribute("step", "10");
    expect(defaultParameterInput.checkValidity()).toBe(true);

    const presets = [
      { label: /1B \(e\.g\. TinyLlama\)/i, value: "1100" },
      { label: /3\.8B \(e\.g\. Phi-3\)/i, value: "3800" },
      { label: /7B \(e\.g\. Mistral\)/i, value: "7000" },
      { label: /8B \(e\.g\. Llama-3\)/i, value: "8000" },
      { label: /70B \(e\.g\. Llama-3 70B\)/i, value: "70000" },
    ];

    for (const preset of presets) {
      fireEvent.click(screen.getByRole("button", { name: preset.label }));
      const parameterInput = (await screen.findByDisplayValue(preset.value)) as HTMLInputElement;
      expect(parameterInput.checkValidity()).toBe(true);
    }
  });

  it("keeps the default two-hour cost duration valid under native step validation", async () => {
    renderComponent();
    fireEvent.click(screen.getByRole("button", { name: /Cost & Pricing/i }));

    const durationInput = (await screen.findByDisplayValue("2")) as HTMLInputElement;
    expect(durationInput).toHaveAttribute("min", "0.1");
    expect(durationInput).toHaveAttribute("step", "0.1");
    expect(durationInput.checkValidity()).toBe(true);
  });
});
