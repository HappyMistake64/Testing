import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AssistantPage } from "@/pages/AssistantPage";
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

describe("AssistantPage", () => {
  it("renders chat, approvals, and capabilities", async () => {
    vi.spyOn(client.assistantApi, "status").mockResolvedValue({
      paused: false,
      tools: [
        {
          name: "home_control",
          capability: "device_control",
          description: "Control an allowlisted smart-home entity",
          requires_approval: true,
        },
      ],
      connectors: {
        smart_home: { provider: "LocalSmartHome", local: true },
      },
    });
    vi.spyOn(client.assistantApi.sessions, "list").mockResolvedValue([
      {
        id: "01TESTSESSION0000000000001",
        title: "Session 1",
        provider_id: null,
        model_id: null,
        created_at: "2026-08-02T00:00:00Z",
      },
    ]);
    vi.spyOn(client.assistantApi.turns, "list").mockResolvedValue([
      {
        id: "01TESTTURN000000000000001",
        session_id: "01TESTSESSION0000000000001",
        command: "turn on light.office",
        mode: "execute",
        state: "completed",
        provider_id: null,
        model_id: null,
        response: "light.office is now on.",
        tool_calls: [],
        created_at: "2026-08-02T00:00:00Z",
        updated_at: "2026-08-02T00:00:00Z",
      },
    ]);
    vi.spyOn(client.assistantApi.approvals, "list").mockResolvedValue([
      {
        id: "01TESTAPPROVAL00000000001",
        turn_id: "01TESTTURN000000000000001",
        tool_name: "home_control",
        capability: "device_control",
        args_preview: '{"entity_id": "light.office"}',
        created_at: "2026-08-02T00:00:00Z",
      },
    ]);
    vi.spyOn(client.assistantApi.memory, "list").mockResolvedValue([]);
    vi.spyOn(client.assistantApi.automations, "list").mockResolvedValue([]);

    renderWithProviders(<AssistantPage />);
    expect(await screen.findByText("Assistant")).toBeInTheDocument();
    expect(await screen.findByText("turn on light.office")).toBeInTheDocument();
    expect(await screen.findByText("light.office is now on.")).toBeInTheDocument();
    expect(await screen.findByText("Approve")).toBeInTheDocument();
    expect(await screen.findByText("Emergency stop")).toBeInTheDocument();
    expect((await screen.findAllByText("home_control")).length).toBeGreaterThan(0);
  });
});
