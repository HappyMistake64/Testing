/** Extended API types for M2-M9 endpoints. */

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
  resource_budgets?: Record<string, number>;
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

export interface HealthComponent {
  name: string;
  status: string;
  message: string;
  evidence?: Record<string, unknown>;
}

export interface ProjectHealthResponse {
  project_id: string;
  components: HealthComponent[];
}

export interface ProjectProfile {
  id: string;
  project_id: string;
  version: number;
  revision: string | null;
  languages: string[];
  frameworks: string[];
  commands: Record<string, string>;
  file_count: number;
  symbol_count: number;
  created_at: string;
}

export interface SymbolInfo {
  name: string;
  kind: string;
  line: number;
}

export interface ExplorerNode {
  path: string;
  is_dir: boolean;
  size_bytes?: number;
  symbols: SymbolInfo[];
  children: ExplorerNode[];
}

export interface ExplorerResponse {
  project_id: string;
  root: ExplorerNode;
}

export interface Goal {
  id: string;
  project_id: string;
  title: string;
  intent: string;
  constraints: string[];
  priority: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface GoalListResponse {
  items: Goal[];
}

export interface CreateGoalRequest {
  title: string;
  intent: string;
  constraints?: string[];
  acceptance_criteria?: string[];
  priority?: string;
}

export interface PlanStep {
  ordinal: number;
  title: string;
  description: string;
  step_type: string;
  acceptance_criteria: string[];
}

export interface Plan {
  id: string;
  goal_id: string;
  version: number;
  status: string;
  assumptions: string[];
  steps: PlanStep[];
  test_plan: string[];
  risk_level: string;
  model_id: string | null;
  created_at: string;
  approved_at: string | null;
}

export interface Job {
  id: string;
  project_id: string;
  job_type: string;
  state: string;
  autonomy_level: string;
  payload: Record<string, unknown>;
  worker_id: string | null;
  lease_expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobEvent {
  id: string;
  sequence: number;
  event_type: string;
  payload_json: string;
  payload_hash: string;
  previous_event_hash: string | null;
  event_hash: string;
  timestamp: string;
}

export interface DiffFile {
  path: string;
  status: string;
  additions: number;
  deletions: number;
  patch: string;
}

export interface DiffResponse {
  job_id: string;
  base_revision: string;
  files: DiffFile[];
  review_status: string;
  findings: Array<Record<string, unknown>>;
}

export interface Policy {
  id: string;
  scope_type: string;
  scope_id: string | null;
  rule_type: string;
  effect: string;
  parameters: Record<string, unknown>;
  version: number;
  enabled: boolean;
  created_at: string | null;
}

export interface PolicyListResponse {
  items: Policy[];
  total: number;
}
