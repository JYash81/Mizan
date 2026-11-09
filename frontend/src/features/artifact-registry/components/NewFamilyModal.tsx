import { useState } from "react";
import { X, Layers, Plus } from "lucide-react";
import { createModelFamily } from "../api";
import type { ModelFamily } from "../types";

interface NewFamilyModalProps {
  workspaceId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (family: ModelFamily) => void;
}

export function NewFamilyModal({ workspaceId, isOpen, onClose, onSuccess }: NewFamilyModalProps) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [taskType, setTaskType] = useState("TEXT_GENERATION");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleNameChange = (val: string) => {
    setName(val);
    if (!slug || slug === name.toLowerCase().replace(/[^a-z0-9]+/g, "-")) {
      setSlug(val.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !slug) {
      setError("Name and slug are required.");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const family = await createModelFamily(workspaceId, {
        name,
        slug,
        task_type: taskType,
        description: description || undefined,
      });
      onSuccess(family);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create model family";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
      <div className="bg-card border border-border rounded-xl shadow-xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between p-5 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-foreground">Create Model Family</h3>
              <p className="text-xs text-muted-foreground">Namespace for versioned model releases</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-md text-muted-foreground hover:text-foreground">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">Family Name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="e.g. Customer Support Assistant"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground focus:ring-1 focus:ring-primary outline-none"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">Slug (Identifier)</label>
            <input
              type="text"
              required
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="customer-support-assistant"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground font-mono text-xs focus:ring-1 focus:ring-primary outline-none"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">Task Type</label>
            <select
              value={taskType}
              onChange={(e) => setTaskType(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground focus:ring-1 focus:ring-primary outline-none"
            >
              <option value="TEXT_GENERATION">Text Generation / Assistant</option>
              <option value="RAG_REASONING">RAG & Knowledge Retrieval</option>
              <option value="CLASSIFICATION">Classification & Routing</option>
              <option value="EMBEDDING">Dense Embedding</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">Description (Optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Purpose, intended scope, target users..."
              className="w-full h-20 px-3 py-2 rounded-lg border border-border bg-background text-xs text-foreground focus:ring-1 focus:ring-primary outline-none resize-none"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-muted-foreground hover:bg-secondary transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              {isSubmitting ? "Creating..." : "Create Family"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
