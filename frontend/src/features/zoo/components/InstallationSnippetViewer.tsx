import { useState } from "react";
import { Check, Copy, Shield, Terminal } from "lucide-react";

interface InstallationSnippetViewerProps {
  snippets: Record<string, string>;
  title?: string;
}

export function InstallationSnippetViewer({
  snippets,
  title = "Integration & Installation Guides",
}: InstallationSnippetViewerProps) {
  const keys = Object.keys(snippets);
  const [selectedKey, setSelectedKey] = useState<string>(keys[0] || "");
  const [copied, setCopied] = useState(false);

  const snippetNames: Record<string, string> = {
    python_transformers: "Python (Transformers)",
    llamacpp_cli: "Llama.cpp CLI",
    declarative_app_manifest: "App Manifest Spec",
    m13_serving_spec: "M13 Runtime Notice",
    api_curl_binding: "API / cURL",
  };

  const handleCopy = () => {
    const code = snippets[selectedKey];
    if (code) {
      navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (keys.length === 0) {
    return (
      <div className="p-4 rounded-lg border border-dashed text-sm text-muted-foreground">
        No installation guides or code snippets available for this listing.
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b flex flex-wrap items-center justify-between gap-3 bg-muted/40">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-primary" />
          <h4 className="text-sm font-semibold tracking-tight">{title}</h4>
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {keys.map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setSelectedKey(k)}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                selectedKey === k
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              {snippetNames[k] || k.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Security & Truthfulness Banner */}
      <div className="px-4 py-2 bg-amber-500/10 border-b border-amber-500/20 text-xs flex items-center gap-2 text-amber-900 dark:text-amber-200">
        <Shield className="w-3.5 h-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
        <span>
          Deterministic installation specification pinned to release manifest digest. Zero secrets, zero credential transmission, zero command execution.
        </span>
      </div>

      <div className="relative">
        <button
          type="button"
          onClick={handleCopy}
          className="absolute right-3 top-3 px-2 py-1 bg-background/80 hover:bg-background border rounded text-xs font-medium flex items-center gap-1 shadow-sm backdrop-blur transition-colors"
          title="Copy code snippet to clipboard"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-600" />
              <span>Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5 text-muted-foreground" />
              <span>Copy</span>
            </>
          )}
        </button>

        <pre className="p-4 text-xs font-mono bg-zinc-950 text-zinc-100 overflow-x-auto whitespace-pre leading-relaxed select-all">
          {snippets[selectedKey] || "# No content"}
        </pre>
      </div>
    </div>
  );
}
