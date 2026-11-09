export type CatalogVisibility = "PRIVATE" | "WORKSPACE" | "ORGANIZATION" | "PUBLIC";

export type PublicationStatus =
  | "DRAFT"
  | "SUBMITTED_FOR_REVIEW"
  | "PUBLISHED"
  | "REJECTED"
  | "SUSPENDED"
  | "ARCHIVED";

export type DistributionStatus = "DOWNLOADABLE" | "METADATA_ONLY" | "UNAVAILABLE";

export type HardwareCompatibilityBadge = "TESTED" | "ESTIMATED" | "INCOMPATIBLE" | "UNKNOWN";

export interface HardwareSnapshot {
  badge: HardwareCompatibilityBadge;
  hardware_profile_key?: string | null;
  hardware_name?: string | null;
  category?: string | null;
  evidence_type?: string | null;
  measured_throughput_tokens_per_sec?: number | null;
  measured_latency_ms?: number | null;
  notes?: string | null;
  snapshot_digest?: string | null;
}

export interface ModelListingSummary {
  id: string;
  organization_id: string;
  workspace_id: string;
  model_family_id: string;
  model_version_id: string;
  title: string;
  slug: string;
  description: string;
  category: string;
  tags: string[];
  visibility: CatalogVisibility;
  publication_status: PublicationStatus;
  distribution_status: DistributionStatus;
  publication_digest?: string | null;
  is_featured: boolean;
  created_at: string;
  published_at?: string | null;
  model_family_name?: string | null;
  model_family_slug?: string | null;
  version_tag?: string | null;
  source_model_key?: string | null;
  final_evaluation_score?: number | null;
}

export interface ModelArtifactInfo {
  id: string;
  artifact_type: string;
  format: string;
  quantization_type?: string | null;
  file_size_bytes: number;
  sha256: string;
  is_primary_weights: boolean;
}

export interface ModelListingDetail {
  listing: {
    id: string;
    title: string;
    slug: string;
    description: string;
    detailed_description?: string | null;
    category: string;
    tags: string[];
    visibility: CatalogVisibility;
    publication_status: PublicationStatus;
    distribution_status: DistributionStatus;
    publication_digest?: string | null;
    created_at: string;
    published_at?: string | null;
  };
  model_family: {
    id: string;
    name: string;
    slug: string;
    task_type: string;
  };
  model_version: {
    id: string;
    version_tag: string;
    source_model_key: string;
    source_model_revision?: string | null;
    recipe_key?: string | null;
    base_evaluation_score?: number | null;
    final_evaluation_score?: number | null;
    quality_delta?: number | null;
    min_ram_mb: number;
    min_vram_mb: number;
    target_hardware_key?: string | null;
    release_manifest_digest: string;
  };
  artifacts: ModelArtifactInfo[];
  hardware_badges: HardwareSnapshot[];
  installation_snippets: Record<string, string>;
  version_history: Array<{
    id: string;
    version_tag: string;
    status: string;
    created_at: string;
    release_manifest_digest?: string | null;
  }>;
}

export interface AppListingSummary {
  id: string;
  organization_id: string;
  workspace_id: string;
  app_definition_id: string;
  app_version_id: string;
  title: string;
  slug: string;
  description: string;
  category: string;
  tags: string[];
  visibility: CatalogVisibility;
  publication_status: PublicationStatus;
  distribution_status: DistributionStatus;
  publication_digest?: string | null;
  is_featured: boolean;
  created_at: string;
  published_at?: string | null;
  app_name?: string | null;
  app_key?: string | null;
  version_tag?: string | null;
  dependency_count: number;
}

export interface AppModelDependencyInfo {
  id: string;
  model_family_id: string;
  model_version_id: string;
  release_manifest_digest: string;
  dependency_role: string;
  model_family_name?: string | null;
  model_family_slug?: string | null;
  model_version_tag?: string | null;
}

export interface AppListingDetail {
  listing: {
    id: string;
    title: string;
    slug: string;
    description: string;
    detailed_description?: string | null;
    category: string;
    tags: string[];
    visibility: CatalogVisibility;
    publication_status: PublicationStatus;
    distribution_status: DistributionStatus;
    publication_digest?: string | null;
    created_at: string;
    published_at?: string | null;
  };
  app_definition: {
    id: string;
    name: string;
    app_key: string;
    category: string;
  };
  app_version: {
    id: string;
    version_tag: string;
    manifest_digest: string;
    license_id: string;
    capabilities: string[];
    supported_input_types: string[];
    supported_output_types: string[];
    supported_languages: string[];
    min_ram_mb: number;
    min_vram_mb: number;
    target_hardware_key?: string | null;
  };
  dependencies: AppModelDependencyInfo[];
  hardware_badges: HardwareSnapshot[];
  installation_snippets: Record<string, string>;
  version_history: Array<{
    id: string;
    version_tag: string;
    status: string;
    manifest_digest: string;
    created_at: string;
  }>;
}

export interface AppDefinition {
  id: string;
  organization_id: string;
  workspace_id: string;
  name: string;
  app_key: string;
  description?: string | null;
  category: string;
  status: string;
  created_at: string;
  versions?: AppVersion[];
}

export interface AppVersion {
  id: string;
  app_definition_id: string;
  version_tag: string;
  description?: string | null;
  manifest_digest: string;
  license_id: string;
  capabilities: string[];
  supported_input_types: string[];
  supported_output_types: string[];
  supported_languages: string[];
  min_ram_mb: number;
  min_vram_mb: number;
  target_hardware_key?: string | null;
  status: string;
  created_at: string;
  model_dependencies?: AppModelDependencyInfo[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreateModelListingRequest {
  model_version_id: string;
  title: string;
  slug?: string;
  description: string;
  detailed_description?: string;
  category?: string;
  tags?: string[];
  visibility?: CatalogVisibility;
  distribution_status?: DistributionStatus;
  is_featured?: boolean;
}

export interface CreateAppDefinitionRequest {
  name: string;
  app_key?: string;
  description?: string;
  category?: string;
}

export interface CreateAppVersionRequest {
  version_tag: string;
  description?: string;
  capabilities?: string[];
  supported_input_types?: string[];
  supported_output_types?: string[];
  supported_languages?: string[];
  license_id?: string;
  min_ram_mb?: number;
  min_vram_mb?: number;
  target_hardware_key?: string;
  model_dependencies?: Array<{
    model_version_id: string;
    dependency_role?: string;
  }>;
}

export interface CreateAppListingRequest {
  app_version_id: string;
  title: string;
  slug?: string;
  description: string;
  detailed_description?: string;
  category?: string;
  tags?: string[];
  visibility?: CatalogVisibility;
  distribution_status?: DistributionStatus;
  is_featured?: boolean;
}

export interface ReviewListingRequest {
  decision: "APPROVED" | "REJECTED";
  rationale: string;
}

export interface SuspendListingRequest {
  reason: string;
}

export interface DownloadAuthorizationResponse {
  authorized: boolean;
  artifact_id: string;
  storage_reference: string;
  sha256: string;
  file_size_bytes: number;
  download_url: string;
  expires_in_seconds: number;
}
