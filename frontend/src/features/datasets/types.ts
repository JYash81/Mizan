export interface DatasetVersion {
  id: string;
  dataset_id: string;
  version_number: number;
  name: string;
  description: string | null;
  status: "DRAFT" | "PROCESSING" | "READY" | "ARCHIVED";
  total_documents: number;
  total_raw_bytes: number;
  content_hash: string | null;
  created_at: string;
  updated_at: string;
}

export interface Dataset {
  id: string;
  workspace_id: string;
  name: string;
  slug: string;
  description: string | null;
  status: "ACTIVE" | "ARCHIVED";
  created_by: string;
  created_at: string;
  updated_at: string;
  active_version?: DatasetVersion | null;
}

export interface Document {
  id: string;
  dataset_version_id: string;
  workspace_id: string;
  name: string;
  file_type: "PDF" | "DOCX" | "XLSX" | "CSV" | "TXT" | "JSON" | "JSONL" | "IMAGE";
  mime_type: string;
  raw_file_size_bytes: number;
  raw_sha256: string;
  extracted_text_sample: string | null;
  extracted_text?: string | null;
  char_count: number;
  word_count: number;
  page_count: number | null;
  extraction_status: "PENDING" | "PARSING" | "COMPLETED" | "FAILED";
  extraction_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProcessingJob {
  id: string;
  workspace_id: string;
  dataset_version_id: string | null;
  document_id: string | null;
  job_type: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  progress_pct: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateDatasetPayload {
  name: string;
  slug?: string;
  description?: string;
}

export interface CreateVersionPayload {
  name?: string;
  description?: string;
}
