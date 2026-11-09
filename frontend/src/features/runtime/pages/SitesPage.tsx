import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import {
  Server,
  Plus,
  Key,
  ShieldAlert,
  Radio,
  CheckCircle2,
  Clock,
  ExternalLink,
  AlertCircle,
} from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { listCustomerSites, createCustomerSite, revokeCustomerSite } from "../api";
import type { CustomerSite } from "../types";
import { SiteEnrollmentModal } from "../components/SiteEnrollmentModal";

export const SitesPage: React.FC = () => {
  const { activeWorkspace } = useAuth();
  const params = useParams<{ workspaceId?: string }>();
  const workspaceId = params.workspaceId || activeWorkspace?.id || "";
  const queryClient = useQueryClient();

  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [siteKey, setSiteKey] = useState("");
  const [siteName, setSiteName] = useState("");
  const [description, setDescription] = useState("");
  const [enrollingSite, setEnrollingSite] = useState<CustomerSite | null>(null);

  const { data: sites = [], isLoading, error } = useQuery({
    queryKey: ["customer-sites", workspaceId],
    queryFn: () => listCustomerSites(workspaceId),
    enabled: !!workspaceId,
  });

  const createMutation = useMutation({
    mutationFn: (payload: { site_key: string; site_name: string; description?: string }) =>
      createCustomerSite(workspaceId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customer-sites", workspaceId] });
      setIsRegisterOpen(false);
      setSiteKey("");
      setSiteName("");
      setDescription("");
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (siteId: string) => revokeCustomerSite(workspaceId, siteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customer-sites", workspaceId] });
    },
  });

  const handleRegisterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!siteKey.trim() || !siteName.trim()) return;
    createMutation.mutate({
      site_key: siteKey.trim(),
      site_name: siteName.trim(),
      description: description.trim() || undefined,
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ACTIVE":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
            <Radio className="w-3 h-3 text-emerald-500 animate-pulse" /> Active
          </span>
        );
      case "ENROLLING":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300">
            <Clock className="w-3 h-3" /> Enrolling
          </span>
        );
      case "REVOKED":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300">
            <ShieldAlert className="w-3 h-3" /> Revoked
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-muted text-muted-foreground">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Server className="w-7 h-7 text-primary" />
            Customer Deployment Sites
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Register and manage customer-premises runtime environments, edge nodes, and Site Agent credentials.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsRegisterOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" /> Register Customer Site
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>Failed to load customer sites: {error instanceof Error ? error.message : "Unknown error"}</span>
        </div>
      )}

      {/* Sites List */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 animate-pulse">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-44 rounded-xl border border-border bg-card p-5" />
          ))}
        </div>
      ) : sites.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border p-12 text-center bg-card/50">
          <Server className="w-12 h-12 mx-auto text-muted-foreground/60 mb-3" />
          <h3 className="text-base font-semibold text-foreground">No Customer Sites Registered</h3>
          <p className="text-xs text-muted-foreground max-w-md mx-auto mt-1 mb-5">
            Register a customer deployment environment to begin installing approved AI packages, managing Blue/Green slots, and running offline inference.
          </p>
          <button
            type="button"
            onClick={() => setIsRegisterOpen(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus className="w-4 h-4" /> Register First Site
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {sites.map((site) => (
            <div
              key={site.id}
              className="rounded-xl border border-border bg-card p-5 shadow-sm hover:border-border/80 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <h3 className="text-base font-semibold text-foreground">{site.site_name}</h3>
                    <p className="text-xs font-mono text-muted-foreground">{site.site_key}</p>
                  </div>
                  {getStatusBadge(site.status)}
                </div>

                <p className="text-xs text-muted-foreground line-clamp-2 mb-4">
                  {site.description || "No description provided."}
                </p>

                <div className="space-y-2 py-3 border-t border-border/60 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Agent Identity</span>
                    <span className="font-medium text-foreground flex items-center gap-1">
                      {site.agent_enrolled ? (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> Enrolled
                        </>
                      ) : (
                        "Pending Enrollment"
                      )}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Runtime Version</span>
                    <span className="font-mono text-foreground">
                      {site.active_runtime_version || "—"}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Last Heartbeat</span>
                    <span className="text-muted-foreground">
                      {site.last_heartbeat_at ? new Date(site.last_heartbeat_at).toLocaleTimeString() : "Never"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-border flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={() => setEnrollingSite(site)}
                  disabled={site.status === "REVOKED"}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-input bg-background hover:bg-muted transition-colors disabled:opacity-50"
                >
                  <Key className="w-3.5 h-3.5 text-primary" /> Token
                </button>

                <div className="flex items-center gap-2">
                  {site.status !== "REVOKED" && (
                    <button
                      type="button"
                      onClick={() => {
                        if (confirm(`Revoke customer site '${site.site_name}' and terminate all agent credentials?`)) {
                          revokeMutation.mutate(site.id);
                        }
                      }}
                      className="px-2.5 py-1.5 text-xs font-medium rounded-lg text-red-600 hover:bg-red-500/10 transition-colors"
                    >
                      Revoke
                    </button>
                  )}

                  <Link
                    to={`/runtime?site_id=${site.id}`}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                  >
                    Console <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Register Site Modal */}
      {isRegisterOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-card border border-border rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <h3 className="text-base font-semibold text-foreground">Register Customer Site</h3>
              <button
                type="button"
                onClick={() => setIsRegisterOpen(false)}
                className="text-muted-foreground hover:text-foreground text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleRegisterSubmit} className="py-4 space-y-3.5">
              <div>
                <label className="text-xs font-medium text-foreground block mb-1">
                  Site Key (Unique Identifier, e.g. site-fra-01) <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={siteKey}
                  onChange={(e) => setSiteKey(e.target.value)}
                  placeholder="site-frankfurt-datacenter"
                  pattern="^[a-z0-9\-_]+$"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-foreground block mb-1">
                  Site Display Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={siteName}
                  onChange={(e) => setSiteName(e.target.value)}
                  placeholder="Frankfurt Primary Edge Node"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-foreground block mb-1">
                  Description / Location Details
                </label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="On-premises private Kubernetes cluster with air-gapped network segment."
                  className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="pt-3 border-t border-border flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsRegisterOpen(false)}
                  className="px-4 py-2 text-xs font-medium rounded-lg border border-input bg-background hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || !siteKey.trim() || !siteName.trim()}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {createMutation.isPending ? "Registering..." : "Register Site"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Enrollment Token Modal */}
      {enrollingSite && (
        <SiteEnrollmentModal
          site={enrollingSite}
          isOpen={!!enrollingSite}
          onClose={() => setEnrollingSite(null)}
        />
      )}
    </div>
  );
};
