import type {
  DoctorResponse,
  ErrorResponse,
  HealthResponse,
  PreflightReport,
  Project,
  ProjectListResponse,
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
};

export type { Project, ProjectListResponse, PreflightReport, RegisterProjectRequest };
