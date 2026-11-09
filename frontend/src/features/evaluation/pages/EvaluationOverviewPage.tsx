import { useState, useEffect, type FormEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  Award,
  BookOpen,
  ChevronRight,
  FileCheck,
  Layers,
  Play,
  Plus,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import {
  fetchSuites,
  createSuite,
  fetchRuns,
  createAndExecuteRun,
} from "../api";
import type {
  CreateRunPayload,
  CreateSuitePayload,
  EvaluationRun,
  EvaluationSuite,
} from "../types";

export function EvaluationOverviewPage() {
  const { activeWorkspace } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const workspaceId = activeWorkspace?.id;

  const [activeTab, setActiveTab] = useState<"suites" | "runs">("suites");
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateSuiteModal, setShowCreateSuiteModal] = useState(false);
  const [showCreateRunModal, setShowCreateRunModal] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // New Suite Form State
  const [suiteName, setSuiteName] = useState("");
  const [suiteSlug, setSuiteSlug] = useState("");
  const [suiteDesc, setSuiteDesc] = useState("");
  const [suiteDomain, setSuiteDomain] = useState("Banking & Regulatory Compliance");
  const [suiteLang, setSuiteLang] = useState("en");

  // New Run Form State
  const [runSuiteId, setRunSuiteId] = useState("");
  const [runTargetType, setRunTargetType] = useState("MOCK_LLM");
  const [runTargetName, setRunTargetName] = useState("Mizan Free Local Baseline");
  const [runProvider, setRunProvider] = useState("mock");
  const [runModel, setRunModel] = useState("mock-generator-v1");

  useEffect(() => {
    if (suiteName) {
      const gen = suiteName
        .toLowerCase()
        .replace(/[^\w\s-]/g, "")
        .replace(/[\s_-]+/g, "-")
        .replace(/^-+|-+$/g, "");
      setSuiteSlug(gen);
    }
  }, [suiteName]);

  // Queries
  const {
    data: suites = [],
    isLoading: suitesLoading,
  } = useQuery<EvaluationSuite[]>({
    queryKey: ["evaluation-suites", workspaceId],
    queryFn: () => fetchSuites(workspaceId!),
    enabled: !!workspaceId,
  });

  const {
    data: runs = [],
    isLoading: runsLoading,
  } = useQuery<EvaluationRun[]>({
    queryKey: ["evaluation-runs", workspaceId],
    queryFn: () => fetchRuns(workspaceId!),
    enabled: !!workspaceId,
  });

  // Create Suite Mutation
  const createSuiteMutation = useMutation({
    mutationFn: (payload: CreateSuitePayload) => createSuite(workspaceId!, payload),
    onSuccess: (newSuite) => {
      queryClient.invalidateQueries({ queryKey: ["evaluation-suites", workspaceId] });
      setShowCreateSuiteModal(false);
      setSuiteName("");
      setSuiteSlug("");
      setSuiteDesc("");
      navigate(`/evaluation/suites/${newSuite.id}`);
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || "Failed to create evaluation suite.");
    },
  });

  // Create & Execute Run Mutation
  const createRunMutation = useMutation({
    mutationFn: (payload: CreateRunPayload) => createAndExecuteRun(workspaceId!, payload),
    onSuccess: (newRun) => {
      queryClient.invalidateQueries({ queryKey: ["evaluation-runs", workspaceId] });
      setShowCreateRunModal(false);
      navigate(`/evaluation/runs/${newRun.id}`);
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || "Failed to execute evaluation run.");
    },
  });

  const handleCreateSuite = (e: FormEvent) => {
    e.preventDefault();
    if (!suiteName.trim()) return;
    createSuiteMutation.mutate({
      name: suiteName.trim(),
      slug: suiteSlug.trim() || undefined,
      description: suiteDesc.trim() || undefined,
      domain: suiteDomain.trim() || undefined,
      language: suiteLang,
    });
  };

  const handleCreateRun = (e: FormEvent) => {
    e.preventDefault();
    if (!runSuiteId) {
      setErrorMessage("Please select an evaluation suite.");
      return;
    }
    createRunMutation.mutate({
      suite_id: runSuiteId,
      target_type: runTargetType,
      target_name: runTargetName,
      provider_name: runProvider,
      model_name: runModel,
    });
  };

  const filteredSuites = suites.filter((s) =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (s.domain && s.domain.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const totalQuestions = suites.reduce((acc, s) => acc + (s.case_count || s.total_cases || 0), 0);
  const completedRuns = runs.filter((r) => r.status === "COMPLETED");
  const avgScore =
    completedRuns.length > 0
      ? (completedRuns.reduce((acc, r) => acc + (r.overall_score || 0), 0) / completedRuns.length).toFixed(1)
      : "—";

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6 sm:p-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="w-3.5 h-3.5" />
              Gate 1 Guarded
            </span>
            <span className="text-xs text-muted-foreground">Milestone 6 Engine</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight mt-1 text-foreground">
            Evaluation Centre
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Automated examination suites, 11-metric deterministic rubrics, groundedness benchmarks & audit-attested runs.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setShowCreateSuiteModal(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            New Evaluation Suite
          </button>
          <button
            onClick={() => {
              if (suites.length > 0 && !runSuiteId) {
                setRunSuiteId(suites[0].id);
              }
              setShowCreateRunModal(true);
            }}
            disabled={suites.length === 0}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium bg-secondary text-secondary-foreground hover:bg-secondary/80 disabled:opacity-50 transition-colors border border-border"
          >
            <Play className="w-4 h-4 text-emerald-500" />
            Run Benchmark
          </button>
        </div>
      </div>

      {/* Error alert */}
      {errorMessage && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-destructive hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Evaluation Suites
            </span>
            <BookOpen className="w-4 h-4 text-blue-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">{suites.length}</span>
            <span className="text-xs text-muted-foreground">in workspace</span>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Examination Cases
            </span>
            <FileCheck className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">{totalQuestions}</span>
            <span className="text-xs text-muted-foreground">grounded items</span>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Benchmark Runs
            </span>
            <Layers className="w-4 h-4 text-purple-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">{runs.length}</span>
            <span className="text-xs text-emerald-500 font-medium">
              {completedRuns.length} completed
            </span>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Mean Benchmark Score
            </span>
            <Award className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">{avgScore}</span>
            {avgScore !== "—" && <span className="text-xs text-muted-foreground">/ 100</span>}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-border flex items-center gap-6">
        <button
          onClick={() => setActiveTab("suites")}
          className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "suites"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Examination Suites ({suites.length})
        </button>
        <button
          onClick={() => setActiveTab("runs")}
          className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "runs"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Benchmark Runs ({runs.length})
        </button>
      </div>

      {/* Tab: Suites */}
      {activeTab === "suites" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search suites by name or domain..."
                className="w-full pl-9 pr-4 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </div>

          {suitesLoading ? (
            <div className="py-12 text-center text-sm text-muted-foreground">
              Loading evaluation suites...
            </div>
          ) : filteredSuites.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border p-12 text-center">
              <BookOpen className="w-10 h-10 mx-auto text-muted-foreground/60 mb-3" />
              <h3 className="text-base font-semibold text-foreground">No evaluation suites yet</h3>
              <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
                Create an evaluation suite to generate questions from your Gate 1 approved masked business datasets.
              </p>
              <button
                onClick={() => setShowCreateSuiteModal(true)}
                className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <Plus className="w-4 h-4" />
                Create First Suite
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredSuites.map((s) => {
                const count = s.case_count ?? s.total_cases ?? 0;
                return (
                  <div
                    key={s.id}
                    onClick={() => navigate(`/evaluation/suites/${s.id}`)}
                    className="group cursor-pointer rounded-xl border border-border bg-card p-5 hover:border-primary/50 hover:shadow-md transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium uppercase tracking-wider ${
                            s.status === "READY"
                              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                              : "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                          }`}
                        >
                          {s.status}
                        </span>
                        {s.active_version ? (
                          <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-secondary text-secondary-foreground border border-border">
                            v{s.active_version} Frozen
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">Draft</span>
                        )}
                      </div>

                      <h3 className="text-base font-semibold text-foreground mt-3 group-hover:text-primary transition-colors">
                        {s.name}
                      </h3>
                      {s.description && (
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {s.description}
                        </p>
                      )}

                      <div className="mt-4 flex flex-wrap gap-1.5">
                        {s.domain && (
                          <span className="px-2 py-0.5 rounded text-xs bg-muted text-muted-foreground">
                            {s.domain}
                          </span>
                        )}
                        <span className="px-2 py-0.5 rounded text-xs bg-muted text-muted-foreground uppercase font-mono">
                          {s.language}
                        </span>
                      </div>
                    </div>

                    <div className="mt-5 pt-4 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
                      <div className="flex items-center gap-1.5 font-medium text-foreground">
                        <FileCheck className="w-4 h-4 text-emerald-500" />
                        <span>{count} Cases</span>
                      </div>
                      <span className="inline-flex items-center gap-1 group-hover:translate-x-0.5 transition-transform text-primary font-medium">
                        Open Suite
                        <ChevronRight className="w-3.5 h-3.5" />
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab: Runs */}
      {activeTab === "runs" && (
        <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
          {runsLoading ? (
            <div className="py-12 text-center text-sm text-muted-foreground">
              Loading benchmark runs...
            </div>
          ) : runs.length === 0 ? (
            <div className="py-12 text-center">
              <Layers className="w-10 h-10 mx-auto text-muted-foreground/60 mb-3" />
              <h3 className="text-base font-semibold text-foreground">No benchmark runs yet</h3>
              <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
                Execute a benchmark run against your finalized evaluation suites to test model groundedness and accuracy.
              </p>
              <button
                onClick={() => {
                  if (suites.length > 0 && !runSuiteId) {
                    setRunSuiteId(suites[0].id);
                  }
                  setShowCreateRunModal(true);
                }}
                disabled={suites.length === 0}
                className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <Play className="w-4 h-4" />
                Launch First Benchmark
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-muted/50 border-b border-border text-xs uppercase font-medium text-muted-foreground">
                  <tr>
                    <th className="px-5 py-3.5">Target & Model</th>
                    <th className="px-5 py-3.5">Suite & Version</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5 text-center">Score</th>
                    <th className="px-5 py-3.5">Cases Evaluated</th>
                    <th className="px-5 py-3.5">Executed</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {runs.map((r) => {
                    const score = r.overall_score ?? 0;
                    const scoreColor =
                      score >= 80
                        ? "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                        : score >= 60
                        ? "text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/20"
                        : "text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/20";

                    return (
                      <tr
                        key={r.id}
                        className="hover:bg-muted/30 cursor-pointer transition-colors"
                        onClick={() => navigate(`/evaluation/runs/${r.id}`)}
                      >
                        <td className="px-5 py-4">
                          <div className="font-medium text-foreground">{r.target_name}</div>
                          <div className="text-xs text-muted-foreground font-mono mt-0.5">
                            {r.provider_name} • {r.model_name}
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <span className="font-mono text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                            v{r.rubric_version || 1}
                          </span>
                        </td>
                        <td className="px-5 py-4">
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-xs font-medium uppercase tracking-wider ${
                              r.status === "COMPLETED"
                                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                                : r.status === "RUNNING"
                                ? "bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 animate-pulse"
                                : "bg-destructive/10 text-destructive border border-destructive/20"
                            }`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-center">
                          <span
                            className={`inline-block font-bold text-sm px-2.5 py-1 rounded-lg border ${scoreColor}`}
                          >
                            {score.toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-5 py-4 text-xs text-muted-foreground">
                          <span className="font-medium text-foreground">
                            {r.completed_cases}
                          </span>{" "}
                          / {r.total_cases}
                        </td>
                        <td className="px-5 py-4 text-xs text-muted-foreground">
                          {r.created_at ? new Date(r.created_at).toLocaleDateString() : "—"}
                        </td>
                        <td className="px-5 py-4 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/evaluation/runs/${r.id}`);
                            }}
                            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                          >
                            Scorecard
                            <ChevronRight className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Modal: Create Suite */}
      {showCreateSuiteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h2 className="text-lg font-bold text-foreground">Create Evaluation Suite</h2>
              <button
                onClick={() => setShowCreateSuiteModal(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSuite} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                  Suite Name *
                </label>
                <input
                  type="text"
                  required
                  value={suiteName}
                  onChange={(e) => setSuiteName(e.target.value)}
                  placeholder="e.g. Retail Lending Policies 2026"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                  Slug
                </label>
                <input
                  type="text"
                  value={suiteSlug}
                  onChange={(e) => setSuiteSlug(e.target.value)}
                  placeholder="retail-lending-policies-2026"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm font-mono text-xs focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                  Description
                </label>
                <textarea
                  rows={2}
                  value={suiteDesc}
                  onChange={(e) => setSuiteDesc(e.target.value)}
                  placeholder="Describe the scope, objectives, or compliance standards examined..."
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                    Domain
                  </label>
                  <input
                    type="text"
                    value={suiteDomain}
                    onChange={(e) => setSuiteDomain(e.target.value)}
                    placeholder="Banking, Legal, HR"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                    Language
                  </label>
                  <select
                    value={suiteLang}
                    onChange={(e) => setSuiteLang(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="en">English (en)</option>
                    <option value="ar">Arabic (ar)</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowCreateSuiteModal(false)}
                  className="px-4 py-2 rounded-lg text-sm text-muted-foreground hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createSuiteMutation.isPending}
                  className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {createSuiteMutation.isPending ? "Creating..." : "Create Suite"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Create & Execute Benchmark Run */}
      {showCreateRunModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Play className="w-5 h-5 text-emerald-500" />
                <h2 className="text-lg font-bold text-foreground">Launch Benchmark Run</h2>
              </div>
              <button
                onClick={() => setShowCreateRunModal(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateRun} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                  Evaluation Suite *
                </label>
                <select
                  required
                  value={runSuiteId}
                  onChange={(e) => setRunSuiteId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value="" disabled>Select an evaluation suite</option>
                  {suites.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.status}, {s.case_count ?? s.total_cases ?? 0} cases)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                  Target Evaluation System Name
                </label>
                <input
                  type="text"
                  required
                  value={runTargetName}
                  onChange={(e) => setRunTargetName(e.target.value)}
                  placeholder="e.g. Mizan Free Local Baseline RAG"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                    Target Type
                  </label>
                  <select
                    value={runTargetType}
                    onChange={(e) => setRunTargetType(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="MOCK_LLM">Mock LLM Provider (Free / Deterministic)</option>
                    <option value="OLLAMA">Ollama Local Model (Local CPU)</option>
                    <option value="GEMINI_FREE">Gemini Free Tier (API)</option>
                    <option value="RAG_PIPELINE">Full Mizan RAG Pipeline</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                    Provider
                  </label>
                  <input
                    type="text"
                    value={runProvider}
                    onChange={(e) => setRunProvider(e.target.value)}
                    placeholder="mock, ollama, gemini_free"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                  Model Identifier
                </label>
                <input
                  type="text"
                  value={runModel}
                  onChange={(e) => setRunModel(e.target.value)}
                  placeholder="mock-generator-v1, llama3:8b, gemini-1.5-flash"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm font-mono text-xs focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
                <span className="font-semibold text-foreground">Zero-Cost Guarantee: </span>
                Evaluations run 100% locally on CPU with zero cloud bills. Scoring applies all 11 deterministic metric evaluators.
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowCreateRunModal(false)}
                  className="px-4 py-2 rounded-lg text-sm text-muted-foreground hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createRunMutation.isPending}
                  className="px-4 py-2 rounded-lg text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                  {createRunMutation.isPending ? "Executing Evaluation..." : "Start Benchmark"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
