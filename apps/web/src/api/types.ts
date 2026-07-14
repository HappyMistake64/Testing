/** Stable API error codes matching backend domain types. */
export type ErrorCode =
  | "INTERNAL_ERROR"
  | "VALIDATION_ERROR"
  | "NOT_FOUND"
  | "CONFLICT"
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "DATABASE_ERROR"
  | "CONFIGURATION_ERROR"
  | "SERVICE_UNAVAILABLE";

export interface ErrorDetail {
  field: string | null;
  message: string;
  code: string | null;
}

export interface ErrorResponse {
  error: ErrorCode;
  message: string;
  correlation_id: string;
  details: ErrorDetail[];
}

export interface DatabaseHealth {
  connected: boolean;
  engine: string;
  wal_mode: boolean | null;
  integrity_ok: boolean | null;
  project_count: number | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  database: DatabaseHealth;
  capabilities: Record<string, boolean>;
}

export interface DoctorIssue {
  severity: string;
  code: string;
  message: string;
}

export interface DoctorResponse {
  status: string;
  version: string;
  environment: string;
  settings: Record<string, unknown>;
  checks: Record<string, unknown>;
  issues: DoctorIssue[];
  capabilities: Record<string, boolean>;
}

export interface PreflightIssue {
  code: string;
  severity: string;
  message: string;
}

export interface GitMetadata {
  is_git_repo: boolean;
  branch: string | null;
  revision: string | null;
  dirty: boolean | null;
}

export interface InventorySummary {
  file_count: number;
  total_bytes: number;
  manifest_files: string[];
  sensitive_paths: string[];
}

export interface PreflightReport {
  status: string;
  git: GitMetadata;
  inventory: InventorySummary;
  issues: PreflightIssue[];
  completed_at: string | null;
}

export interface Project {
  id: string;
  name: string;
  slug: string;
  status: string;
  source_type: string;
  source_location: string;
  default_branch: string | null;
  tags: string[];
  preflight: PreflightReport | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
}

export interface RegisterProjectRequest {
  name: string;
  source_path: string;
  tags?: string[];
  require_git?: boolean;
}
