import { useState, useRef, type DragEvent, type ChangeEvent } from "react";
import { AlertCircle, CheckCircle2, Loader2, UploadCloud } from "lucide-react";
import { apiUpload } from "../../../lib/api/client";

interface UploadDropzoneProps {
  workspaceId: string;
  datasetId: string;
  versionId: string;
  onUploadSuccess: () => void;
  disabled?: boolean;
}

const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB
const ALLOWED_EXTENSIONS = [
  "pdf",
  "docx",
  "doc",
  "xlsx",
  "xls",
  "csv",
  "tsv",
  "txt",
  "md",
  "json",
  "jsonl",
  "png",
  "jpg",
  "jpeg",
  "webp",
];

export function UploadDropzone({
  workspaceId,
  datasetId,
  versionId,
  onUploadSuccess,
  disabled = false,
}: UploadDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progressMsg, setProgressMsg] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (disabled || uploading) return;
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled || uploading) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await processFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInputChange = async (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await processFiles(Array.from(e.target.files));
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const processFiles = async (files: File[]) => {
    setErrorMessage(null);
    setSuccessMessage(null);
    setUploading(true);

    let successCount = 0;
    const errors: string[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setProgressMsg(`Uploading ${file.name} (${i + 1}/${files.length})...`);

      // 1. Client-side extension check
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (!ext || !ALLOWED_EXTENSIONS.includes(ext)) {
        errors.push(`${file.name}: Unsupported file extension .${ext}`);
        continue;
      }

      // 2. Client-side size check
      if (file.size > MAX_FILE_SIZE_BYTES) {
        errors.push(`${file.name}: Exceeds 25 MB limit (${(file.size / 1024 / 1024).toFixed(1)} MB)`);
        continue;
      }

      // 3. Upload to API
      const formData = new FormData();
      formData.append("file", file);

      try {
        await apiUpload(
          `/api/v1/workspaces/${workspaceId}/datasets/${datasetId}/versions/${versionId}/documents/upload`,
          formData
        );
        successCount++;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        errors.push(`${file.name}: ${msg}`);
      }
    }

    setUploading(false);
    setProgressMsg(null);

    if (successCount > 0) {
      setSuccessMessage(`Successfully uploaded and parsed ${successCount} document${successCount > 1 ? "s" : ""}.`);
      onUploadSuccess();
    }

    if (errors.length > 0) {
      setErrorMessage(errors.join(" | "));
    }
  };

  return (
    <div className="w-full">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && !uploading && fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-all cursor-pointer ${
          isDragging
            ? "border-emerald-500 bg-emerald-50/50"
            : disabled
            ? "border-gray-200 bg-gray-50 opacity-60 cursor-not-allowed"
            : "border-gray-300 hover:border-emerald-500 hover:bg-gray-50/80 bg-white"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          data-testid="file-upload-input"
          multiple
          className="hidden"
          disabled={disabled || uploading}
          accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.tsv,.txt,.md,.json,.jsonl,.png,.jpg,.jpeg,.webp"
          onChange={handleFileInputChange}
        />

        <div className="flex flex-col items-center justify-center gap-2">
          {uploading ? (
            <Loader2 className="w-10 h-10 text-emerald-600 animate-spin" />
          ) : (
            <div className="p-3 bg-emerald-50 text-emerald-600 rounded-full">
              <UploadCloud className="w-6 h-6" />
            </div>
          )}

          <div className="text-sm">
            {uploading ? (
              <span className="font-medium text-emerald-700">{progressMsg}</span>
            ) : (
              <>
                <span className="font-semibold text-gray-900">Click to upload</span> or drag and drop
              </>
            )}
          </div>

          <p className="text-xs text-gray-500 max-w-md">
            PDF, Word (.docx), Excel (.xlsx), CSV, TXT, Markdown, JSON, JSONL, or Images. Max 25 MB per file.
          </p>
        </div>
      </div>

      {successMessage && (
        <div className="mt-3 p-3 bg-emerald-50 border border-emerald-200 rounded-md text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{successMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md text-red-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
}
