import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { AddProjectPage } from "@/pages/AddProjectPage";
import { AssistantPage } from "@/pages/AssistantPage";
import { DiffReviewPage } from "@/pages/DiffReviewPage";
import { GoalsPlanPage } from "@/pages/GoalsPlanPage";
import { JobConsolePage } from "@/pages/JobConsolePage";
import { PoliciesPage } from "@/pages/PoliciesPage";
import { PortfolioPage } from "@/pages/PortfolioPage";
import { ProjectExplorerPage } from "@/pages/ProjectExplorerPage";
import { ProjectOverviewPage } from "@/pages/ProjectOverviewPage";
import { SystemStatusPage } from "@/pages/SystemStatusPage";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<PortfolioPage />} />
            <Route path="assistant" element={<AssistantPage />} />
            <Route path="projects/new" element={<AddProjectPage />} />
            <Route path="projects/:projectId" element={<ProjectOverviewPage />} />
            <Route path="projects/:projectId/explorer" element={<ProjectExplorerPage />} />
            <Route path="projects/:projectId/goals" element={<GoalsPlanPage />} />
            <Route path="jobs/:jobId" element={<JobConsolePage />} />
            <Route path="jobs/:jobId/diff" element={<DiffReviewPage />} />
            <Route path="settings/policies" element={<PoliciesPage />} />
            <Route path="system" element={<SystemStatusPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
