import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ShieldCheck, X } from "lucide-react";
import { fetchModelFamilies } from "../../artifact-registry/api";
import { createModelListing } from "../api";
import type { CatalogVisibility, DistributionStatus } from "../types";

interface NewModelListingModalProps {
  workspaceId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function NewModelListingModal({
  workspaceId,
  isOpen,
  onClose,
  onSuccess,
}: NewModelListingModalProps) {
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [detailedDescription, setDetailedDescription] = useState("");
  const [category, setCategory] = useState("TEXT_GENERATION");
  const [tagsInput, setTagsInput] = useState("");
  const [visibility, setVisibility] = useState<CatalogVisibility>("WORKSPACE");
  const [distributionStatus, setDistributionStatus] = useState<DistributionStatus>("DOWNLOADABLE");
  const [isFeatured, setIsFeatured] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch approved model families/versions
  const familiesQuery = useQuery({
    queryKey: ["artifact-families", workspaceId],
    queryFn: () => fetchModelFamilies(workspaceId),
    enabled: isOpen,
  });

  const families = familiesQuery.data || [];
  const approvedVersions: Array<{
    id: string;
    versionTag: string;
    familyName: string;
    sourceModel: string;
  }> = [];

  for (const f of families) {
    if (f.versions) {
      for (const v of f.versions) {
        if (v.status === "APPROVED") {
          approvedVersions.push({
            id: v.id,
            versionTag: v.version_tag,
            familyName: f.name,
            sourceModel: v.source_model_key,
          });
        }
      }
    }
  }

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedVersionId) {
      setError("Please select an approved M11 model release to publish.");
      return;
    }
    if (!title.trim() || !description.trim()) {
      setError("Title and description are required.");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      const tags = tagsInput
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);

      await createModelListing(workspaceId, {
        model_version_id: selectedVersionId,
        title: title.trim(),
        slug: slug.trim() || undefined,
        description: description.trim(),
        detailed_description: detailedDescription.trim() || undefined,
        category,
        tags,
        visibility,
        distribution_status: distributionStatus,
        is_featured: isFeatured,
      });

      onSuccess();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create model listing";
      setError(msg);
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
          <ShieldCheck className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold tracking-tight">Create Model Zoo Listing</h2>
        </div>
        <p className="text-xs text-muted-foreground mb-4">
          Publish an approved Gate 3 model release into the workspace, organization, or public catalog.
        </p>

        {error && (
          <div className="p-3 mb-4 rounded-md bg-destructive/10 text-destructive text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">
              Select Approved Release *
            </label>
            {approvedVersions.length === 0 ? (
              <div className="p-3 rounded border border-dashed text-xs text-muted-foreground bg-muted/30">
                No Gate 3 approved model releases found in this workspace. Create and approve a model version in the Artifact Registry first.
              </div>
            ) : (
              <select
                value={selectedVersionId}
                onChange={(e) => {
                  setSelectedVersionId(e.target.value);
                  const selected = approvedVersions.find((v) => v.id === e.target.value);
                  if (selected && !title) {
                    setTitle(`${selected.familyName} ${selected.versionTag}`);
                  }
                }}
                className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
                required
              >
                <option value="">-- Choose an approved version --</option>
                {approvedVersions.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.familyName} ({v.versionTag}) · {v.sourceModel}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-foreground block mb-1">Title *</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Customer Support LLM"
                className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
                required
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-foreground block mb-1">Custom Slug</label>
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="Optional URL identifier"
                className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">Short Description *</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Concise business-ready summary of what this model does"
              className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
              required
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">Detailed Markdown Overview</label>
            <textarea
              value={detailedDescription}
              onChange={(e) => setDetailedDescription(e.target.value)}
              rows={3}
              placeholder="Use cases, evaluation methodology, hardware recommendations..."
              className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground font-mono"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-semibold text-foreground block mb-1">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
              >
                <option value="TEXT_GENERATION">Text Generation</option>
                <option value="CUSTOMER_SUPPORT">Customer Support</option>
                <option value="CODE_GENERATION">Code Generation</option>
                <option value="RAG_EMBEDDINGS">RAG & Embeddings</option>
                <option value="CLASSIFICATION">Classification</option>
                <option value="REASONING">Reasoning</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-foreground block mb-1">Visibility</label>
              <select
                value={visibility}
                onChange={(e) => setVisibility(e.target.value as CatalogVisibility)}
                className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
              >
                <option value="WORKSPACE">Workspace</option>
                <option value="ORGANIZATION">Organization</option>
                <option value="PUBLIC">Public</option>
                <option value="PRIVATE">Private</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-foreground block mb-1">Distribution</label>
              <select
                value={distributionStatus}
                onChange={(e) => setDistributionStatus(e.target.value as DistributionStatus)}
                className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
              >
                <option value="DOWNLOADABLE">Downloadable</option>
                <option value="METADATA_ONLY">Metadata Only</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">Tags (comma-separated)</label>
            <input
              type="text"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              placeholder="e.g. support, lora, llama3, uae"
              className="w-full px-3 py-2 text-xs rounded-md border bg-background text-foreground"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="isFeatured"
              checked={isFeatured}
              onChange={(e) => setIsFeatured(e.target.checked)}
              className="rounded border"
            />
            <label htmlFor="isFeatured" className="text-xs text-foreground font-medium">
              Feature this model prominently in catalog discovery
            </label>
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
              {isSubmitting ? "Creating..." : "Save Draft Listing"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
