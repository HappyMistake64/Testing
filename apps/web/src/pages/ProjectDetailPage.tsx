import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { projectsApi } from "@/api/client";

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: project, isLoading, isError } = useQuery({
    queryKey: ["projects", projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  const archiveMutation = useMutation({
    mutationFn: () => projectsApi.archive(projectId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate("/");
    },
  });

  if (isLoading) return <div className="loading">Loading project…</div>;
  if (isError || !project) return <div className="error-state">Project not found.</div>;

  const preflight = project.preflight;

  return (
    <>
      <header className="page-header">
        <Link to="/">← Portfolio</Link>
        <h1>{project.name}</h1>
        <p>{project.source_location}</p>
      </header>

      <div className="card">
        <div className="data-grid">
          <div className="data-item">
            <label>Status</label>
            <span className={`status-badge status-badge--${project.status}`}>
              {project.status}
            </span>
          </div>
          <div className="data-item">
            <label>Slug</label>
            <span>{project.slug}</span>
          </div>
          <div className="data-item">
            <label>Source type</label>
            <span>{project.source_type}</span>
          </div>
          <div className="data-item">
            <label>Branch</label>
            <span>{project.default_branch ?? "—"}</span>
          </div>
        </div>
      </div>

      {preflight && (
        <div className="card">
          <h2>Preflight Report</h2>
          <div className="data-grid">
            <div className="data-item">
              <label>Preflight</label>
              <span className={`status-badge status-badge--${preflight.status}`}>
                {preflight.status}
              </span>
            </div>
            <div className="data-item">
              <label>Files</label>
              <span>{preflight.inventory.file_count}</span>
            </div>
            <div className="data-item">
              <label>Size</label>
              <span>{(preflight.inventory.total_bytes / 1024).toFixed(1)} KB</span>
            </div>
            <div className="data-item">
              <label>Git revision</label>
              <span>{preflight.git.revision ?? "—"}</span>
            </div>
          </div>
          {preflight.inventory.manifest_files.length > 0 && (
            <p>Manifests: {preflight.inventory.manifest_files.join(", ")}</p>
          )}
          {preflight.issues.length > 0 && (
            <ul className="issue-list">
              {preflight.issues.map((issue) => (
                <li key={issue.code} className={`severity-${issue.severity}`}>
                  <strong>{issue.code}</strong>: {issue.message}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {project.status !== "archived" && (
        <button
          type="button"
          className="btn-danger"
          onClick={() => archiveMutation.mutate()}
          disabled={archiveMutation.isPending}
        >
          {archiveMutation.isPending ? "Archiving…" : "Archive Project"}
        </button>
      )}
    </>
  );
}
