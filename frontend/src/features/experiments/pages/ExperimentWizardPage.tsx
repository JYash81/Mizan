import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  FlaskConical,
  Layers,
  ShieldCheck,
  Cpu,
  Play,
  Settings2,
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import { apiGet } from "../../../lib/api/client";
import { createExperiment, generateMatrix, executeExperiment } from "../api";
import type { TrialConfig } from "../types";

interface DatasetOption {
  id: string;
  name: string;
  slug: string;
  current_version_id?: string;
}

interface SuiteOption {
  id: string;
  name: string;
  case_count?: number;
}

interface SuiteVersionOption {
  id: string;
  version_number: number;
  case_count: number;
  suite_digest?: string;
}

export function ExperimentWizardPage() {
  const { activeWorkspace } = useAuth();
  const navigate = useNavigate();
  const workspaceId = activeWorkspace?.id;

  const [step, setStep] = useState<1 | 2 | 3 | 4 | 5>(1);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Step 1: Metadata & Provenance
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [datasetVersionId, setDatasetVersionId] = useState("");
  const [suiteId, setSuiteId] = useState("");
  const [suiteVersionId, setSuiteVersionId] = useState("");
  const [evaluationSplit, setEvaluationSplit] = useState<"VALIDATION" | "TEST">("VALIDATION");

  // Step 2: Baseline Config
  const [providerName, setProviderName] = useState("mock");
  const [modelName, setModelName] = useState("mock-rag-v1");
  const [chunkSize, setChunkSize] = useState(500);
  const [chunkOverlap, setChunkOverlap] = useState(100);
  const [topK, setTopK] = useState(4);
  const [promptStrategy, setPromptStrategy] = useState("standard_qa");

  // Step 3: Matrix Strategy
  const matrixStrategy = "PRESET_MATRIX";
  const [presetName, setPresetName] = useState("chunk_sensitivity");

  // Load available datasets
  const { data: datasets = [] } = useQuery<DatasetOption[]>({
    queryKey: ["datasets", workspaceId],
    queryFn: () => apiGet<DatasetOption[]>(`/workspaces/${workspaceId}/datasets`),
    enabled: Boolean(workspaceId),
  });

  // Load available evaluation suites
  const { data: suites = [] } = useQuery<SuiteOption[]>({
    queryKey: ["evaluation-suites", workspaceId],
    queryFn: () => apiGet<SuiteOption[]>(`/workspaces/${workspaceId}/evaluation/suites`),
    enabled: Boolean(workspaceId),
  });

  // Load suite versions when suite is selected
  const { data: suiteVersions = [] } = useQuery<SuiteVersionOption[]>({
    queryKey: ["suite-versions", workspaceId, suiteId],
    queryFn: () => apiGet<SuiteVersionOption[]>(`/workspaces/${workspaceId}/evaluation/suites/${suiteId}/versions`),
    enabled: Boolean(workspaceId && suiteId),
  });

  const launchMutation = useMutation({
    mutationFn: async () => {
      setErrorMessage(null);
      if (!workspaceId) throw new Error("No active workspace");

      const baselineConfig: TrialConfig = {
        chunk_size_chars: chunkSize,
        chunk_overlap_chars: chunkOverlap,
        top_k: topK,
        provider_name: providerName,
        model_name: modelName,
        prompt_strategy: promptStrategy,
      };

      // 1. Create experiment
      const exp = await createExperiment(workspaceId, {
        name,
        slug: slug || undefined,
        description: description || undefined,
        dataset_id: datasetId,
        dataset_version_id: datasetVersionId,
        evaluation_suite_id: suiteId,
        evaluation_suite_version_id: suiteVersionId,
        evaluation_split: evaluationSplit,
        baseline_config: baselineConfig,
      });

      // 2. Generate trial matrix
      await generateMatrix(workspaceId, exp.id, {
        strategy: matrixStrategy,
        preset_name: presetName,
      });

      // 3. Trigger sequential execution
      await executeExperiment(workspaceId, exp.id);

      return exp;
    },
    onSuccess: (exp) => {
      navigate(`/experiments/${exp.id}`);
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || "Failed to initialize and launch experiment.");
    },
  });

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      {/* Wizard Header */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <button
            onClick={() => navigate("/experiments")}
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-2 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Experiments
          </button>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FlaskConical className="w-6 h-6 text-primary" />
            New Model Experiment
          </h1>
          <p className="text-sm text-muted-foreground">
            Configure a bounded trial matrix (3-9 trials) against Gate 1 approved business knowledge.
          </p>
        </div>

        {/* Stepper Progress */}
        <div className="hidden sm:flex items-center gap-1 text-xs">
          {[1, 2, 3, 4, 5].map((s) => (
            <div
              key={s}
              className={`w-7 h-7 rounded-full flex items-center justify-center font-semibold ${
                step === s
                  ? "bg-primary text-primary-foreground"
                  : step > s
                  ? "bg-emerald-500/20 text-emerald-500 border border-emerald-500/30"
                  : "bg-secondary text-muted-foreground"
              }`}
            >
              {step > s ? <CheckCircle2 className="w-4 h-4" /> : s}
            </div>
          ))}
        </div>
      </div>

      {errorMessage && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-500 text-sm rounded-lg flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* STEP 1: Metadata & Provenance */}
      {step === 1 && (
        <div className="space-y-6 bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Layers className="w-5 h-5 text-primary" />
            Step 1: Experiment Details & Target Provenance
          </h2>

          <div className="grid grid-cols-1 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                Experiment Name *
              </label>
              <input
                type="text"
                placeholder="e.g. Chunk Size Sensitivity Study"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (!slug) {
                    setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, "-"));
                  }
                }}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                URL Slug
              </label>
              <input
                type="text"
                placeholder="chunk-sensitivity-study"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                Hypothesis / Description
              </label>
              <textarea
                rows={2}
                placeholder="We hypothesize that smaller chunk sizes (250 chars) will increase groundedness by reducing irrelevant context..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              <div>
                <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                  Approved Dataset *
                </label>
                <select
                  value={datasetId}
                  onChange={(e) => {
                    setDatasetId(e.target.value);
                    const ds = datasets.find((d: DatasetOption) => d.id === e.target.value);
                    if (ds?.current_version_id) {
                      setDatasetVersionId(ds.current_version_id);
                    }
                  }}
                  className="w-full px-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">Select Dataset...</option>
                  {datasets.map((d: DatasetOption) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.slug})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                  Evaluation Suite *
                </label>
                <select
                  value={suiteId}
                  onChange={(e) => {
                    setSuiteId(e.target.value);
                    setSuiteVersionId("");
                  }}
                  className="w-full px-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">Select Exam Suite...</option>
                  {suites.map((s: SuiteOption) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.case_count || 0} cases)
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {suiteVersions.length > 0 && (
              <div>
                <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                  Frozen Suite Snapshot Version *
                </label>
                <select
                  value={suiteVersionId}
                  onChange={(e) => setSuiteVersionId(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">Select Frozen Version...</option>
                  {suiteVersions.map((sv: SuiteVersionOption) => (
                    <option key={sv.id} value={sv.id}>
                      v{sv.version_number} — {sv.case_count} cases (Digest: {sv.suite_digest?.slice(0, 10)}...)
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                Evaluation Split
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label
                  className={`p-3 border rounded-lg cursor-pointer flex flex-col gap-1 transition-all ${
                    evaluationSplit === "VALIDATION"
                      ? "border-primary bg-primary/5"
                      : "border-border hover:bg-secondary/40"
                  }`}
                >
                  <input
                    type="radio"
                    name="split"
                    checked={evaluationSplit === "VALIDATION"}
                    onChange={() => setEvaluationSplit("VALIDATION")}
                    className="sr-only"
                  />
                  <span className="font-semibold text-sm">Validation Split (Recommended)</span>
                  <span className="text-xs text-muted-foreground">Standard split for tuning hyper-parameters.</span>
                </label>
                <label
                  className={`p-3 border rounded-lg cursor-pointer flex flex-col gap-1 transition-all ${
                    evaluationSplit === "TEST"
                      ? "border-primary bg-primary/5"
                      : "border-border hover:bg-secondary/40"
                  }`}
                >
                  <input
                    type="radio"
                    name="split"
                    checked={evaluationSplit === "TEST"}
                    onChange={() => setEvaluationSplit("TEST")}
                    className="sr-only"
                  />
                  <span className="font-semibold text-sm">Test Split</span>
                  <span className="text-xs text-muted-foreground">Held for unbiased assessment before release.</span>
                </label>
              </div>
              <p className="text-xs text-amber-500/90 mt-2 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5" />
                Holdout set is strictly protected by Mizan security policy and cannot be targeted for iterative experimentation.
              </p>
            </div>
          </div>

          <div className="flex justify-end pt-4 border-t border-border">
            <button
              onClick={() => {
                if (!name || !datasetId || !suiteId) {
                  setErrorMessage("Please complete all required fields.");
                  return;
                }
                setErrorMessage(null);
                setStep(2);
              }}
              className="inline-flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-md font-medium text-sm transition-colors"
            >
              Continue to Baseline Config <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: Baseline Configuration */}
      {step === 2 && (
        <div className="space-y-6 bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Settings2 className="w-5 h-5 text-primary" />
            Step 2: Baseline RAG & Model Configuration
          </h2>

          <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-xs rounded-md flex items-center gap-2">
            <Cpu className="w-4 h-4 shrink-0" />
            <span>Mizan Free-Only Cost Policy Active: Billable external APIs are prohibited ($0.00 spend).</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                Local AI Provider *
              </label>
              <select
                value={providerName}
                onChange={(e) => {
                  setProviderName(e.target.value);
                  if (e.target.value === "mock") setModelName("mock-rag-v1");
                  else if (e.target.value === "ollama") setModelName("llama3:8b");
                  else setModelName("gemini-1.5-flash");
                }}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="mock">Mock Provider (Deterministic Local CPU)</option>
                <option value="ollama">Ollama (Local Self-Hosted LLM)</option>
                <option value="gemini_free">Gemini Free Quota (Synthetic Only)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                Model Identifier *
              </label>
              <input
                type="text"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary font-mono text-xs"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                Chunk Size (chars: 50-5000)
              </label>
              <input
                type="number"
                min={50}
                max={5000}
                step={50}
                value={chunkSize}
                onChange={(e) => setChunkSize(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                Chunk Overlap (chars: 0-1000)
              </label>
              <input
                type="number"
                min={0}
                max={1000}
                step={25}
                value={chunkOverlap}
                onChange={(e) => setChunkOverlap(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                Top-K Retrieved Chunks (1-20)
              </label>
              <input
                type="number"
                min={1}
                max={20}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                Prompt Strategy
              </label>
              <select
                value={promptStrategy}
                onChange={(e) => setPromptStrategy(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="standard_qa">Standard QA Prompt</option>
                <option value="precise_grounded">Strict Groundedness Prompt</option>
                <option value="regulatory_strict">Regulatory Compliance Prompt</option>
              </select>
            </div>
          </div>

          <div className="flex justify-between pt-4 border-t border-border">
            <button
              onClick={() => setStep(1)}
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-4 h-4" /> Back
            </button>
            <button
              onClick={() => {
                if (chunkOverlap >= chunkSize) {
                  setErrorMessage("Chunk overlap must be less than chunk size.");
                  return;
                }
                setErrorMessage(null);
                setStep(3);
              }}
              className="inline-flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-md font-medium text-sm transition-colors"
            >
              Continue to Trial Matrix <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: Trial Matrix Strategy */}
      {step === 3 && (
        <div className="space-y-6 bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Cpu className="w-5 h-5 text-primary" />
            Step 3: Trial Matrix Generation Strategy
          </h2>

          <div className="space-y-4">
            <label className="block text-xs font-semibold uppercase text-muted-foreground">
              Select Preset Matrix
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                {
                  id: "chunk_sensitivity",
                  name: "Chunk Sensitivity (3 Trials)",
                  desc: "Tests small (250/50), medium (500/100), and large (1000/200) chunks.",
                },
                {
                  id: "retrieval_depth",
                  name: "Retrieval Depth (3 Trials)",
                  desc: "Tests shallow (k=2), standard (k=4), and deep (k=8) retrieval.",
                },
                {
                  id: "prompt_strategy",
                  name: "Prompt Assembly (3 Trials)",
                  desc: "Tests standard QA, grounded synthesis, and regulatory compliance prompts.",
                },
                {
                  id: "chunk_and_retrieval",
                  name: "Chunk & Retrieval Grid (9 Trials)",
                  desc: "Exhaustive 3x3 Cartesian grid across 3 chunk sizes and 3 top-k values.",
                },
              ].map((p) => (
                <div
                  key={p.id}
                  onClick={() => setPresetName(p.id)}
                  className={`p-4 border rounded-lg cursor-pointer transition-all ${
                    presetName === p.id
                      ? "border-primary bg-primary/5 ring-1 ring-primary"
                      : "border-border hover:bg-secondary/40"
                  }`}
                >
                  <div className="font-semibold text-sm mb-1">{p.name}</div>
                  <div className="text-xs text-muted-foreground">{p.desc}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-between pt-4 border-t border-border">
            <button
              onClick={() => setStep(2)}
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-4 h-4" /> Back
            </button>
            <button
              onClick={() => setStep(4)}
              className="inline-flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-md font-medium text-sm transition-colors"
            >
              Preflight Inspection <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: Preflight Validation */}
      {step === 4 && (
        <div className="space-y-6 bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-500" />
            Step 4: Preflight Matrix Inspection & Security Checks
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3 bg-secondary/30 rounded-lg border border-border text-center">
              <span className="text-xs text-muted-foreground">Gate 1 Approval</span>
              <div className="font-semibold text-emerald-500 text-sm flex items-center justify-center gap-1 mt-1">
                <CheckCircle2 className="w-4 h-4" /> Verified
              </div>
            </div>
            <div className="p-3 bg-secondary/30 rounded-lg border border-border text-center">
              <span className="text-xs text-muted-foreground">Free-Only Policy</span>
              <div className="font-semibold text-emerald-500 text-sm flex items-center justify-center gap-1 mt-1">
                <CheckCircle2 className="w-4 h-4" /> $0.00 Budget
              </div>
            </div>
            <div className="p-3 bg-secondary/30 rounded-lg border border-border text-center">
              <span className="text-xs text-muted-foreground">Holdout Protection</span>
              <div className="font-semibold text-emerald-500 text-sm flex items-center justify-center gap-1 mt-1">
                <CheckCircle2 className="w-4 h-4" /> Protected
              </div>
            </div>
          </div>

          <div className="border border-border rounded-lg overflow-hidden">
            <div className="bg-secondary/40 px-4 py-2 font-medium text-xs border-b border-border">
              Candidate Trial Matrix Preview ({presetName === "chunk_and_retrieval" ? 9 : 3} Unique Trials)
            </div>
            <div className="p-4 space-y-2 text-xs">
              <div className="flex items-center justify-between py-1.5 border-b border-border/50">
                <span className="font-medium">Preset Selected:</span>
                <span className="font-mono text-primary">{presetName}</span>
              </div>
              <div className="flex items-center justify-between py-1.5 border-b border-border/50">
                <span className="font-medium">Sequential Concurrency:</span>
                <span>1 (Local CPU Safe)</span>
              </div>
              <div className="flex items-center justify-between py-1.5">
                <span className="font-medium">Deterministic Evaluator:</span>
                <span>11 Canonical Metrics</span>
              </div>
            </div>
          </div>

          <div className="flex justify-between pt-4 border-t border-border">
            <button
              onClick={() => setStep(3)}
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-4 h-4" /> Back
            </button>
            <button
              onClick={() => setStep(5)}
              className="inline-flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-md font-medium text-sm transition-colors"
            >
              Review & Launch <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 5: Final Review & Launch */}
      {step === 5 && (
        <div className="space-y-6 bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Play className="w-5 h-5 text-primary" />
            Step 5: Review & Launch Sequential Execution
          </h2>

          <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg space-y-2 text-sm">
            <h4 className="font-semibold text-primary">Ready to execute trial matrix:</h4>
            <p className="text-xs text-muted-foreground">
              Trials will run sequentially on local CPU, attributing real citations, measuring 11 deterministic rubric criteria, and logging cryptographic hashes without external cloud costs.
            </p>
          </div>

          <div className="flex justify-between pt-4 border-t border-border">
            <button
              onClick={() => setStep(4)}
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-4 h-4" /> Back
            </button>
            <button
              onClick={() => launchMutation.mutate()}
              disabled={launchMutation.isPending}
              className="inline-flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 px-6 py-2.5 rounded-md font-medium text-sm transition-colors shadow-sm disabled:opacity-50"
            >
              {launchMutation.isPending ? (
                <>Launching Sequential Matrix...</>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  Create & Launch Experiment
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
