import type {
  ApplyDiffResponse,
  AssistantApproval,
  AssistantAutomation,
  AssistantMemory,
  AssistantSession,
  AssistantStatus,
  AssistantTurn,
  CreateGoalRequest,
  DiffResponse,
  DoctorResponse,
  ErrorResponse,
  ExplorerResponse,
  Goal,
  GoalListResponse,
  HealthResponse,
  Job,
  Plan,
  PolicyListResponse,
  PreflightReport,
  Project,
  ProjectHealthResponse,
  ProjectListResponse,
  ProjectProfile,
  RegisterProjectRequest,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ErrorResponse | { detail?: unknown },
  ) {
    const message =
      "message" in body && typeof (body as ErrorResponse).message === "string"
        ? (body as ErrorResponse).message
        : "API request failed";
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = (await response.json()) as ErrorResponse;
    throw new ApiError(response.status, body);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const systemApi = {
  health: () => request<HealthResponse>("/api/v1/system/health"),
  doctor: () => request<DoctorResponse>("/api/v1/system/doctor"),
};

export const projectsApi = {
  list: (includeArchived = false) =>
    request<ProjectListResponse>(
      `/api/v1/projects?include_archived=${includeArchived}`,
    ),
  get: (id: string) => request<Project>(`/api/v1/projects/${id}`),
  register: (body: RegisterProjectRequest) =>
    request<Project>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (id: string, body: Partial<RegisterProjectRequest>) =>
    request<Project>(`/api/v1/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  archive: (id: string) =>
    request<Project>(`/api/v1/projects/${id}/archive`, { method: "POST" }),
  analyze: (id: string) =>
    request<ProjectProfile>(`/api/v1/projects/${id}/analyze`, { method: "POST" }),
  profile: (id: string) =>
    request<ProjectProfile>(`/api/v1/projects/${id}/profile`),
  health: (id: string) =>
    request<ProjectHealthResponse>(`/api/v1/projects/${id}/health`),
  explorer: (id: string, q?: string) => {
    const params = q ? `?q=${encodeURIComponent(q)}` : "";
    return request<ExplorerResponse>(`/api/v1/projects/${id}/explorer${params}`);
  },
  goals: {
    list: (id: string) =>
      request<GoalListResponse>(`/api/v1/projects/${id}/goals`),
    create: (id: string, body: CreateGoalRequest) =>
      request<Goal>(`/api/v1/projects/${id}/goals`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
  },
};

export const plansApi = {
  propose: (goalId: string) =>
    request<Plan>(`/api/v1/plans?goal_id=${encodeURIComponent(goalId)}`, {
      method: "POST",
    }),
  approve: (planId: string) =>
    request<Plan>(`/api/v1/plans/${planId}/approve`, { method: "POST" }),
  createJob: (planId: string) =>
    request<Job>(`/api/v1/plans/${planId}/jobs`, { method: "POST" }),
};

export const jobsApi = {
  get: (jobId: string) => request<Job>(`/api/v1/jobs/${jobId}`),
  pause: (jobId: string) =>
    request<Job>(`/api/v1/jobs/${jobId}/pause`, { method: "POST" }),
  resume: (jobId: string) =>
    request<Job>(`/api/v1/jobs/${jobId}/resume`, { method: "POST" }),
  cancel: (jobId: string) =>
    request<Job>(`/api/v1/jobs/${jobId}/cancel`, { method: "POST" }),
  eventsStreamUrl: (jobId: string, after = 0) =>
    `${API_BASE}/api/v1/jobs/${jobId}/events?after=${after}`,
  diff: (jobId: string) => request<DiffResponse>(`/api/v1/jobs/${jobId}/diff`),
  approveDiff: (jobId: string) =>
    request<Job>(`/api/v1/jobs/${jobId}/diff/approve`, { method: "POST" }),
  rejectDiff: (jobId: string, reason = "") =>
    request<Job>(`/api/v1/jobs/${jobId}/diff/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  applyDiff: (jobId: string) =>
    request<ApplyDiffResponse>(`/api/v1/jobs/${jobId}/diff/apply`, { method: "POST" }),
};

export const policiesApi = {
  list: () => request<PolicyListResponse>("/api/v1/policies"),
};

export const assistantApi = {
  status: () => request<AssistantStatus>("/api/v1/assistant/status"),
  emergencyStop: (paused: boolean, reason = "") =>
    request<{ paused: boolean; revoked_approvals: number }>(
      "/api/v1/assistant/emergency-stop",
      { method: "POST", body: JSON.stringify({ paused, reason }) },
    ),
  sessions: {
    list: () => request<AssistantSession[]>("/api/v1/assistant/sessions"),
    create: (title = "") =>
      request<AssistantSession>("/api/v1/assistant/sessions", {
        method: "POST",
        body: JSON.stringify({ title }),
      }),
  },
  turns: {
    list: (sessionId: string) =>
      request<AssistantTurn[]>(`/api/v1/assistant/sessions/${sessionId}/turns`),
    create: (sessionId: string, command: string, mode = "execute") =>
      request<AssistantTurn>(`/api/v1/assistant/sessions/${sessionId}/turns`, {
        method: "POST",
        body: JSON.stringify({ command, mode }),
      }),
    get: (turnId: string) => request<AssistantTurn>(`/api/v1/assistant/turns/${turnId}`),
    execute: (turnId: string) =>
      request<AssistantTurn>(`/api/v1/assistant/turns/${turnId}/execute`, {
        method: "POST",
      }),
  },
  approvals: {
    list: () => request<AssistantApproval[]>("/api/v1/assistant/approvals"),
    approve: (approvalId: string) =>
      request<{ approval_id: string; turn_id: string; decision: string; turn_requeued: boolean }>(
        `/api/v1/assistant/approvals/${approvalId}/approve`,
        { method: "POST" },
      ),
    deny: (approvalId: string) =>
      request<{ approval_id: string; turn_id: string; decision: string; turn_requeued: boolean }>(
        `/api/v1/assistant/approvals/${approvalId}/deny`,
        { method: "POST" },
      ),
  },
  memory: {
    list: (query?: string) =>
      request<AssistantMemory[]>(
        `/api/v1/assistant/memory${query ? `?query=${encodeURIComponent(query)}` : ""}`,
      ),
    store: (content: string) =>
      request<AssistantMemory>("/api/v1/assistant/memory", {
        method: "POST",
        body: JSON.stringify({ content }),
      }),
    remove: (memoryId: string) =>
      request<void>(`/api/v1/assistant/memory/${memoryId}`, { method: "DELETE" }),
  },
  automations: {
    list: () => request<AssistantAutomation[]>("/api/v1/assistant/automations"),
    create: (body: {
      name: string;
      command: string;
      schedule_kind: string;
      interval_seconds?: number | null;
      delay_seconds?: number | null;
    }) =>
      request<AssistantAutomation>("/api/v1/assistant/automations", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    toggle: (automationId: string) =>
      request<AssistantAutomation>(
        `/api/v1/assistant/automations/${automationId}/toggle`,
        { method: "POST" },
      ),
    remove: (automationId: string) =>
      request<void>(`/api/v1/assistant/automations/${automationId}`, { method: "DELETE" }),
  },
};

export type { Project, ProjectListResponse, PreflightReport, RegisterProjectRequest };
