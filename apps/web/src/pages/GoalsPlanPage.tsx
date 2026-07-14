import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { plansApi, projectsApi } from "@/api/client";

export function GoalsPlanPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [intent, setIntent] = useState("");

  const { data: goals, isLoading } = useQuery({
    queryKey: ["projects", projectId, "goals"],
    queryFn: () => projectsApi.goals.list(projectId!),
    enabled: !!projectId,
  });

  const createGoal = useMutation({
    mutationFn: () =>
      projectsApi.goals.create(projectId!, {
        title,
        intent,
        constraints: ["Read-only until job workspace created"],
        acceptance_criteria: ["Tests pass after implementation"],
        priority: "medium",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "goals"] });
      setTitle("");
      setIntent("");
    },
  });

  const planMutation = useMutation({
    mutationFn: async (goalId: string) => {
      const plan = await plansApi.propose(goalId);
      await plansApi.approve(plan.id);
      return plansApi.createJob(plan.id);
    },
    onSuccess: (job) => navigate(`/jobs/${job.id}`),
  });

  if (isLoading) return <div className="loading">Loading goals…</div>;

  return (
    <>
      <header className="page-header">
        <Link to={`/projects/${projectId}`}>← Overview</Link>
        <h1>Goals & Plan</h1>
        <nav className="sub-nav">
          <Link to={`/projects/${projectId}`}>Overview</Link>
          <Link to={`/projects/${projectId}/explorer`}>Explorer</Link>
          <Link to={`/projects/${projectId}/goals`} className="active">Goals & Plan</Link>
        </nav>
      </header>

      <div className="card">
        <h2>Create Goal</h2>
        <form
          className="form-stack"
          onSubmit={(e) => {
            e.preventDefault();
            createGoal.mutate();
          }}
        >
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label>
            Intent
            <textarea value={intent} onChange={(e) => setIntent(e.target.value)} required rows={3} />
          </label>
          <button type="submit" className="btn-primary" disabled={createGoal.isPending}>
            {createGoal.isPending ? "Creating…" : "Create Goal"}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Goals</h2>
        {goals?.items.length === 0 && <p className="text-muted">No goals yet.</p>}
        <ul className="goal-list">
          {goals?.items.map((goal) => (
            <li key={goal.id} className="goal-item">
              <div>
                <strong>{goal.title}</strong>
                <span className={`status-badge status-badge--${goal.status}`}>{goal.status}</span>
                <p>{goal.intent}</p>
              </div>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => planMutation.mutate(goal.id)}
                disabled={planMutation.isPending}
              >
                Plan & Start Job
              </button>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
