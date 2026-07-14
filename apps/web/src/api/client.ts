import type { DoctorResponse, ErrorResponse, HealthResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ErrorResponse,
  ) {
    super(body.message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    const body = (await response.json()) as ErrorResponse;
    throw new ApiError(response.status, body);
  }

  return response.json() as Promise<T>;
}

export const systemApi = {
  health: () => request<HealthResponse>("/api/v1/system/health"),
  doctor: () => request<DoctorResponse>("/api/v1/system/doctor"),
};
