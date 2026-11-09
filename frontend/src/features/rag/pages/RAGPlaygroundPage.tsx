import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  AlertCircle,
  Award,
  Bot,
  CheckCircle2,
  Cpu,
  Database,
  Layers,
  Play,
  RotateCcw,
  Search,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import {
  fetchProviders,
  indexDatasetVersion,
  queryRAG,
  evaluateRAG,
} from "../api";
import type {
  ProviderInfo,
  RAGEvalResponse,
  RAGIndexResponse,
  RAGQueryResponse,
} from "../types";

export function RAGPlaygroundPage() {
  const { activeWorkspace } = useAuth();
  const workspaceId = activeWorkspace?.id;

  // Selected state
  const [selectedProvider, setSelectedProvider] = useState<string>("mock");
  const [datasetVersionId, setDatasetVersionId] = useState<string>("");
  const [queryText, setQueryText] = useState<string>(
    "What are the requirements for corporate budget approvals exceeding 50,000 AED?"
  );
  const [topK, setTopK] = useState<number>(4);
  const [scoreThreshold, setScoreThreshold] = useState<number>(0.2);

  // Result state
  const [lastIndexResult, setLastIndexResult] = useState<RAGIndexResponse | null>(null);
  const [queryResult, setQueryResult] = useState<RAGQueryResponse | null>(null);
  const [evalResult, setEvalResult] = useState<RAGEvalResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch Providers
  const {
    data: providers = [],
    isLoading: providersLoading,
    refetch: refetchProviders,
  } = useQuery<ProviderInfo[]>({
    queryKey: ["rag-providers", workspaceId],
    queryFn: () => fetchProviders(workspaceId!),
    enabled: !!workspaceId,
  });

  // Index Mutation
  const indexMutation = useMutation({
    mutationFn: (versionId: string) =>
      indexDatasetVersion(workspaceId!, versionId, 500, 100),
    onSuccess: (data) => {
      setLastIndexResult(data);
      setErrorMessage(null);
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || "Failed to index dataset version.");
    },
  });

  // Query Mutation
  const queryMutation = useMutation({
    mutationFn: () =>
      queryRAG(workspaceId!, {
        query: queryText,
        dataset_version_id: datasetVersionId.trim() || undefined,
        provider: selectedProvider,
        top_k: topK,
        score_threshold: scoreThreshold,
      }),
    onSuccess: (data) => {
      setQueryResult(data);
      setEvalResult(null);
      setErrorMessage(null);
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || "Query failed. Please verify provider and index.");
    },
  });

  // Evaluation Mutation
  const evalMutation = useMutation({
    mutationFn: () => {
      if (!queryResult) throw new Error("No query result to evaluate.");
      return evaluateRAG(workspaceId!, {
        query: queryResult.query,
        answer: queryResult.answer,
        retrieved_chunks: queryResult.retrieved_chunks,
        expected_keywords: ["approval", "budget", "executive", "compliance"],
      });
    },
    onSuccess: (data) => {
      setEvalResult(data);
      setErrorMessage(null);
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || "Evaluation failed.");
    },
  });

  if (!workspaceId) {
    return (
      <div className="max-w-7xl mx-auto p-12 my-6 bg-slate-900 text-slate-200 rounded-2xl border border-slate-800 shadow-xl text-center space-y-3">
        <AlertCircle className="w-10 h-10 mx-auto text-amber-400" />
        <h2 className="text-lg font-semibold text-slate-100">No Workspace Selected</h2>
        <p className="text-xs text-slate-400">Please select an active workspace to access the RAG Playground.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6 sm:p-8 my-6 bg-slate-900 text-slate-100 rounded-2xl border border-slate-800 shadow-xl pb-12">
      {/* Free Infrastructure Policy Banner */}
      <div className="bg-gradient-to-r from-emerald-950/70 via-slate-900 to-indigo-950/70 border border-emerald-500/30 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                Free-Only Architecture Mandate
              </span>
              <span className="text-xs text-slate-400">Zero Cloud Billing ($0.00 Surcharge)</span>
            </div>
            <p className="text-sm text-slate-300 mt-0.5">
              Embedded persistent Qdrant + Local CPU FastEmbed (384-dim ONNX, Multilingual English/Arabic) + Sovereign LLM Execution.
            </p>
          </div>
        </div>
        <div className="text-right shrink-0">
          <span className="text-xs font-mono text-emerald-400 bg-slate-950 px-3 py-1.5 rounded-md border border-slate-800">
            ALLOW_PAID_PROVIDERS: false
          </span>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold tracking-wider uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              AI Data Plane
            </span>
            <span className="text-xs text-slate-400">Step 5 of 12 — Experimentation & RAG</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Bot className="w-7 h-7 text-indigo-400" />
            AI Provider & RAG Experimentation Console
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-3xl leading-relaxed">
            Query your Gate 1 approved sovereign business documents with grounded citations, semantic search, and deterministic quality metrics.
          </p>
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="bg-red-950/60 border border-red-500/40 rounded-lg p-4 flex items-start gap-3 text-red-200">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div className="text-sm">
            <span className="font-semibold">Guardrail Intervention: </span>
            {errorMessage}
          </div>
        </div>
      )}

      {/* Registered Free Providers Grid */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Cpu className="w-4 h-4 text-indigo-400" />
            Registered Free Providers ({providers.length})
          </h2>
          <button
            onClick={() => refetchProviders()}
            className="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Refresh Status
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {providersLoading ? (
            <div className="col-span-3 text-center py-6 text-sm text-slate-500 animate-pulse">
              Inspecting registered AI provider daemons...
            </div>
          ) : (
            providers.map((p) => {
              const isSelected = selectedProvider === p.provider_name;
              return (
                <div
                  key={p.provider_name}
                  onClick={() => setSelectedProvider(p.provider_name)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? "bg-slate-900 border-indigo-500 ring-1 ring-indigo-500/50 shadow-lg shadow-indigo-950/40"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white uppercase text-xs tracking-wider flex items-center gap-1.5">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          p.is_available ? "bg-emerald-400" : "bg-amber-400"
                        }`}
                      />
                      {p.provider_name}
                    </span>
                    <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      $0.00 / FREE
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-2 line-clamp-2">{p.status_message}</p>
                  <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                    <span>Rate limit: {p.provider_name === "gemini_free" ? "15 RPM Free" : "Unlimited"}</span>
                    <span className={isSelected ? "text-indigo-400 font-semibold" : "text-slate-500"}>
                      {isSelected ? "Selected" : "Click to select"}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Dataset Indexing Section */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-indigo-400" />
            <h3 className="font-semibold text-white">Index Gate 1 Approved Dataset Version</h3>
          </div>
          <span className="text-xs text-slate-400 flex items-center gap-1">
            <ShieldCheck className="w-4 h-4 text-emerald-400" /> Gate 1 Human Sign-off Enforced
          </span>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed">
          Vectorize masked business documents using local FastEmbed into the persistent Qdrant store.
          Unapproved versions are strictly blocked by the fail-closed Gate 1 security invariant.
        </p>

        <div className="flex flex-col sm:flex-row items-center gap-3">
          <input
            type="text"
            placeholder="Enter approved Dataset Version UUID (e.g. from approved masking run)..."
            value={datasetVersionId}
            onChange={(e) => setDatasetVersionId(e.target.value)}
            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 w-full"
          />
          <button
            onClick={() => {
              if (datasetVersionId.trim()) {
                indexMutation.mutate(datasetVersionId.trim());
              }
            }}
            disabled={!datasetVersionId.trim() || indexMutation.isPending}
            className="w-full sm:w-auto px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-2 shrink-0"
          >
            {indexMutation.isPending ? (
              <>
                <RotateCcw className="w-4 h-4 animate-spin" />
                Indexing Chunks...
              </>
            ) : (
              <>
                <Layers className="w-4 h-4" />
                Index for RAG
              </>
            )}
          </button>
        </div>

        {lastIndexResult && (
          <div className="bg-slate-950 border border-emerald-500/30 rounded-lg p-3 text-xs flex flex-wrap items-center justify-between gap-3 text-slate-300">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>
                Successfully indexed <strong>{lastIndexResult.chunks_indexed}</strong> chunks across{" "}
                <strong>{lastIndexResult.documents_indexed}</strong> document(s).
              </span>
            </div>
            <div className="flex items-center gap-3 text-slate-400 font-mono text-[11px]">
              <span>Collection: {lastIndexResult.collection_name}</span>
              <span>Model: {lastIndexResult.embedding_model}</span>
            </div>
          </div>
        )}
      </div>

      {/* Interactive Query Console */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Query Controls */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="font-semibold text-white flex items-center gap-2 text-sm">
              <Search className="w-4 h-4 text-indigo-400" />
              Query Prompt
            </h3>

            <textarea
              rows={4}
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              placeholder="Ask a question about the approved workshop documentation..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 resize-none"
            />

            {/* Quick Templates */}
            <div>
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                Quick Prompts
              </span>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() =>
                    setQueryText(
                      "What are the requirements for corporate budget approvals exceeding 50,000 AED?"
                    )
                  }
                  className="text-xs bg-slate-950 hover:bg-slate-800 text-slate-300 px-2.5 py-1.5 rounded border border-slate-800 transition-colors text-left"
                >
                  Budget Approval Rules
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setQueryText(
                      "What is the contact information and phone number for the financial controller?"
                    )
                  }
                  className="text-xs bg-slate-950 hover:bg-slate-800 text-slate-300 px-2.5 py-1.5 rounded border border-slate-800 transition-colors text-left"
                >
                  Controller Inquiries
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setQueryText(
                      "What KYC and AML compliance standards apply to customer accounts?"
                    )
                  }
                  className="text-xs bg-slate-950 hover:bg-slate-800 text-slate-300 px-2.5 py-1.5 rounded border border-slate-800 transition-colors text-left"
                >
                  KYC & Compliance
                </button>
              </div>
            </div>

            {/* Sliders */}
            <div className="space-y-3 pt-2 border-t border-slate-800">
              <div>
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Top-K Retrieved Chunks</span>
                  <span className="font-mono text-white">{topK}</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={8}
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="w-full accent-indigo-500"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Score Threshold (Cosine)</span>
                  <span className="font-mono text-white">{scoreThreshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min={0.0}
                  max={0.9}
                  step={0.05}
                  value={scoreThreshold}
                  onChange={(e) => setScoreThreshold(Number(e.target.value))}
                  className="w-full accent-indigo-500"
                />
              </div>
            </div>

            <button
              onClick={() => queryMutation.mutate()}
              disabled={!queryText.trim() || queryMutation.isPending}
              className="w-full py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition-all shadow-md shadow-indigo-950/50 flex items-center justify-center gap-2"
            >
              {queryMutation.isPending ? (
                <>
                  <RotateCcw className="w-4 h-4 animate-spin" />
                  Retrieving & Generating...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  Execute RAG Query
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Answer & Attribution Panel */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4 min-h-[420px] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-semibold text-white flex items-center gap-2 text-sm">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                Synthesized Answer & Citations
              </h3>

              {queryResult && (
                <div className="flex items-center gap-2 font-mono text-[11px]">
                  <span className="bg-slate-950 px-2 py-0.5 rounded text-slate-400 border border-slate-800">
                    {queryResult.metrics.latency_ms} ms
                  </span>
                  <span className="bg-slate-950 px-2 py-0.5 rounded text-slate-400 border border-slate-800">
                    {queryResult.metrics.total_tokens} tokens
                  </span>
                  <span className="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20 font-semibold">
                    $0.00 Free
                  </span>
                </div>
              )}
            </div>

            {queryResult ? (
              <div className="space-y-4 flex-1">
                {/* Answer Box */}
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                  {queryResult.answer}
                </div>

                {/* Citations List */}
                {queryResult.citations.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                      Grounded Source Attributions ({queryResult.citations.length})
                    </h4>
                    <div className="grid grid-cols-1 gap-2">
                      {queryResult.citations.map((c, idx) => (
                        <div
                          key={idx}
                          className="bg-slate-950 border border-slate-800/80 rounded p-2.5 text-xs text-slate-300"
                        >
                          <div className="flex items-center justify-between text-[11px] text-indigo-400 font-mono mb-1">
                            <span className="font-bold">{c.citation_marker}</span>
                            <span className="text-slate-500">Score: {c.score.toFixed(3)}</span>
                          </div>
                          <p className="text-slate-400 italic">"{c.snippet}..."</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Retrieved Chunks Accordion */}
                <div className="space-y-2 pt-2 border-t border-slate-800">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>Retrieved Chunks from Vector Store ({queryResult.retrieved_chunks.length})</span>
                  </div>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {queryResult.retrieved_chunks.map((chunk, idx) => (
                      <div
                        key={idx}
                        className="bg-slate-950/70 border border-slate-800 rounded p-2 text-xs font-mono text-slate-400"
                      >
                        <div className="flex items-center justify-between text-[10px] text-slate-500 mb-1">
                          <span>Chunk #{chunk.chunk_index} (Doc: {chunk.document_id.slice(0, 8)}...)</span>
                          <span className="text-emerald-400">Cosine: {chunk.score.toFixed(4)}</span>
                        </div>
                        <p className="text-slate-300 font-sans line-clamp-2">{chunk.text}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Evaluation Trigger */}
                <div className="pt-2">
                  <button
                    onClick={() => evalMutation.mutate()}
                    disabled={evalMutation.isPending}
                    className="w-full py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-indigo-300 rounded-lg text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 border border-indigo-500/20"
                  >
                    {evalMutation.isPending ? (
                      <>
                        <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                        Calculating Metrics...
                      </>
                    ) : (
                      <>
                        <Award className="w-3.5 h-3.5 text-indigo-400" />
                        Run Deterministic Quality Evaluation
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-500">
                <Bot className="w-12 h-12 mb-3 text-slate-700" />
                <p className="text-sm font-medium text-slate-400">RAG Console Ready</p>
                <p className="text-xs text-slate-600 mt-1 max-w-sm">
                  Index an approved dataset version and click "Execute RAG Query" to retrieve context chunks and generate a verifiable answer.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quantitative Evaluation Metrics Card */}
      {evalResult && (
        <div className="bg-slate-900 border border-indigo-500/30 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Award className="w-5 h-5 text-amber-400" />
              <h3 className="font-semibold text-white">RAG Quality Benchmark Scorecard</h3>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Overall Score:</span>
              <span className="text-lg font-bold font-mono text-emerald-400">
                {(evalResult.overall_score * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
                Retrieval Recall
              </span>
              <span className="text-xl font-bold font-mono text-white mt-1 block">
                {(evalResult.retrieval_recall * 100).toFixed(0)}%
              </span>
              <span className="text-[10px] text-slate-500 mt-0.5 block">Keywords in context</span>
            </div>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
                Context Relevance
              </span>
              <span className="text-xl font-bold font-mono text-white mt-1 block">
                {(evalResult.context_relevance * 100).toFixed(0)}%
              </span>
              <span className="text-[10px] text-slate-500 mt-0.5 block">Chunks matching query</span>
            </div>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
                Faithfulness
              </span>
              <span className="text-xl font-bold font-mono text-white mt-1 block">
                {(evalResult.faithfulness * 100).toFixed(0)}%
              </span>
              <span className="text-[10px] text-slate-500 mt-0.5 block">Answer grounding ratio</span>
            </div>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
                Citation Completeness
              </span>
              <span className="text-xl font-bold font-mono text-white mt-1 block">
                {(evalResult.citation_completeness * 100).toFixed(0)}%
              </span>
              <span className="text-[10px] text-slate-500 mt-0.5 block">Verifiable source markers</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
