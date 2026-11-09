import React, { useState } from "react";
import { Copy, Check, Terminal, AlertCircle } from "lucide-react";
import type { CustomerSite, EnrollmentTokenResponse } from "../types";
import { generateEnrollmentToken } from "../api";

interface SiteEnrollmentModalProps {
  site: CustomerSite;
  isOpen: boolean;
  onClose: () => void;
}

export const SiteEnrollmentModal: React.FC<SiteEnrollmentModalProps> = ({ site, isOpen, onClose }) => {
  const [tokenData, setTokenData] = useState<EnrollmentTokenResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await generateEnrollmentToken(site.workspace_id, site.id);
      setTokenData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate enrollment token.");
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-card border border-border rounded-xl shadow-xl w-full max-w-lg p-6 overflow-hidden">
        <div className="flex items-center justify-between pb-4 border-b border-border">
          <div>
            <h3 className="text-base font-semibold text-foreground">Enroll Site Agent</h3>
            <p className="text-xs text-muted-foreground">Site: {site.site_name} ({site.site_key})</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground text-sm font-medium"
          >
            ✕
          </button>
        </div>

        <div className="py-4 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!tokenData ? (
            <div className="text-center py-6">
              <Terminal className="w-12 h-12 mx-auto text-muted-foreground/60 mb-3" />
              <p className="text-sm text-foreground font-medium">Generate Single-Use Cryptographic Token</p>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1 mb-5">
                Generates 256-bits of high-entropy credentials. The token can only be consumed once by the customer Site Agent.
              </p>
              <button
                type="button"
                onClick={handleGenerate}
                disabled={isLoading}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {isLoading ? "Generating Token..." : "Generate Enrollment Token"}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1">
                  Raw Enrollment Token (Single-Use, Valid for 60m)
                </label>
                <div className="flex items-center gap-2 bg-muted p-2 rounded-lg border border-border">
                  <input
                    type="text"
                    readOnly
                    value={tokenData.raw_token}
                    className="bg-transparent border-0 text-xs font-mono text-foreground flex-1 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => copyToClipboard(tokenData.raw_token)}
                    className="p-1.5 hover:bg-background rounded text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1">
                  Docker Run Command
                </label>
                <div className="bg-slate-950 p-3 rounded-lg border border-border text-xs font-mono text-slate-200 overflow-x-auto">
                  <code>
                    docker run --rm -v mizan-data:/var/lib/mizan/data mizan/site-agent:1.0.0 \<br />
                    &nbsp;&nbsp;--token "{tokenData.raw_token}" \<br />
                    &nbsp;&nbsp;--site-id "{site.id}"
                  </code>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-300 text-xs">
                ⚠️ Store this token securely. It will not be shown again and expires at{" "}
                <span className="font-semibold">{new Date(tokenData.expires_at).toLocaleTimeString()}</span>.
              </div>
            </div>
          )}
        </div>

        <div className="pt-4 border-t border-border flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium rounded-lg border border-input bg-background hover:bg-muted transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
