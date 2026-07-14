import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { projectsApi } from "@/api/client";
import type { Project } from "@/api/types";

function StatusBadge({ status }: { status: string }) {
  return <span className={`status-badge status-badge--${status}`}>{status}</span>;
}

function ProjectCard({ project }: { project: Project }) {
  const manifests = project.preflight?.inventory.manifest_files ?? [];
  return (
    <div className="card project-card">
      <div className="project-card__header">
        <h3>{project.name}</h3>
        <StatusBadge status={project.status} />
      </div>
      <p className="project-card__path">{project.source_location}</p>
      <div className="data-grid">
        <div className="data-item">
          <label>Branch</label>
          <span>{project.default_branch ?? "—"}</span>
        </div>
        <div className="data-item">
          <label>Files</label>
          <span>{project.preflight?.inventory.file_count ?? "—"}</span>
        </div>
        <div className="data-item">
          <label>Manifests</label>
          <span>{manifests.length > 0 ? manifests.join(", ") : "none"}</span>
        </div>
      </div>
      {project.tags.length > 0 && (
        <div className="tag-list">
          {project.tags.map((tag) => (
            <span key={tag} className="tag">{tag}</span>
          ))}
        </div>
      )}
      <Link to={`/projects/${project.id}`} className="project-card__link">
        View details →
      </Link>
    </div>
  );
}

export function PortfolioPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list(),
  });

  return (
    <>
      <header className="page-header">
        <h1>Portfolio</h1>
        <p>Registered managed projects</p>
      </header>

      {isLoading && <div className="loading">Loading projects…</div>}

      {isError && (
        <div className="error-state">
          Failed to load projects.
          {error instanceof Error && <p>{error.message}</p>}
        </div>
      )}

      {data && data.items.length === 0 && (
        <div className="empty-state card">
          <p>No projects registered yet.</p>
          <Link to="/projects/new">Add your first project →</Link>
        </div>
      )}

      {data && data.items.length > 0 && (
        <div className="project-grid">
          {data.items.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </>
  );
}
