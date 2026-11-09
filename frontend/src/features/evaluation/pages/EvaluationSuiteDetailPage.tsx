import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  Check,
  CheckCircle2,
  Edit3,
  HelpCircle,
  Lock,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import {
  fetchSuite,
  fetchCases,
  fetchSuiteVersions,
  generateExam,
  finalizeSuite,
  createManualCase,
  reviewCase,
} from "../api";
import type {
  CreateManualCasePayload,
  DifficultyLevel,
  EvaluationCase,
  GenerateExamPayload,
  QuestionCategory,
  ReviewCasePayload,
  SplitType,
} from "../types";

const ALL_CATEGORIES: QuestionCategory[] = [
  "FACTUAL",
  "CONCEPTUAL",
  "PROCEDURAL",
  "COMPARISON",
  "MULTI_HOP",
  "NUMERICAL",
  "DOCUMENT_SPECIFIC",
  "UNANSWERABLE",
];

export function EvaluationSuiteDetailPage() {
  const { suiteId } = useParams<{ suiteId: string }>();
  const { activeWorkspace } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const workspaceId = activeWorkspace?.id;

  // Filter states
  const [selectedSplit, setSelectedSplit] = useState<string>("ALL");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  // Modal states
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [showManualModal, setShowManualModal] = useState(false);
  const [showFinalizeModal, setShowFinalizeModal] = useState(false);
  const [reviewingCase, setReviewingCase] = useState<EvaluationCase | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Generate Exam State
  const [genDatasetVersionId, setGenDatasetVersionId] = useState("");
  const [genQuestionsPerCategory, setGenQuestionsPerCategory] = useState<number>(2);
  const [selectedGenCategories, setSelectedGenCategories] = useState<QuestionCategory[]>([
    "FACTUAL",
    "PROCEDURAL",
    "NUMERICAL",
    "UNANSWERABLE",
  ]);

  // Manual Case Form State
  const [manQuestion, setManQuestion] = useState("");
  const [manExpectedAnswer, setManExpectedAnswer] = useState("");
  const [manCategory, setManCategory] = useState<QuestionCategory>("FACTUAL");
  const [manDifficulty, setManDifficulty] = useState<DifficultyLevel>("MEDIUM");
  const [manSplit, setManSplit] = useState<SplitType>("DEVELOPMENT");
  const [manIsUnanswerable, setManIsUnanswerable] = useState(false);
  const [manNotes, setManNotes] = useState("");

  // Review Case Form State
  const [reviewDecision, setReviewDecision] = useState<"APPROVED" | "REJECTED" | "EDITED" | "FLAGGED">("APPROVED");
  const [reviewCorrectedAnswer, setReviewCorrectedAnswer] = useState("");
  const [reviewComments, setReviewComments] = useState("");

  // Queries
  const { data: suite, isLoading: suiteLoading } = useQuery({
    queryKey: ["evaluation-suite", workspaceId, suiteId],
    queryFn: () => fetchSuite(workspaceId!, suiteId!),
    enabled: !!workspaceId && !!suiteId,
  });

  const { data: cases = [], isLoading: casesLoading } = useQuery({
    queryKey: ["evaluation-cases", workspaceId, suiteId],
    queryFn: () => fetchCases(workspaceId!, suiteId!),
    enabled: !!workspaceId && !!suiteId,
  });

  const { data: versions = [] } = useQuery({
    queryKey: ["evaluation-versions", workspaceId, suiteId],
    queryFn: () => fetchSuiteVersions(workspaceId!, suiteId!),
    enabled: !!workspaceId && !!suiteId,
  });

  // Mutations
  const generateMutation = useMutation({
    mutationFn: (payload: GenerateExamPayload) => generateExam(workspaceId!, suiteId!, payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["evaluation-cases", workspaceId, suiteId] });
      queryClient.invalidateQueries({ queryKey: ["evaluation-suite", workspaceId, suiteId] });
      setShowGenerateModal(false);
      setSuccessMessage(`Successfully generated ${data.generated_count} examination cases.`);
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || "Failed to generate examination cases. Ensure dataset has Gate 1 approval.");
    },
  });

  const manualCaseMutation = useMutation({
    mutationFn: (payload: CreateManualCasePayload) => createManualCase(workspaceId!, suiteId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["evaluation-cases", workspaceId, suiteId] });
      queryClient.invalidateQueries({ queryKey: ["evaluation-suite", workspaceId, suiteId] });
      setShowManualModal(false);
      setManQuestion("");
      setManExpectedAnswer("");
      setManNotes("");
      setSuccessMessage("Manual examination case added and verified.");
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || "Failed to create manual case.");
    },
  });

  const finalizeMutation = useMutation({
    mutationFn: () => finalizeSuite(workspaceId!, suiteId!),
    onSuccess: (ver) => {
      queryClient.invalidateQueries({ queryKey: ["evaluation-suite", workspaceId, suiteId] });
      queryClient.invalidateQueries({ queryKey: ["evaluation-versions", workspaceId, suiteId] });
      setShowFinalizeModal(false);
      setSuccessMessage(`Suite frozen as immutable Version ${ver.version_number} with SHA-256 attestation.`);
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || "Failed to finalize suite.");
    },
  });

  const reviewMutation = useMutation({
    mutationFn: (payload: ReviewCasePayload) =>
      reviewCase(workspaceId!, reviewingCase!.id, payload, suiteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["evaluation-cases", workspaceId, suiteId] });
      setReviewingCase(null);
      setSuccessMessage("Case review decision submitted successfully.");
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || "Failed to review case.");
    },
  });

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!genDatasetVersionId.trim()) {
      setErrorMessage("Please enter an approved Dataset Version ID.");
      return;
    }
    generateMutation.mutate({
      dataset_version_id: genDatasetVersionId.trim(),
      language: suite?.language || "en",
      categories: selectedGenCategories,
      questions_per_category: genQuestionsPerCategory,
      target_splits: { development: 0.6, validation: 0.2, holdout: 0.2 },
    });
  };

  const handleManualCase = (e: React.FormEvent) => {
    e.preventDefault();
    if (!manQuestion.trim() || !manExpectedAnswer.trim()) return;
    manualCaseMutation.mutate({
      question: manQuestion.trim(),
      expected_answer: manExpectedAnswer.trim(),
      category: manCategory,
      difficulty: manDifficulty,
      split: manSplit,
      language: suite?.language || "en",
      is_unanswerable: manIsUnanswerable,
      reviewer_notes: manNotes.trim() || undefined,
    });
  };

  const handleReviewSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewingCase) return;
    reviewMutation.mutate({
      decision: reviewDecision,
      comments: reviewComments.trim() || undefined,
      updated_expected_answer:
        reviewDecision === "EDITED" || reviewCorrectedAnswer.trim()
          ? reviewCorrectedAnswer.trim()
          : undefined,
    });
  };

  const toggleGenCategory = (cat: QuestionCategory) => {
    if (selectedGenCategories.includes(cat)) {
      if (selectedGenCategories.length > 1) {
        setSelectedGenCategories(selectedGenCategories.filter((c) => c !== cat));
      }
    } else {
      setSelectedGenCategories([...selectedGenCategories, cat]);
    }
  };

  // Filter cases
  const filteredCases = cases.filter((c) => {
    if (selectedSplit !== "ALL" && c.split !== selectedSplit) return false;
    if (selectedCategory !== "ALL" && c.category !== selectedCategory) return false;
    if (selectedStatus !== "ALL" && c.ground_truth_status !== selectedStatus) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        c.question.toLowerCase().includes(q) ||
        c.expected_answer.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const latestVersion = versions.length > 0 ? versions[0] : null;

  if (suiteLoading) {
    return <div className="py-12 text-center text-sm text-muted-foreground">Loading evaluation suite...</div>;
  }

  if (!suite) {
    return (
      <div className="rounded-xl border border-destructive/50 bg-destructive/10 p-6 text-center text-destructive">
        Evaluation Suite not found.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Navigation & Header */}
      <div>
        <button
          onClick={() => navigate("/evaluation")}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Evaluation Overview
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
          <div>
            <div className="flex items-center gap-2">
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-medium uppercase tracking-wider ${
                  suite.status === "READY"
                    ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                    : "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                }`}
              >
                {suite.status}
              </span>
              <span className="text-xs font-mono text-muted-foreground">{suite.slug}</span>
              <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground uppercase font-mono">
                {suite.language}
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight mt-1 text-foreground">
              {suite.name}
            </h1>
            {suite.description && (
              <p className="text-sm text-muted-foreground mt-0.5">{suite.description}</p>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowGenerateModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
            >
              <Sparkles className="w-4 h-4" />
              Generate Exam
            </button>
            <button
              onClick={() => setShowManualModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-secondary text-secondary-foreground hover:bg-secondary/80 border border-border"
            >
              <Plus className="w-4 h-4" />
              Add Question
            </button>
            <button
              onClick={() => setShowFinalizeModal(true)}
              disabled={cases.length === 0}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              <Lock className="w-4 h-4" />
              Freeze Version
            </button>
          </div>
        </div>
      </div>

      {/* Notifications */}
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

      {successMessage && (
        <div className="rounded-lg border border-emerald-500/50 bg-emerald-500/10 p-4 text-sm text-emerald-600 dark:text-emerald-400 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage(null)} className="hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Version Attestation Banner */}
      {latestVersion && (
        <div className="rounded-xl border border-border bg-muted/40 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0 border border-emerald-500/20">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-foreground">
                  Version {latestVersion.version_number} Attested
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-medium">
                  Immutable
                </span>
              </div>
              <div className="text-xs font-mono text-muted-foreground mt-0.5 truncate max-w-md sm:max-w-xl">
                SHA-256 Digest: {latestVersion.canonical_digest_sha256}
              </div>
            </div>
          </div>
          <div className="text-xs text-muted-foreground sm:text-right shrink-0">
            <div>{latestVersion.case_count} cases locked</div>
            <div>{new Date(latestVersion.created_at).toLocaleDateString()}</div>
          </div>
        </div>
      )}

      {/* Filters & Case Count */}
      <div className="rounded-xl border border-border bg-card p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mr-1">
              Split:
            </span>
            {["ALL", "DEVELOPMENT", "VALIDATION", "HOLDOUT"].map((sp) => (
              <button
                key={sp}
                onClick={() => setSelectedSplit(sp)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  selectedSplit === sp
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:text-foreground"
                }`}
              >
                {sp}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-2.5 py-1.5 rounded-md border border-border bg-background text-xs text-foreground focus:outline-none"
            >
              <option value="ALL">All Categories ({ALL_CATEGORIES.length})</option>
              {ALL_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="px-2.5 py-1.5 rounded-md border border-border bg-background text-xs text-foreground focus:outline-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="NEEDS_REVIEW">Needs Review</option>
              <option value="HUMAN_VERIFIED">Human Verified</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search questions or expected answers..."
            className="w-full pl-9 pr-4 py-1.5 rounded-lg border border-border bg-background text-xs focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
      </div>

      {/* Case List */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
          <span>Showing {filteredCases.length} of {cases.length} questions</span>
          <span>Deterministic CPU Scoring Ready</span>
        </div>

        {casesLoading ? (
          <div className="py-12 text-center text-sm text-muted-foreground">Loading examination cases...</div>
        ) : filteredCases.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border p-12 text-center">
            <HelpCircle className="w-10 h-10 mx-auto text-muted-foreground/60 mb-3" />
            <h3 className="text-base font-semibold text-foreground">No questions found</h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
              Generate examination cases from your approved masked dataset or add manual benchmark questions.
            </p>
          </div>
        ) : (
          filteredCases.map((c, idx) => {
            const statusColor =
              c.ground_truth_status === "HUMAN_VERIFIED"
                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                : c.ground_truth_status === "REJECTED"
                ? "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20"
                : "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20";

            return (
              <div
                key={c.id}
                className="rounded-xl border border-border bg-card p-4 hover:border-primary/40 transition-colors shadow-sm space-y-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-muted-foreground font-semibold">
                      #{idx + 1}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${statusColor}`}>
                      {c.ground_truth_status.replace("_", " ")}
                    </span>
                    <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-secondary text-secondary-foreground">
                      {c.category}
                    </span>
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-muted text-muted-foreground">
                      {c.difficulty}
                    </span>
                    <span className="px-2 py-0.5 rounded text-xs font-mono font-semibold bg-muted text-primary">
                      {c.split}
                    </span>
                    {c.is_unanswerable && (
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                        Negative (Abstention Test)
                      </span>
                    )}
                  </div>

                  <button
                    onClick={() => {
                      setReviewingCase(c);
                      setReviewDecision("APPROVED");
                      setReviewCorrectedAnswer(c.expected_answer);
                      setReviewComments("");
                    }}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-secondary hover:bg-secondary/80 text-foreground border border-border transition-colors"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    Review
                  </button>
                </div>

                <div>
                  <h4 className="text-sm font-semibold text-foreground">{c.question}</h4>
                </div>

                <div className="rounded-lg bg-muted/40 p-3 text-xs space-y-1">
                  <span className="font-semibold text-muted-foreground uppercase tracking-wider block">
                    Expected Reference Answer:
                  </span>
                  <p className="text-foreground leading-relaxed">{c.expected_answer}</p>
                </div>

                {c.reviewer_notes && (
                  <div className="text-xs text-muted-foreground italic">
                    Note: {c.reviewer_notes}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Modal: Generate Examination Cases */}
      {showGenerateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-primary" />
                <h2 className="text-lg font-bold text-foreground">Generate Examination Cases</h2>
              </div>
              <button onClick={() => setShowGenerateModal(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleGenerate} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                  Gate 1 Approved Dataset Version ID *
                </label>
                <input
                  type="text"
                  required
                  value={genDatasetVersionId}
                  onChange={(e) => setGenDatasetVersionId(e.target.value)}
                  placeholder="e.g. ver-7c89..."
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm font-mono text-xs focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
                <span className="text-xs text-muted-foreground mt-1 block">
                  INVARIANT: Must be approved through Gate 1. Unapproved datasets will fail closed with 403 Forbidden.
                </span>
              </div>

              <div>
                <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1.5">
                  Question Categories
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {ALL_CATEGORIES.map((cat) => {
                    const isSelected = selectedGenCategories.includes(cat);
                    return (
                      <button
                        type="button"
                        key={cat}
                        onClick={() => toggleGenCategory(cat)}
                        className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg border text-xs text-left transition-colors ${
                          isSelected
                            ? "bg-primary/10 border-primary text-primary font-medium"
                            : "bg-background border-border text-muted-foreground hover:border-muted-foreground"
                        }`}
                      >
                        <div
                          className={`w-3.5 h-3.5 rounded flex items-center justify-center border ${
                            isSelected ? "bg-primary border-primary text-primary-foreground" : "border-muted-foreground"
                          }`}
                        >
                          {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                        </div>
                        <span className="truncate">{cat}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                  Questions per Category: {genQuestionsPerCategory}
                </label>
                <input
                  type="range"
                  min={1}
                  max={8}
                  value={genQuestionsPerCategory}
                  onChange={(e) => setGenQuestionsPerCategory(parseInt(e.target.value, 10))}
                  className="w-full"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowGenerateModal(false)}
                  className="px-4 py-2 rounded-lg text-sm text-muted-foreground hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={generateMutation.isPending}
                  className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {generateMutation.isPending ? "Generating..." : "Generate Examination"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add Manual Question */}
      {showManualModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h2 className="text-lg font-bold text-foreground">Add Manual Question</h2>
              <button onClick={() => setShowManualModal(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleManualCase} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                  Question Text *
                </label>
                <textarea
                  rows={2}
                  required
                  value={manQuestion}
                  onChange={(e) => setManQuestion(e.target.value)}
                  placeholder="Enter clear, domain-specific prompt..."
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                  Expected Reference Answer *
                </label>
                <textarea
                  rows={3}
                  required
                  value={manExpectedAnswer}
                  onChange={(e) => setManExpectedAnswer(e.target.value)}
                  placeholder="Enter authoritative, human-verified ground truth answer..."
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                    Category
                  </label>
                  <select
                    value={manCategory}
                    onChange={(e) => setManCategory(e.target.value as QuestionCategory)}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-border bg-background text-xs focus:outline-none"
                  >
                    {ALL_CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                    Difficulty
                  </label>
                  <select
                    value={manDifficulty}
                    onChange={(e) => setManDifficulty(e.target.value as DifficultyLevel)}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-border bg-background text-xs focus:outline-none"
                  >
                    <option value="EASY">Easy</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HARD">Hard</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                    Split
                  </label>
                  <select
                    value={manSplit}
                    onChange={(e) => setManSplit(e.target.value as SplitType)}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-border bg-background text-xs focus:outline-none"
                  >
                    <option value="DEVELOPMENT">Development</option>
                    <option value="VALIDATION">Validation</option>
                    <option value="HOLDOUT">Holdout</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="unanswerableCheck"
                  checked={manIsUnanswerable}
                  onChange={(e) => setManIsUnanswerable(e.target.checked)}
                  className="rounded border-border text-primary focus:ring-primary/20"
                />
                <label htmlFor="unanswerableCheck" className="text-xs text-foreground cursor-pointer">
                  This is a negative question (verifies appropriate model abstention)
                </label>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowManualModal(false)}
                  className="px-4 py-2 rounded-lg text-sm text-muted-foreground hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={manualCaseMutation.isPending}
                  className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {manualCaseMutation.isPending ? "Adding..." : "Add Question"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Review Case Decision */}
      {reviewingCase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h2 className="text-lg font-bold text-foreground">Review Examination Case</h2>
              <button onClick={() => setReviewingCase(null)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleReviewSubmit} className="space-y-4">
              <div className="rounded-lg bg-muted/40 p-3 text-xs space-y-1">
                <span className="font-semibold text-muted-foreground uppercase tracking-wider block">Question:</span>
                <p className="text-foreground">{reviewingCase.question}</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1.5">
                  Review Action
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { id: "APPROVED", label: "Approve", color: "hover:border-emerald-500" },
                    { id: "EDITED", label: "Edit & Approve", color: "hover:border-blue-500" },
                    { id: "FLAGGED", label: "Flag", color: "hover:border-amber-500" },
                    { id: "REJECTED", label: "Reject", color: "hover:border-rose-500" },
                  ].map((act) => (
                    <button
                      type="button"
                      key={act.id}
                      onClick={() => setReviewDecision(act.id as "APPROVED" | "REJECTED" | "EDITED" | "FLAGGED")}
                      className={`px-3 py-2 rounded-lg border text-xs font-medium transition-colors ${
                        reviewDecision === act.id
                          ? "bg-primary text-primary-foreground border-primary"
                          : `bg-background border-border text-muted-foreground ${act.color}`
                      }`}
                    >
                      {act.label}
                    </button>
                  ))}
                </div>
              </div>

              {(reviewDecision === "EDITED" || reviewDecision === "APPROVED") && (
                <div>
                  <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                    Expected Answer (Ground Truth)
                  </label>
                  <textarea
                    rows={3}
                    value={reviewCorrectedAnswer}
                    onChange={(e) => setReviewCorrectedAnswer(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-foreground uppercase tracking-wider mb-1">
                  Reviewer Notes / Evidence Rationale
                </label>
                <input
                  type="text"
                  value={reviewComments}
                  onChange={(e) => setReviewComments(e.target.value)}
                  placeholder="e.g. Verified against CBUAE circular 12/2024"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setReviewingCase(null)}
                  className="px-4 py-2 rounded-lg text-sm text-muted-foreground hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={reviewMutation.isPending}
                  className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {reviewMutation.isPending ? "Submitting..." : "Submit Review"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Finalize Suite */}
      {showFinalizeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                <Lock className="w-5 h-5" />
                <h2 className="text-lg font-bold text-foreground">Freeze Evaluation Suite</h2>
              </div>
              <button onClick={() => setShowFinalizeModal(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-sm text-muted-foreground">
              Finalizing will lock all current {cases.length} examination cases into an immutable version snapshot with a canonical SHA-256 digest. No further questions can be added or edited on this version.
            </p>

            <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
              <span className="font-semibold text-foreground">Audit Guarantee: </span>
              All subsequent benchmark runs against this version are 100% reproducible and cryptographically attested.
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
              <button
                type="button"
                onClick={() => setShowFinalizeModal(false)}
                className="px-4 py-2 rounded-lg text-sm text-muted-foreground hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => finalizeMutation.mutate()}
                disabled={finalizeMutation.isPending}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {finalizeMutation.isPending ? "Freezing..." : "Confirm & Freeze Version"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
