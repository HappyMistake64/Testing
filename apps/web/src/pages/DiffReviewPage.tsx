import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { jobsApi } from "@/api/client";
import type { VerificationDetail } from "@/api/types";

export function DiffReviewPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const queryClient = useQueryClient();

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

  const approveMutation = useMutation({
    mutationFn: () => jobsApi.approveDiff(jobId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs", jobId] });
      queryClient.invalidateQueries({ queryKey: ["jobs", jobId, "diff"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () => jobsApi.rejectDiff(jobId!, "Rejected from diff review UI"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs", jobId] });
      queryClient.invalidateQueries({ queryKey: ["jobs", jobId, "diff"] });
    },
  });

  const applyMutation = useMutation({
    mutationFn: () => jobsApi.applyDiff(jobId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs", jobId] });
      queryClient.invalidateQueries({ queryKey: ["jobs", jobId, "diff"] });
    },
  });

  if (isLoading) return <div className="loading">Loading diff…</div>;
  if (isError || !diff) return <div className="error-state">Diff not available.</div>;

  const canApprove = ["ready", "needs_review", "pending"].includes(diff.review_status);
  const canApply = diff.review_status === "approved";
  const verification = (diff.verification ?? job?.checkpoint?.verification) as VerificationDetail | undefined;

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
        <div className="button-row">
          <button
            type="button"
            onClick={() => approveMutation.mutate()}
            disabled={!canApprove || approveMutation.isPending}
          >
            Approve Diff
          </button>
          <button
            type="button"
            className="btn-danger"
            onClick={() => rejectMutation.mutate()}
            disabled={!canApprove || rejectMutation.isPending}
          >
            Reject Diff
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => applyMutation.mutate()}
            disabled={!canApply || applyMutation.isPending}
          >
            Apply to Source
          </button>
        </div>
        {applyMutation.isSuccess && (
          <p className="text-success">
            Applied {applyMutation.data.promoted_files.length} file(s) to {applyMutation.data.source_path}
          </p>
        )}
        {diff.promoted_files.length > 0 && (
          <p>Promoted: {diff.promoted_files.join(", ")}</p>
        )}
      </div>

      {verification && (
        <div className="card">
          <div className="card-header">
            <h2>Verification</h2>
            <span className={`status-badge status-badge--${verification.result}`}>
              {verification.result}
            </span>
          </div>
          <p>{verification.summary}</p>
          <ul className="verification-checks">
            {verification.checks.map((check) => (
              <li key={check.name} className={`verification-check verification-check--${check.exit_code === 0 ? "pass" : "fail"}`}>
                <strong>{check.name}</strong>
                <span>{check.layer} · exit {check.exit_code}</span>
                {check.stderr_tail && <pre>{check.stderr_tail}</pre>}
              </li>
            ))}
          </ul>
        </div>
      )}

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
