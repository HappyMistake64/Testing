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
