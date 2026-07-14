import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { jobsApi } from "@/api/client";

export function DiffReviewPage() {
  const { jobId } = useParams<{ jobId: string }>();

  const { data: job } = useQuery({
    queryKey: ["jobs", jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
  });

  const { data: diff, isLoading, isError } = useQuery({
    queryKey: ["jobs", jobId, "diff"],
    queryFn: () => jobsApi.diff(jobId!),
    enabled: !!jobId,
  });

  if (isLoading) return <div className="loading">Loading diff…</div>;
  if (isError || !diff) return <div className="error-state">Diff not available.</div>;

  return (
    <>
      <header className="page-header">
        <Link to={`/jobs/${jobId}`}>← Job Console</Link>
        <h1>Diff Review</h1>
        <p className="text-muted">Base revision {diff.base_revision.slice(0, 12)}</p>
      </header>

      <div className="card">
        <div className="card-header">
          <h2>Review Status</h2>
          <span className={`status-badge status-badge--${diff.review_status}`}>{diff.review_status}</span>
        </div>
        {job && (
          <p>Project: <Link to={`/projects/${job.project_id}`}>{job.project_id}</Link></p>
        )}
      </div>

      {diff.files.map((file) => (
        <div key={file.path} className="card diff-card">
          <div className="card-header">
            <h3>{file.path}</h3>
            <span className="diff-stats">+{file.additions} / -{file.deletions}</span>
          </div>
          <pre className="diff-patch">{file.patch}</pre>
        </div>
      ))}
    </>
  );
}
