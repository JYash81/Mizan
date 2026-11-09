import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Boxes,
  Globe,
  Lock,
  ShieldCheck,
} from "lucide-react";
import { getAppDetail } from "../api";
import { HardwareSnapshotList } from "../components/HardwareBadgePill";
import { InstallationSnippetViewer } from "../components/InstallationSnippetViewer";

export function AppDetailPage() {
  const { listingId } = useParams<{ listingId: string }>();

  const [activeTab, setActiveTab] = useState<
    "OVERVIEW" | "MODELS" | "HARDWARE" | "INSTALL" | "MANIFEST"
  >("OVERVIEW");

  const detailQuery = useQuery({
    queryKey: ["zoo-app-detail", listingId],
    queryFn: () => (listingId ? getAppDetail(listingId) : Promise.reject("No listing ID")),
    enabled: Boolean(listingId),
  });

  const detail = detailQuery.data;

  if (detailQuery.isLoading) {
    return <div className="max-w-7xl mx-auto p-12 text-center text-sm text-muted-foreground">Loading app details...</div>;
  }

  if (detailQuery.isError || !detail) {
    return (
      <div className="max-w-7xl mx-auto p-8 my-6 text-center text-xs text-destructive border rounded-xl bg-destructive/5">
        Failed to load application details. It may be private or unapproved.
      </div>
    );
  }

  const { listing, app_definition, app_version, dependencies, hardware_badges, installation_snippets } = detail;

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6 sm:p-8">
      {/* Top Back Link */}
      <div>
        <Link
          to="/zoo/apps"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to App Zoo
        </Link>

        {/* Title Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-muted font-semibold text-foreground">
                {app_version.version_tag}
              </span>
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-950/40 dark:text-indigo-300">
                {listing.category.replace(/_/g, " ")}
              </span>
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200 dark:bg-purple-950/40 dark:text-purple-300">
                {listing.visibility === "PUBLIC" ? <Globe className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
                {listing.visibility}
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">{listing.title}</h1>
            <p className="text-xs text-muted-foreground mt-1 max-w-2xl">{listing.description}</p>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border bg-muted/40 text-foreground">
              <Boxes className="w-4 h-4 text-primary" />
              <span>Key: {app_definition.app_key}</span>
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b text-xs font-medium space-x-6">
        {(
          [
            { key: "OVERVIEW", label: "Capabilities & Overview" },
            { key: "MODELS", label: `Bound Models (${dependencies.length})` },
            { key: "HARDWARE", label: "Hardware Matrix" },
            { key: "INSTALL", label: "Integration Guides" },
            { key: "MANIFEST", label: "Declarative Manifest" },
          ] as const
        ).map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setActiveTab(t.key)}
            className={`pb-3 border-b-2 font-semibold transition-colors ${
              activeTab === t.key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* TAB CONTENT: Overview */}
      {activeTab === "OVERVIEW" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg border bg-card">
              <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">
                License
              </span>
              <span className="text-sm font-semibold text-foreground">{app_version.license_id}</span>
              <span className="text-xs text-muted-foreground block mt-1">Enterprise approved</span>
            </div>

            <div className="p-4 rounded-lg border bg-card">
              <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">
                Languages
              </span>
              <span className="text-sm font-semibold text-foreground">
                {app_version.supported_languages.join(", ") || "en"}
              </span>
              <span className="text-xs text-muted-foreground block mt-1">Localization support</span>
            </div>

            <div className="p-4 rounded-lg border bg-card">
              <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">
                Manifest Digest
              </span>
              <span className="text-xs font-mono text-foreground truncate block select-all">
                {app_version.manifest_digest.slice(0, 16)}...
              </span>
              <span className="text-xs text-muted-foreground block mt-1">Deterministic SHA-256</span>
            </div>
          </div>

          {/* Capabilities */}
          <div className="p-5 rounded-lg border bg-card space-y-3">
            <h3 className="text-sm font-semibold text-foreground">Declared Capabilities</h3>
            <div className="flex flex-wrap gap-2">
              {app_version.capabilities.map((c) => (
                <span
                  key={c}
                  className="px-2.5 py-1 rounded-md text-xs font-medium bg-primary/10 text-primary border border-primary/20"
                >
                  {c}
                </span>
              ))}
            </div>
          </div>

          {/* Detailed description */}
          {listing.detailed_description && (
            <div className="p-5 rounded-lg border bg-card">
              <h3 className="text-sm font-semibold text-foreground mb-2">Application Description</h3>
              <p className="text-xs text-muted-foreground whitespace-pre-wrap leading-relaxed">
                {listing.detailed_description}
              </p>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: Bound Models */}
      {activeTab === "MODELS" && (
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            Strict governance requirement: Each app version is bound to specific, immutable M11 approved model releases.
          </p>

          <div className="border rounded-lg overflow-hidden bg-card">
            <table className="w-full text-xs text-left">
              <thead className="bg-muted/50 border-b">
                <tr>
                  <th className="p-3 font-semibold">Model Family</th>
                  <th className="p-3 font-semibold">Version Tag</th>
                  <th className="p-3 font-semibold">Dependency Role</th>
                  <th className="p-3 font-semibold">Release Manifest Digest</th>
                  <th className="p-3 font-semibold text-right">Model Release</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {dependencies.map((dep) => (
                  <tr key={dep.id} className="hover:bg-muted/30">
                    <td className="p-3 font-semibold text-foreground">
                      {dep.model_family_name || "Governed Model"}
                    </td>
                    <td className="p-3 font-mono">{dep.model_version_tag || "v1.0.0"}</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-primary/10 text-primary">
                        {dep.dependency_role}
                      </span>
                    </td>
                    <td className="p-3 font-mono text-muted-foreground truncate max-w-[200px]" title={dep.release_manifest_digest}>
                      {dep.release_manifest_digest}
                    </td>
                    <td className="p-3 text-right">
                      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-600 font-medium">
                        <ShieldCheck className="w-3.5 h-3.5" /> Approved
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB CONTENT: Hardware Matrix */}
      {activeTab === "HARDWARE" && (
        <div className="space-y-6">
          <div className="p-4 rounded-lg border bg-card">
            <h3 className="text-sm font-semibold text-foreground mb-1">Hardware Compatibility Snapshots</h3>
            <p className="text-xs text-muted-foreground mb-4">
              Hardware badges derived from combined component and model requirements.
            </p>
            <HardwareSnapshotList snapshots={hardware_badges} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-lg border bg-card">
              <span className="text-xs font-semibold text-muted-foreground block mb-1">App Min RAM</span>
              <span className="text-lg font-bold font-mono text-foreground">
                {(app_version.min_ram_mb / 1024).toFixed(1)} GB
              </span>
            </div>

            <div className="p-4 rounded-lg border bg-card">
              <span className="text-xs font-semibold text-muted-foreground block mb-1">App Min VRAM</span>
              <span className="text-lg font-bold font-mono text-foreground">
                {(app_version.min_vram_mb / 1024).toFixed(1)} GB
              </span>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: Installation Guides */}
      {activeTab === "INSTALL" && (
        <div className="space-y-4">
          <InstallationSnippetViewer snippets={installation_snippets} />
        </div>
      )}

      {/* TAB CONTENT: Declarative Manifest */}
      {activeTab === "MANIFEST" && (
        <div className="space-y-4">
          <div className="p-4 rounded-lg border bg-card space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground">Declarative App Manifest Spec</h3>
              <span className="text-xs font-mono text-muted-foreground">
                SHA-256: {app_version.manifest_digest}
              </span>
            </div>
            <pre className="p-4 text-xs font-mono bg-zinc-950 text-zinc-100 rounded-md overflow-x-auto whitespace-pre leading-relaxed select-all">
              {installation_snippets.declarative_app_manifest || "{\n  \"app_version\": \"" + app_version.version_tag + "\"\n}"}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
