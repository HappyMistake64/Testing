import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { projectsApi } from "@/api/client";

export function ProjectOverviewPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const queryClient = useQueryClient();

  const { data: project, isLoading, isError } = useQuery({
    queryKey: ["projects", projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  const { data: profile } = useQuery({
    queryKey: ["projects", projectId, "profile"],
    queryFn: () => projectsApi.profile(projectId!),
    enabled: !!projectId,
    retry: false,
  });

  const { data: health } = useQuery({
    queryKey: ["projects", projectId, "health"],
    queryFn: () => projectsApi.health(projectId!),
    enabled: !!projectId,
  });

  const analyzeMutation = useMutation({
    mutationFn: () => projectsApi.analyze(projectId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
    },
  });

  if (isLoading) return <div className="loading">Loading project…</div>;
  if (isError || !project) return <div className="error-state">Project not found.</div>;

  return (
    <>
      <header className="page-header">
        <Link to="/">← Portfolio</Link>
        <h1>{project.name}</h1>
        <p className="text-muted">{project.source_location}</p>
        <nav className="sub-nav">
          <Link to={`/projects/${projectId}`} className="active">Overview</Link>
          <Link to={`/projects/${projectId}/explorer`}>Explorer</Link>
          <Link to={`/projects/${projectId}/goals`}>Goals & Plan</Link>
        </nav>
      </header>

      <div className="card">
        <div className="card-header">
          <h2>Status</h2>
          <span className={`status-badge status-badge--${project.status}`}>{project.status}</span>
        </div>
        <div className="data-grid">
          <div className="data-item"><label>Slug</label><span>{project.slug}</span></div>
          <div className="data-item"><label>Branch</label><span>{project.default_branch ?? "—"}</span></div>
          <div className="data-item"><label>Tags</label><span>{project.tags.join(", ") || "—"}</span></div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Project Profile</h2>
          <button
            type="button"
            className="btn-primary"
            onClick={() => analyzeMutation.mutate()}
            disabled={analyzeMutation.isPending}
          >
            {analyzeMutation.isPending ? "Analyzing…" : profile ? "Re-analyze" : "Analyze"}
          </button>
        </div>
        {profile ? (
          <div className="data-grid">
            <div className="data-item"><label>Version</label><span>v{profile.version}</span></div>
            <div className="data-item"><label>Languages</label><span>{profile.languages.join(", ") || "—"}</span></div>
            <div className="data-item"><label>Files</label><span>{profile.file_count}</span></div>
            <div className="data-item"><label>Symbols</label><span>{profile.symbol_count}</span></div>
            <div className="data-item"><label>Revision</label><span>{profile.revision ?? "—"}</span></div>
          </div>
        ) : (
          <p className="text-muted">No profile yet. Run analysis to build project profile.</p>
        )}
      </div>

      {health && health.components.length > 0 && (
        <div className="card">
          <h2>Health Components</h2>
          <ul className="health-list">
            {health.components.map((c) => (
              <li key={c.name} className={`health-item health-item--${c.status}`}>
                <strong>{c.name}</strong>
                <span className={`status-badge status-badge--${c.status}`}>{c.status}</span>
                <p>{c.message}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {project.preflight && (
        <div className="card">
          <h2>Preflight</h2>
          <p>{project.preflight.inventory.file_count} files · {(project.preflight.inventory.total_bytes / 1024).toFixed(1)} KB</p>
        </div>
      )}
    </>
  );
}
