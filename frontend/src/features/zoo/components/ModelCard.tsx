import { Link } from "react-router-dom";
import { ArrowUpRight, Download, Eye, Globe, Lock, ShieldCheck } from "lucide-react";
import type { ModelListingSummary } from "../types";

interface ModelCardProps {
  listing: ModelListingSummary;
  manageMode?: boolean;
}

export function ModelCard({ listing, manageMode = false }: ModelCardProps) {
  const isPublic = listing.visibility === "PUBLIC";
  const isOrg = listing.visibility === "ORGANIZATION";
  const isWorkspace = listing.visibility === "WORKSPACE";

  const isDownloadable = listing.distribution_status === "DOWNLOADABLE";

  return (
    <div className="flex flex-col justify-between rounded-lg border bg-card text-card-foreground shadow-sm hover:shadow-md transition-all p-5">
      <div>
        {/* Header / Visibility / Status */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex flex-wrap items-center gap-1.5">
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium border ${
                isPublic
                  ? "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-800"
                  : isOrg
                  ? "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800"
                  : isWorkspace
                  ? "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700"
                  : "bg-zinc-100 text-zinc-600 border-zinc-200"
              }`}
            >
              {isPublic ? <Globe className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
              {listing.visibility}
            </span>

            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium border ${
                isDownloadable
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300"
                  : "bg-zinc-100 text-zinc-600 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400"
              }`}
            >
              {isDownloadable ? <Download className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
              {listing.distribution_status === "DOWNLOADABLE" ? "Downloadable" : "Metadata Only"}
            </span>

            {manageMode && (
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-primary/10 text-primary border border-primary/20">
                {listing.publication_status}
              </span>
            )}
          </div>

          {listing.version_tag && (
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-muted font-medium text-foreground">
              {listing.version_tag}
            </span>
          )}
        </div>

        {/* Title & Description */}
        <h3 className="text-base font-semibold tracking-tight text-foreground line-clamp-1 mb-1">
          {listing.title}
        </h3>
        <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
          {listing.description}
        </p>

        {/* Technical Specs */}
        <div className="grid grid-cols-2 gap-2 text-xs py-2 border-y mb-3 bg-muted/20 -mx-5 px-5">
          <div>
            <span className="text-muted-foreground block text-[10px] uppercase font-bold tracking-wider">
              Category
            </span>
            <span className="font-medium text-foreground truncate block">
              {listing.category.replace(/_/g, " ")}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground block text-[10px] uppercase font-bold tracking-wider">
              Evaluation
            </span>
            <span className="font-medium text-foreground">
              {listing.final_evaluation_score != null
                ? `${(listing.final_evaluation_score * 100).toFixed(1)}% score`
                : "Evaluated"}
            </span>
          </div>
        </div>

        {/* Tags */}
        {listing.tags && listing.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-4">
            {listing.tags.slice(0, 3).map((t) => (
              <span key={t} className="px-1.5 py-0.5 rounded text-[10px] bg-muted text-muted-foreground">
                #{t}
              </span>
            ))}
            {listing.tags.length > 3 && (
              <span className="text-[10px] text-muted-foreground self-center">
                +{listing.tags.length - 3} more
              </span>
            )}
          </div>
        )}
      </div>

      {/* Footer Link */}
      <div className="pt-2 flex items-center justify-between border-t mt-auto">
        <div className="flex items-center gap-1 text-[11px] text-muted-foreground font-mono">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>Gate 3 Approved</span>
        </div>

        <Link
          to={`/zoo/models/${listing.id}`}
          className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
        >
          View Release <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
