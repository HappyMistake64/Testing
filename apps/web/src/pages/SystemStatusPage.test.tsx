import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SystemStatusPage } from "@/pages/SystemStatusPage";
import * as client from "@/api/client";

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe("SystemStatusPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows loading state initially", () => {
    vi.spyOn(client.systemApi, "health").mockReturnValue(new Promise(() => {}));
    vi.spyOn(client.systemApi, "doctor").mockReturnValue(new Promise(() => {}));

    renderWithQuery(<SystemStatusPage />);
    expect(screen.getByText(/loading system status/i)).toBeInTheDocument();
  });

  it("shows health data on success", async () => {
    vi.spyOn(client.systemApi, "health").mockResolvedValue({
      status: "healthy",
      version: "0.1.0",
      environment: "test",
      database: {
        connected: true,
        engine: "sqlite",
        wal_mode: true,
        integrity_ok: true,
        project_count: 0,
      },
      capabilities: { project_registry: false },
    });
    vi.spyOn(client.systemApi, "doctor").mockResolvedValue({
      status: "pass",
      version: "0.1.0",
      environment: "test",
      settings: {},
      checks: {},
      issues: [],
      capabilities: {},
    });

    renderWithQuery(<SystemStatusPage />);
    expect(await screen.findByText("0.1.0")).toBeInTheDocument();
    expect(screen.getByText(/healthy/i)).toBeInTheDocument();
  });

  it("shows error state on failure", async () => {
    vi.spyOn(client.systemApi, "health").mockRejectedValue(new Error("Network error"));
    vi.spyOn(client.systemApi, "doctor").mockRejectedValue(new Error("Network error"));

    renderWithQuery(<SystemStatusPage />);
    await waitFor(
      () => {
        expect(screen.getByText(/failed to load system status/i)).toBeInTheDocument();
      },
      { timeout: 5000 },
    );
  });
});
