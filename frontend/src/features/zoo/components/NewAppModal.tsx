import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Boxes, X } from "lucide-react";
import { fetchModelFamilies } from "../../artifact-registry/api";
import { createAppDefinition, createAppListing, createAppVersion, fetchWorkspaceAppDefinitions } from "../api";
import type { CatalogVisibility } from "../types";

interface NewAppModalProps {
  workspaceId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function NewAppModal({
  workspaceId,
  isOpen,
  onClose,
  onSuccess,
}: NewAppModalProps) {
  const [activeTab, setActiveTab] = useState<"DEFINITION" | "LISTING">("DEFINITION");

  // State for Definition
  const [defName, setDefName] = useState("");
  const [defKey, setDefKey] = useState("");
  const [defDesc, setDefDesc] = useState("");
  const [defCategory, setDefCategory] = useState("CUSTOMER_SUPPORT");

  // State for Version + Listing
  const [selectedDefId, setSelectedDefId] = useState("");
  const [versionTag, setVersionTag] = useState("v1.0.0");
  const [selectedModelVersionId, setSelectedModelVersionId] = useState("");
  const [capabilitiesInput, setCapabilitiesInput] = useState("DOCUMENT_RETRIEVAL, SUMMARIZATION");
  const [listingTitle, setListingTitle] = useState("");
  const [listingDesc, setListingDesc] = useState("");
  const [visibility, setVisibility] = useState<CatalogVisibility>("ORGANIZATION");

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Queries
  const definitionsQuery = useQuery({
    queryKey: ["app-definitions", workspaceId],
    queryFn: () => fetchWorkspaceAppDefinitions(workspaceId),
    enabled: isOpen,
  });

  const familiesQuery = useQuery({
    queryKey: ["artifact-families", workspaceId],
    queryFn: () => fetchModelFamilies(workspaceId),
    enabled: isOpen,
  });

  const definitions = definitionsQuery.data || [];
  const families = familiesQuery.data || [];
  const approvedVersions: Array<{
    id: string;
    versionTag: string;
    familyName: string;
  }> = [];

  for (const f of families) {
    if (f.versions) {
      for (const v of f.versions) {
        if (v.status === "APPROVED") {
          approvedVersions.push({
            id: v.id,
            versionTag: v.version_tag,
            familyName: f.name,
          });
        }
      }
    }
  }

  if (!isOpen) return null;

  const handleCreateDefinition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!defName.trim()) {
      setError("Application name is required.");
      return;
    }
    try {
      setIsSubmitting(true);
      setError(null);
      await createAppDefinition(workspaceId, {
        name: defName.trim(),
        app_key: defKey.trim() || undefined,
        description: defDesc.trim() || undefined,
        category: defCategory,
      });
      definitionsQuery.refetch();
      setActiveTab("LISTING");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create app definition");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateListing = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDefId) {
      setError("Please select an application definition.");
      return;
    }
    if (!selectedModelVersionId) {
      setError("Every app package must bind to an approved Gate 3 model release.");
      return;
    }
    if (!listingTitle.trim() || !listingDesc.trim()) {
      setError("Listing title and description are required.");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      const caps = capabilitiesInput
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean);

      // 1. Create App Version with bound model dependency
      const updatedDef = await createAppVersion(workspaceId, selectedDefId, {
        version_tag: versionTag.trim(),
        capabilities: caps,
        model_dependencies: [
          {
            model_version_id: selectedModelVersionId,
            dependency_role: "PRIMARY_GENERATOR",
          },
        ],
      });

      // Find the newly created version
      const newVer = updatedDef.versions?.find((v) => v.version_tag === versionTag.trim());
      if (!newVer) {
        throw new Error("Version created but could not be located in response.");
      }

      // 2. Create Listing
      await createAppListing(workspaceId, {
        app_version_id: newVer.id,
        title: listingTitle.trim(),
        description: listingDesc.trim(),
        category: defCategory,
        visibility,
      });

      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create app listing");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-xl rounded-lg border bg-card text-card-foreground shadow-lg my-8 p-6">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 text-muted-foreground hover:text-foreground"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 mb-1">
          <Boxes className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold tracking-tight">Register App Zoo Application</h2>
        </div>
        <p className="text-xs text-muted-foreground mb-4">
          Define declarative AI application packages bound to approved M11 model releases.
        </p>

