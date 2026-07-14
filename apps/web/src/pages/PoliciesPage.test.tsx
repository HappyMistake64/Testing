import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { PoliciesPage } from "@/pages/PoliciesPage";
import * as client from "@/api/client";

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PoliciesPage", () => {
  it("renders policy list", async () => {
    vi.spyOn(client.policiesApi, "list").mockResolvedValue({
      total: 1,
      items: [
        {
          id: "01TESTPOLICY00000000001",
          scope_type: "global",
          scope_id: null,
          rule_type: "network_egress",
          effect: "deny",
          parameters: {},
          version: 1,
          enabled: true,
          created_at: "2026-07-14T00:00:00Z",
        },
      ],
    });

    renderWithProviders(<PoliciesPage />);
    expect(await screen.findByText("Guardian Policies")).toBeInTheDocument();
    expect(await screen.findByText("network_egress")).toBeInTheDocument();
  });
});
