import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Eye,
  PauseCircle,
  Plus,
  Send,
  Settings2,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import {
  fetchWorkspaceAppListings,
  fetchWorkspaceModelListings,
  submitAppListing,
  submitModelListing,
  suspendAppListing,
  suspendModelListing,
} from "../api";
import { ListingReviewModal } from "../components/ListingReviewModal";
import { NewAppModal } from "../components/NewAppModal";
import { NewModelListingModal } from "../components/NewModelListingModal";
import type { AppListingSummary, ModelListingSummary } from "../types";

export function CatalogManagePage() {
  const { workspaceId: paramWsId } = useParams<{ workspaceId: string }>();
  const { activeWorkspace } = useAuth();
  const workspaceId = paramWsId || activeWorkspace?.id;

  const [activeCatalog, setActiveCatalog] = useState<"MODELS" | "APPS">("MODELS");
  const [statusFilter, setStatusFilter] = useState<string>("");

  // Modals state
  const [isNewModelModalOpen, setIsNewModelModalOpen] = useState(false);
  const [isNewAppModalOpen, setIsNewAppModalOpen] = useState(false);

  const [reviewModalState, setReviewModalState] = useState<{
    isOpen: boolean;
    listingId: string;
    listingType: "MODEL" | "APP";
    listingTitle: string;
  }>({
    isOpen: false,
    listingId: "",
    listingType: "MODEL",
    listingTitle: "",
  });

  const [actionError, setActionError] = useState<string | null>(null);

  // Queries
  const modelsQuery = useQuery({
    queryKey: ["manage-models", workspaceId, statusFilter],
    queryFn: () => (workspaceId ? fetchWorkspaceModelListings(workspaceId, { status: statusFilter || undefined }) : []),
    enabled: Boolean(workspaceId && activeCatalog === "MODELS"),
  });

  const appsQuery = useQuery({
    queryKey: ["manage-apps", workspaceId, statusFilter],
    queryFn: () => (workspaceId ? fetchWorkspaceAppListings(workspaceId, { status: statusFilter || undefined }) : []),
    enabled: Boolean(workspaceId && activeCatalog === "APPS"),
  });

  if (!workspaceId) {
    return (
      <div className="p-8 text-center text-xs text-muted-foreground border rounded-lg">
        Please select a workspace to manage catalog listings.
      </div>
    );
  }

  const handleSubmitForReview = async (listingId: string, type: "MODEL" | "APP") => {
    try {
      setActionError(null);
      if (type === "MODEL") {
        await submitModelListing(workspaceId, listingId);
        modelsQuery.refetch();
      } else {
        await submitAppListing(workspaceId, listingId);
        appsQuery.refetch();
      }
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to submit listing for review");
    }
  };

  const handleSuspend = async (listingId: string, type: "MODEL" | "APP") => {
    const reason = window.prompt("Enter reason for suspension:");
    if (!reason) return;

    try {
      setActionError(null);
      if (type === "MODEL") {
        await suspendModelListing(workspaceId, listingId, { reason });
        modelsQuery.refetch();
      } else {
        await suspendAppListing(workspaceId, listingId, { reason });
        appsQuery.refetch();
      }
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to suspend listing");
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6 sm:p-8">
      {/* Top Banner */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Link
            to="/zoo/models"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Model Zoo
          </Link>
          <span className="text-muted-foreground">·</span>
          <Link
            to="/zoo/apps"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            App Zoo
          </Link>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-5">
          <div>
            <div className="flex items-center gap-2">
              <Settings2 className="w-6 h-6 text-primary" />
              <h1 className="text-2xl font-bold tracking-tight text-foreground">Catalog Publisher Hub</h1>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Manage draft, review, and publication status for workspace Model and App Zoo offerings.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {activeCatalog === "MODELS" ? (
              <button
                type="button"
                onClick={() => setIsNewModelModalOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>New Model Listing</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setIsNewAppModalOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Register App Package</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {actionError && (
        <div className="p-3 rounded-md bg-destructive/10 text-destructive text-xs flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      {/* Catalog Selector & Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-2">
        <div className="flex space-x-4 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setActiveCatalog("MODELS")}
            className={`pb-2 border-b-2 transition-colors ${
              activeCatalog === "MODELS"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Model Listings
          </button>
          <button
            type="button"
            onClick={() => setActiveCatalog("APPS")}
            className={`pb-2 border-b-2 transition-colors ${
              activeCatalog === "APPS"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            App Packages
          </button>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2.5 py-1 text-xs rounded-md border bg-background text-foreground"
          >
            <option value="">All Statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="SUBMITTED_FOR_REVIEW">Submitted for Review</option>
            <option value="PUBLISHED">Published</option>
            <option value="SUSPENDED">Suspended</option>
          </select>
        </div>
      </div>

      {/* Listings Table */}
      {activeCatalog === "MODELS" ? (
        <div className="border rounded-lg overflow-hidden bg-card">
          <table className="w-full text-xs text-left">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="p-3 font-semibold">Title & Version</th>
                <th className="p-3 font-semibold">Category</th>
                <th className="p-3 font-semibold">Visibility</th>
                <th className="p-3 font-semibold">Publication Status</th>
                <th className="p-3 font-semibold">Distribution</th>
                <th className="p-3 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {modelsQuery.isLoading ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-muted-foreground">
                    Loading model listings...
                  </td>
                </tr>
              ) : (modelsQuery.data || []).length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-muted-foreground">
                    No model listings in this workspace. Create one from an approved release.
                  </td>
                </tr>
              ) : (
                (modelsQuery.data || []).map((m: ModelListingSummary) => (
                  <tr key={m.id} className="hover:bg-muted/30">
                    <td className="p-3">
                      <div className="font-semibold text-foreground">{m.title}</div>
                      <div className="text-[11px] text-muted-foreground font-mono">
                        {m.version_tag || "v1.0.0"} · {m.slug}
                      </div>
                    </td>
                    <td className="p-3">{m.category.replace(/_/g, " ")}</td>
                    <td className="p-3">
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-muted font-medium">
                        {m.visibility}
                      </span>
                    </td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          m.publication_status === "PUBLISHED"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300"
                            : m.publication_status === "SUBMITTED_FOR_REVIEW"
                            ? "bg-blue-50 text-blue-700 border border-blue-300 dark:bg-blue-950/40 dark:text-blue-300"
                            : m.publication_status === "SUSPENDED"
                            ? "bg-rose-50 text-rose-700 border border-rose-300 dark:bg-rose-950/40 dark:text-rose-300"
                            : "bg-zinc-100 text-zinc-700 border border-zinc-300 dark:bg-zinc-800 dark:text-zinc-300"
                        }`}
                      >
                        {m.publication_status}
                      </span>
                    </td>
                    <td className="p-3 text-muted-foreground">{m.distribution_status}</td>
                    <td className="p-3 text-right space-x-1">
                      <Link
                        to={`/zoo/models/${m.id}`}
                        className="px-2 py-1 text-[11px] rounded border hover:bg-muted font-medium inline-flex items-center gap-1"
                      >
                        <Eye className="w-3 h-3" /> View
                      </Link>

                      {m.publication_status === "DRAFT" && (
                        <button
                          type="button"
                          onClick={() => handleSubmitForReview(m.id, "MODEL")}
                          className="px-2 py-1 text-[11px] rounded border bg-primary text-primary-foreground hover:bg-primary/90 font-medium inline-flex items-center gap-1"
                        >
                          <Send className="w-3 h-3" /> Submit
                        </button>
                      )}

                      {m.publication_status === "SUBMITTED_FOR_REVIEW" && (
                        <button
                          type="button"
                          onClick={() =>
                            setReviewModalState({
                              isOpen: true,
                              listingId: m.id,
                              listingType: "MODEL",
                              listingTitle: m.title,
                            })
                          }
                          className="px-2 py-1 text-[11px] rounded border bg-emerald-600 text-white hover:bg-emerald-700 font-medium inline-flex items-center gap-1"
                        >
                          <ShieldCheck className="w-3 h-3" /> Review
                        </button>
                      )}

                      {m.publication_status === "PUBLISHED" && (
                        <button
                          type="button"
                          onClick={() => handleSuspend(m.id, "MODEL")}
                          className="px-2 py-1 text-[11px] rounded border text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 font-medium inline-flex items-center gap-1"
                        >
                          <PauseCircle className="w-3 h-3" /> Suspend
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden bg-card">
          <table className="w-full text-xs text-left">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="p-3 font-semibold">Title & Version</th>
                <th className="p-3 font-semibold">Category</th>
                <th className="p-3 font-semibold">Visibility</th>
                <th className="p-3 font-semibold">Status</th>
                <th className="p-3 font-semibold">Bound Models</th>
                <th className="p-3 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {appsQuery.isLoading ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-muted-foreground">
                    Loading app listings...
                  </td>
                </tr>
              ) : (appsQuery.data || []).length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-muted-foreground">
                    No application packages in this workspace.
                  </td>
                </tr>
              ) : (
                (appsQuery.data || []).map((a: AppListingSummary) => (
                  <tr key={a.id} className="hover:bg-muted/30">
                    <td className="p-3">
                      <div className="font-semibold text-foreground">{a.title}</div>
                      <div className="text-[11px] text-muted-foreground font-mono">
                        {a.version_tag || "v1.0.0"} · {a.slug}
                      </div>
                    </td>
                    <td className="p-3">{a.category.replace(/_/g, " ")}</td>
                    <td className="p-3">
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-muted font-medium">
                        {a.visibility}
                      </span>
                    </td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          a.publication_status === "PUBLISHED"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300"
                            : a.publication_status === "SUBMITTED_FOR_REVIEW"
                            ? "bg-blue-50 text-blue-700 border border-blue-300 dark:bg-blue-950/40 dark:text-blue-300"
                            : a.publication_status === "SUSPENDED"
                            ? "bg-rose-50 text-rose-700 border border-rose-300 dark:bg-rose-950/40 dark:text-rose-300"
                            : "bg-zinc-100 text-zinc-700 border border-zinc-300 dark:bg-zinc-800 dark:text-zinc-300"
                        }`}
                      >
                        {a.publication_status}
                      </span>
                    </td>
                    <td className="p-3 font-mono">{a.dependency_count} models</td>
                    <td className="p-3 text-right space-x-1">
                      <Link
                        to={`/zoo/apps/${a.id}`}
                        className="px-2 py-1 text-[11px] rounded border hover:bg-muted font-medium inline-flex items-center gap-1"
                      >
                        <Eye className="w-3 h-3" /> View
                      </Link>

                      {a.publication_status === "DRAFT" && (
                        <button
                          type="button"
                          onClick={() => handleSubmitForReview(a.id, "APP")}
                          className="px-2 py-1 text-[11px] rounded border bg-primary text-primary-foreground hover:bg-primary/90 font-medium inline-flex items-center gap-1"
                        >
                          <Send className="w-3 h-3" /> Submit
                        </button>
                      )}

                      {a.publication_status === "SUBMITTED_FOR_REVIEW" && (
                        <button
                          type="button"
                          onClick={() =>
                            setReviewModalState({
                              isOpen: true,
                              listingId: a.id,
                              listingType: "APP",
                              listingTitle: a.title,
                            })
                          }
                          className="px-2 py-1 text-[11px] rounded border bg-emerald-600 text-white hover:bg-emerald-700 font-medium inline-flex items-center gap-1"
                        >
                          <ShieldCheck className="w-3 h-3" /> Review
                        </button>
                      )}

                      {a.publication_status === "PUBLISHED" && (
                        <button
                          type="button"
                          onClick={() => handleSuspend(a.id, "APP")}
                          className="px-2 py-1 text-[11px] rounded border text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 font-medium inline-flex items-center gap-1"
                        >
                          <PauseCircle className="w-3 h-3" /> Suspend
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modals */}
      <NewModelListingModal
        workspaceId={workspaceId}
        isOpen={isNewModelModalOpen}
        onClose={() => setIsNewModelModalOpen(false)}
        onSuccess={() => modelsQuery.refetch()}
      />

      <NewAppModal
        workspaceId={workspaceId}
        isOpen={isNewAppModalOpen}
        onClose={() => setIsNewAppModalOpen(false)}
        onSuccess={() => appsQuery.refetch()}
      />

      <ListingReviewModal
        workspaceId={workspaceId}
        listingId={reviewModalState.listingId}
        listingType={reviewModalState.listingType}
        listingTitle={reviewModalState.listingTitle}
        isOpen={reviewModalState.isOpen}
        onClose={() =>
          setReviewModalState({ isOpen: false, listingId: "", listingType: "MODEL", listingTitle: "" })
        }
        onSuccess={() => {
          if (reviewModalState.listingType === "MODEL") {
            modelsQuery.refetch();
          } else {
            appsQuery.refetch();
          }
        }}
      />
    </div>
  );
}
