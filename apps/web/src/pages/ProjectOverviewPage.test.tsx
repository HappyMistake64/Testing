import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ProjectOverviewPage } from "@/pages/ProjectOverviewPage";
import * as client from "@/api/client";

function renderOverview() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/projects/01TESTPROJECT000000001"]}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectOverviewPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ProjectOverviewPage", () => {
  it("shows project overview with health components", async () => {
    vi.spyOn(client.projectsApi, "get").mockResolvedValue({
      id: "01TESTPROJECT000000001",
      name: "Pilot Small",
      slug: "pilot-small",
      status: "ready",
      source_type: "local_git",
      source_location: "/tmp/pilot",
      default_branch: "main",
      tags: [],
      preflight: null,
      created_at: "2026-07-14T00:00:00Z",
      updated_at: "2026-07-14T00:00:00Z",
      archived_at: null,
    });
    vi.spyOn(client.projectsApi, "profile").mockRejectedValue(new Error("not found"));
    vi.spyOn(client.projectsApi, "health").mockResolvedValue({
      project_id: "01TESTPROJECT000000001",
      components: [
        { name: "inventory", status: "pass", message: "5 source files indexed" },
      ],
    });

    renderOverview();
    expect(await screen.findByText("Pilot Small")).toBeInTheDocument();
    expect(await screen.findByText("inventory")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze/i })).toBeInTheDocument();
  });
});
