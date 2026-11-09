import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  FlaskConical,
  Plus,
  Search,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  ChevronRight,
  BarChart2,
  RefreshCw,
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import { fetchExperiments } from "../api";
import type { Experiment, ExperimentStatus } from "../types";

function getStatusBadge(status: ExperimentStatus) {
  switch (status) {
    case "COMPLETED":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
          <CheckCircle2 className="w-3.5 h-3.5" /> Completed
        </span>
      );
    case "COMPLETED_WITH_ERRORS":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-500 border border-amber-500/20">
          <AlertTriangle className="w-3.5 h-3.5" /> Completed with Errors
        </span>
      );
    case "RUNNING":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-500 border border-blue-500/20 animate-pulse">
          <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Running
        </span>
      );
    case "READY":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-500 border border-indigo-500/20">
          <Layers className="w-3.5 h-3.5" /> Ready to Run
        </span>
      );
    case "CANCELLED":
    case "CANCEL_REQUESTED":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-500/10 text-neutral-400 border border-neutral-500/20">
          <Clock className="w-3.5 h-3.5" /> Cancelled
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-500/10 text-neutral-400 border border-neutral-500/20">
          <Clock className="w-3.5 h-3.5" /> {status}
        </span>
      );
  }
}

export function ExperimentListPage() {
  const { activeWorkspace } = useAuth();
  const navigate = useNavigate();
  const workspaceId = activeWorkspace?.id;

  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const { data: experiments = [], isLoading, refetch } = useQuery<Experiment[]>({
    queryKey: ["experiments", workspaceId, statusFilter],
    queryFn: () => fetchExperiments(workspaceId!, statusFilter === "ALL" ? undefined : statusFilter),
    enabled: Boolean(workspaceId),
    refetchInterval: 5000, // Auto-refresh for live experiment progress updates
  });

  const filteredExperiments = experiments.filter((e) => {
    const q = searchQuery.toLowerCase();
    return e.name.toLowerCase().includes(q) || e.slug.toLowerCase().includes(q);
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <FlaskConical className="w-6 h-6 text-primary" />
            Model Experimentation Lab
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Design controlled trial matrices (3-9 unique configurations), execute sequential local evaluations, and inspect factual metric observations.
          </p>
        </div>
        <button
          onClick={() => navigate("/experiments/new")}
          className="inline-flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-md font-medium text-sm transition-colors shadow-sm self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          New Experiment
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search experiments..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-sm bg-card border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
        <div className="flex items-center gap-1 self-start sm:self-auto overflow-x-auto">
          {["ALL", "RUNNING", "COMPLETED", "READY", "DRAFT"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                statusFilter === st
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary/40 text-muted-foreground hover:bg-secondary"
              }`}
            >
              {st}
            </button>
          ))}
          <button
            onClick={() => refetch()}
            title="Refresh list"
            className="p-1.5 text-muted-foreground hover:text-foreground rounded-md transition-colors ml-2"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Experiment List */}
      {isLoading ? (
        <div className="text-center py-16 text-muted-foreground text-sm flex items-center justify-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin" /> Loading experiments...
        </div>
      ) : filteredExperiments.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-border rounded-lg bg-card/50 p-8">
          <FlaskConical className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-60" />
          <h3 className="font-semibold text-base mb-1">No experiments found</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto mb-5">
            Compare retrieval depths, chunk sizes, and prompt strategies across approved business knowledge with deterministic reproducible metrics.
          </p>
          <button
            onClick={() => navigate("/experiments/new")}
            className="inline-flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-md font-medium text-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create First Experiment
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredExperiments.map((exp) => {
            const progressPct =
              exp.total_trials > 0
                ? Math.round(((exp.completed_trials + exp.failed_trials) / exp.total_trials) * 100)
                : 0;

            return (
              <div
                key={exp.id}
                className="bg-card border border-border rounded-lg p-5 hover:border-primary/50 transition-all shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span
                      onClick={() => navigate(`/experiments/${exp.id}`)}
                      className="font-semibold text-base hover:text-primary cursor-pointer transition-colors"
                    >
                      {exp.name}
                    </span>
                    {getStatusBadge(exp.status)}
                    <span className="text-xs text-muted-foreground font-mono">
                      {exp.slug}
                    </span>
                  </div>
                  {exp.description && (
                    <p className="text-sm text-muted-foreground line-clamp-1">
                      {exp.description}
                    </p>
                  )}
                  <div className="flex items-center gap-4 text-xs text-muted-foreground pt-1">
                    <span>
                      Split: <strong className="text-foreground">{exp.evaluation_split}</strong>
                    </span>
                    <span>•</span>
                    <span>
                      Trials: <strong className="text-foreground">{exp.total_trials}</strong>
                    </span>
                    <span>•</span>
                    <span>
                      Completed: <strong className="text-foreground">{exp.completed_trials}</strong>
                    </span>
                    {exp.failed_trials > 0 && (
                      <>
                        <span>•</span>
                        <span className="text-rose-500 font-medium">
                          Failed: {exp.failed_trials}
                        </span>
                      </>
                    )}
                  </div>

                  {/* Progress bar for running/completed */}
                  {exp.total_trials > 0 && (
                    <div className="w-full max-w-md bg-secondary/50 rounded-full h-1.5 mt-2 overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${
                          exp.status === "COMPLETED"
                            ? "bg-emerald-500"
                            : exp.status === "COMPLETED_WITH_ERRORS"
                            ? "bg-amber-500"
                            : "bg-primary"
                        }`}
                        style={{ width: `${progressPct}%` }}
                      />
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 self-end md:self-center">
                  {exp.status === "COMPLETED" || exp.status === "COMPLETED_WITH_ERRORS" ? (
                    <button
                      onClick={() => navigate(`/experiments/${exp.id}/comparison`)}
                      className="inline-flex items-center gap-1.5 text-xs font-medium bg-secondary hover:bg-secondary/80 text-foreground px-3 py-1.5 rounded-md border border-border transition-colors"
                    >
                      <BarChart2 className="w-3.5 h-3.5" />
                      Factual Comparison
                    </button>
                  ) : null}
                  <button
                    onClick={() => navigate(`/experiments/${exp.id}`)}
                    className="inline-flex items-center gap-1 text-xs font-medium bg-primary/10 hover:bg-primary/20 text-primary px-3 py-1.5 rounded-md transition-colors"
                  >
                    View Matrix
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