        {/* Tab switcher */}
        <div className="flex border-b mb-4">
          <button
            type="button"
            onClick={() => setActiveTab("DEFINITION")}
            className={`px-4 py-2 text-xs font-semibold border-b-2 -mb-px transition-colors ${
              activeTab === "DEFINITION"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            1. App Definition
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("LISTING")}
            className={`px-4 py-2 text-xs font-semibold border-b-2 -mb-px transition-colors ${
              activeTab === "LISTING"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            2. Package Version & Listing
          </button>
        </div>

        {error && (
          <div className="p-3 mb-4 rounded-md bg-destructive/10 text-destructive text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {activeTab === "DEFINITION" ? (
          <form onSubmit={handleCreateDefinition} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Application Name *</label>
                <input
                  type="text"
                  value={defName}
                  onChange={(e) => setDefName(e.target.value)}
                  placeholder="e.g. Contract Assistant"
                  className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
                  required
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">App Key (slug)</label>
                <input
                  type="text"
                  value={defKey}
                  onChange={(e) => setDefKey(e.target.value)}
                  placeholder="e.g. contract-assistant"
                  className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-foreground block mb-1">Category</label>
              <select
                value={defCategory}
                onChange={(e) => setDefCategory(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
              >
                <option value="CUSTOMER_SUPPORT">Customer Support</option>
                <option value="LEGAL_ANALYSIS">Legal & Contracts</option>
                <option value="INTERNAL_SEARCH">Internal Search / RAG</option>
                <option value="DEVELOPER_TOOLS">Developer Tools</option>
                <option value="OPERATIONS">Operations</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-foreground block mb-1">Description</label>
              <input
                type="text"
                value={defDesc}
                onChange={(e) => setDefDesc(e.target.value)}
                placeholder="High-level purpose of this application"
                className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 text-xs font-medium rounded-md border hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-4 py-1.5 text-xs font-semibold rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {isSubmitting ? "Creating..." : "Save Definition & Proceed"}
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleCreateListing} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-foreground block mb-1">App Definition *</label>
              <select
                value={selectedDefId}
                onChange={(e) => {
                  setSelectedDefId(e.target.value);
                  const d = definitions.find((x) => x.id === e.target.value);
                  if (d && !listingTitle) {
                    setListingTitle(`${d.name} Package`);
                    setListingDesc(d.description || "");
                  }
                }}
                className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
                required
              >
                <option value="">-- Select an application definition --</option>
                {definitions.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.app_key})
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Version Tag *</label>
                <input
                  type="text"
                  value={versionTag}
                  onChange={(e) => setVersionTag(e.target.value)}
                  placeholder="v1.0.0"
                  className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground font-mono"
                  required
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Visibility</label>
                <select
                  value={visibility}
                  onChange={(e) => setVisibility(e.target.value as CatalogVisibility)}
                  className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
                >
                  <option value="ORGANIZATION">Organization</option>
                  <option value="WORKSPACE">Workspace</option>
                  <option value="PUBLIC">Public</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-foreground block mb-1">
                Bound Gate 3 Model Release *
              </label>
              <select
                value={selectedModelVersionId}
                onChange={(e) => setSelectedModelVersionId(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
                required
              >
                <option value="">-- Choose an approved M11 release --</option>
                {approvedVersions.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.familyName} ({v.versionTag})
                  </option>
                ))}
              </select>
              <p className="text-[10px] text-muted-foreground mt-1">
                Strict governance requirement: Apps must explicitly link to an approved model release.
              </p>
            </div>

            <div>
              <label className="text-xs font-semibold text-foreground block mb-1">Declared Capabilities</label>
              <input
                type="text"
                value={capabilitiesInput}
                onChange={(e) => setCapabilitiesInput(e.target.value)}
                placeholder="DOCUMENT_RETRIEVAL, SUMMARIZATION, TOOL_CALLING"
                className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Listing Title *</label>
                <input
                  type="text"
                  value={listingTitle}
                  onChange={(e) => setListingTitle(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
                  required
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Short Description *</label>
                <input
                  type="text"
                  value={listingDesc}
                  onChange={(e) => setListingDesc(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
                  required
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 text-xs font-medium rounded-md border hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || approvedVersions.length === 0}
                className="px-4 py-1.5 text-xs font-semibold rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {isSubmitting ? "Creating..." : "Publish App Package"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
