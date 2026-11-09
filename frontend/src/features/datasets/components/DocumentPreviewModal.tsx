import { useState } from "react";
import { Check, Copy, FileText, X } from "lucide-react";
import type { Document } from "../types";

interface DocumentPreviewModalProps {
  document: Document | null;
  onClose: () => void;
}

export function DocumentPreviewModal({ document, onClose }: DocumentPreviewModalProps) {
  const [copied, setCopied] = useState(false);

  if (!document) return null;

  const content = document.extracted_text || document.extracted_text_sample || "";

  const handleCopy = () => {
    if (!content) return;
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-card max-w-2xl w-full max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start pb-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-gray-900">{document.name}</h3>
              <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                <span className="badge-subtle uppercase">{document.file_type}</span>
                <span>•</span>
                <span>{formatSize(document.raw_file_size_bytes)}</span>
                <span>•</span>
                <span>{document.word_count.toLocaleString()} words</span>
                {document.page_count && (
                  <>
                    <span>•</span>
                    <span>{document.page_count} pages</span>
                  </>
                )}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1 rounded-md"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="my-3 py-2 px-3 bg-gray-50 rounded text-xs font-mono text-gray-600 break-all flex justify-between items-center">
          <span>SHA-256: {document.raw_sha256}</span>
        </div>

        {document.extraction_status === "FAILED" && (
          <div className="alert-error my-2">
            <p className="font-semibold">Extraction Failed:</p>
            <p className="text-xs mt-1">{document.extraction_error || "Unknown parser error."}</p>
          </div>
        )}

        <div className="flex-1 overflow-y-auto my-2 p-3 bg-gray-900 text-gray-100 rounded-md font-mono text-xs leading-relaxed max-h-[45vh] whitespace-pre-wrap select-text">
          {content ? content : <span className="text-gray-500 italic">No extracted text content available.</span>}
        </div>

        <div className="flex justify-between items-center pt-3 border-t border-gray-100 mt-2">
          <span className="text-xs text-gray-500">
            {document.char_count.toLocaleString()} characters extracted
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              disabled={!content}
              className="btn-secondary text-xs flex items-center gap-1.5"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? "Copied" : "Copy Text"}
            </button>
            <button onClick={onClose} className="btn-primary text-xs">
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
