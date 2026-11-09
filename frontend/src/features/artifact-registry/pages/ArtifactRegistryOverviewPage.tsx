import { useState, useEffect, useMemo, useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Layers,
  GitBranch,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Plus,
  Search,
  Package,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { fetchModelFamilies } from "../api";
import type { ModelFamily, ModelVersion, ModelVersionStatus } from "../types";
import { NewFamilyModal } from "../components/NewFamilyModal";
import { NewVersionModal } from "../components/NewVersionModal";

export function ArtifactRegistryOverviewPage() {
  const { workspaceId: paramWsId } = useParams<{ workspaceId?: string }>();
  const { activeWorkspace } = useAuth();
  const workspaceId = paramWsId || activeWorkspace?.id || "default-ws";

  const [families, setFamilies] = useState<ModelFamily[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [selectedFamilyId, setSelectedFamilyId] = useState<string>("ALL");

  const [isNewFamilyOpen, setIsNewFamilyOpen] = useState(false);
  const [familyForNewVersion, setFamilyForNewVersion] = useState<ModelFamily | null>(null);

  const loadData = useCallback(
    async (silent = false) => {
      if (!silent) setIsLoading(true);
      else setIsRefreshing(true);
      setError(null);
      try {
        const fams = await fetchModelFamilies(workspaceId);
        setFamilies(fams);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to load artifact registry";
        setError(msg);
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [workspaceId]
  );

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Aggregate stats across all families
  const stats = useMemo(() => {
    let totalVersions = 0;
    let approved = 0;
    let pending = 0;
    let revoked = 0;
    let draft = 0;

    families.forEach((fam) => {
      (fam.versions || []).forEach((v) => {
        totalVersions++;
        if (v.status === "APPROVED") approved++;
        else if (v.status === "PENDING_REVIEW") pending++;
        else if (v.status === "REVOKED" || v.status === "REJECTED") revoked++;
        else if (v.status === "DRAFT") draft++;
      });
    });

    return {
      totalFamilies: families.length,
      totalVersions,
      approved,
      pending,
      revoked,
      draft,
    };
  }, [families]);

  // Filtered versions flat list with family reference
  const filteredVersions = useMemo(() => {
    const list: Array<{ family: ModelFamily; version: ModelVersion }> = [];

    families.forEach((fam) => {
      if (selectedFamilyId !== "ALL" && fam.id !== selectedFamilyId) return;

      (fam.versions || []).forEach((ver) => {
        if (statusFilter !== "ALL" && ver.status !== statusFilter) return;

        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matches =
            fam.name.toLowerCase().includes(q) ||
            fam.slug.toLowerCase().includes(q) ||
            ver.version_tag.toLowerCase().includes(q) ||
            ver.source_model_key.toLowerCase().includes(q) ||
            ver.recipe_key.toLowerCase().includes(q);
          if (!matches) return;
        }

        list.push({ family: fam, version: ver });
      });
    });

    return list;
  }, [families, selectedFamilyId, statusFilter, searchQuery]);

  const getStatusBadge = (status: ModelVersionStatus) => {
    switch (status) {
      case "APPROVED":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" />
            Approved
          </span>
        );
      case "PENDING_REVIEW":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 animate-pulse">
            <Clock className="w-3 h-3" />
            Pending Gate 3
          </span>
        );
      case "REVOKED":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
            <AlertTriangle className="w-3 h-3" />
            Revoked
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
            Rejected
          </span>
        );
      case "DRAFT":
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-secondary text-secondary-foreground border border-border">
            Draft
          </span>
        );
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 py-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Layers className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Artifact Registry & Release Management
            </h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Governed immutable model versions, cryptographic manifests, provenance pillars, and Gate 3 release approvals.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadData(true)}
            disabled={isRefreshing}
            className="p-2 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
            title="Refresh releases"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`} />
          </button>
          <button
            onClick={() => setIsNewFamilyOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary/90 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            New Model Family
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-sm text-red-600 dark:text-red-400 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => loadData()} className="underline font-semibold text-xs ml-4">
            Retry
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Model Families
            </p>
            <p className="text-2xl font-bold text-foreground mt-1">{stats.totalFamilies}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{stats.totalVersions} total versions</p>
          </div>
          <div className="p-3 rounded-lg bg-blue-500/10 text-blue-500">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Approved Releases
            </p>
            <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
              {stats.approved}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">Signed & ready for M12</p>
          </div>
          <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-500">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Pending Gate 3
            </p>
            <p className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">
              {stats.pending}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">Awaiting human sign-off</p>
          </div>
          <div className="p-3 rounded-lg bg-amber-500/10 text-amber-500">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 rounded-xl bg-card border border-border shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Drafts & Revoked
            </p>
            <p className="text-2xl font-bold text-foreground mt-1">
              {stats.draft + stats.revoked}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {stats.draft} draft, {stats.revoked} revoked/rejected
            </p>
          </div>
          <div className="p-3 rounded-lg bg-secondary text-muted-foreground">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Filters & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-card border border-border p-4 rounded-xl shadow-sm">
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search families, versions, models..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-lg border border-border bg-background text-sm text-foreground focus:ring-1 focus:ring-primary outline-none"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Family Dropdown */}
          <select
            value={selectedFamilyId}
            onChange={(e) => setSelectedFamilyId(e.target.value)}
            className="px-3 py-2 rounded-lg border border-border bg-background text-xs font-medium text-foreground outline-none"
          >
            <option value="ALL">All Families ({families.length})</option>
            {families.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name} ({f.versions?.length || 0} versions)
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <div className="flex items-center bg-secondary/60 rounded-lg p-1 border border-border text-xs font-medium">
            {["ALL", "APPROVED", "PENDING_REVIEW", "DRAFT", "REVOKED"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  statusFilter === st
                    ? "bg-background text-foreground shadow-xs font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {st === "ALL" ? "All" : st.replace("_", " ")}
              </button>
            ))}
          </div>

          {selectedFamilyId !== "ALL" && (
            <button
              onClick={() => {
                const fam = families.find((f) => f.id === selectedFamilyId);
                if (fam) setFamilyForNewVersion(fam);
              }}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-foreground text-xs font-semibold transition-colors border border-border"
            >
              <Plus className="w-3.5 h-3.5" />
              New Version
            </button>
          )}
        </div>
      </div>

      {/* Model Families & Versions Table */}
      <div className="space-y-6">
        {isLoading ? (
          <div className="text-center py-16 bg-card border border-border rounded-xl">
            <Layers className="w-8 h-8 mx-auto text-muted-foreground/40 animate-pulse mb-3" />
            <p className="text-sm text-muted-foreground">Loading artifact registry...</p>
          </div>
        ) : filteredVersions.length === 0 ? (
          <div className="text-center py-16 bg-card border border-border rounded-xl space-y-4">
            <Package className="w-12 h-12 mx-auto text-muted-foreground/50" />
            <div>
              <h3 className="text-base font-semibold text-foreground">No Model Releases Found</h3>
              <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
                {families.length === 0
                  ? "Start by creating a Model Family to group your versioned releases and cryptographic manifests."
                  : "No versions match your current search and filter criteria."}
              </p>
            </div>
            {families.length === 0 ? (
              <button
                onClick={() => setIsNewFamilyOpen(true)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground font-semibold text-xs hover:bg-primary/90 transition-colors shadow-sm"
              >
                <Plus className="w-4 h-4" />
                Create First Model Family
              </button>
            ) : (
              <button
                onClick={() => {
                  setSearchQuery("");
                  setStatusFilter("ALL");
                  setSelectedFamilyId("ALL");
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-secondary text-foreground text-xs font-medium hover:bg-secondary/80 transition-colors"
              >
                Reset Filters
              </button>
            )}
          </div>
        ) : (
          <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-secondary/50 text-xs font-semibold text-muted-foreground uppercase border-b border-border">
                  <tr>
                    <th className="py-3 px-4">Version & Family</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Source Model</th>
                    <th className="py-3 px-4">Recipe</th>
                    <th className="py-3 px-4">Artifacts</th>
                    <th className="py-3 px-4">Manifest Digest</th>
                    <th className="py-3 px-4">Created</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredVersions.map(({ family, version }) => (
                    <tr
                      key={version.id}
                      className="hover:bg-secondary/20 transition-colors group"
                    >
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2.5">
                          <div className="p-1.5 rounded-md bg-primary/10 text-primary">
                            <GitBranch className="w-4 h-4" />
                          </div>
                          <div>
                            <Link
                              to={`/artifact-registry/${version.id}`}
                              className="font-semibold text-foreground hover:text-primary transition-colors text-sm"
                            >
                              {version.version_tag}
                            </Link>
                            <div className="text-xs text-muted-foreground">
                              {family.name}{" "}
                              <span className="font-mono text-[11px] opacity-70">
                                ({family.slug})
                              </span>
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4">{getStatusBadge(version.status)}</td>
                      <td className="py-3.5 px-4">
                        <span className="font-mono text-xs text-foreground bg-secondary/80 px-2 py-0.5 rounded border border-border">
                          {version.source_model_key}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="text-xs font-medium text-foreground">
                          {version.recipe_key}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                          <Package className="w-3.5 h-3.5 text-primary" />
                          {version.artifacts?.length || 0} artifacts
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        {version.release_manifest_digest ? (
                          <code className="text-xs font-mono text-foreground">
                            {version.release_manifest_digest.slice(0, 10)}...
                          </code>
                        ) : (
                          <span className="text-xs text-muted-foreground italic">
                            Unfinalized
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-xs text-muted-foreground">
                        {new Date(version.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Link
                          to={`/artifact-registry/${version.id}`}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-primary hover:bg-primary/10 transition-colors"
                        >
                          View Details
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* New Family Modal */}
      <NewFamilyModal
        workspaceId={workspaceId}
        isOpen={isNewFamilyOpen}
        onClose={() => setIsNewFamilyOpen(false)}
        onSuccess={(fam) => {
          setFamilies((prev) => [fam, ...prev]);
          setFamilyForNewVersion(fam);
        }}
      />

      {/* New Version Modal */}
      {familyForNewVersion && (
        <NewVersionModal
          workspaceId={workspaceId}
          family={familyForNewVersion}
          isOpen={Boolean(familyForNewVersion)}
          onClose={() => setFamilyForNewVersion(null)}
          onSuccess={() => {
            loadData(true);
          }}
        />
      )}
    </div>
  );
}
