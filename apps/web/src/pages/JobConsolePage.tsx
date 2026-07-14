import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { jobsApi } from "@/api/client";
import type { JobEvent, VerificationDetail } from "@/api/types";

export function JobConsolePage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [after, setAfter] = useState(0);

  const { data: job, isLoading, isError } = useQuery({
    queryKey: ["jobs", jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
    refetchInterval: 3000,
  });

  const pauseMutation = useMutation({ mutationFn: () => jobsApi.pause(jobId!) });
  const resumeMutation = useMutation({ mutationFn: () => jobsApi.resume(jobId!) });
  const cancelMutation = useMutation({ mutationFn: () => jobsApi.cancel(jobId!) });

  useEffect(() => {
    if (!jobId) return;
    const source = new EventSource(jobsApi.eventsStreamUrl(jobId, after));
    source.onmessage = (msg) => {
      const event = JSON.parse(msg.data) as JobEvent;
      setEvents((prev) => [...prev, event]);
      setAfter(event.sequence);
    };
    return () => source.close();
  }, [jobId, after]);

  if (isLoading) return <div className="loading">Loading job…</div>;
  if (isError || !job) return <div className="error-state">Job not found.</div>;

  const verification = job.checkpoint?.verification as VerificationDetail | undefined;
  const reviewStatus = typeof job.checkpoint?.review_status === "string"
    ? job.checkpoint.review_status
    : null;

  return (
    <>
      <header className="page-header">
        <Link to={`/projects/${job.project_id}/goals`}>← Goals</Link>
        <h1>Job Console</h1>
        <p className="text-muted">{job.job_type} · {job.id}</p>
      </header>

      <div className="card">
        <div className="card-header">
          <h2>State</h2>
          <span className={`status-badge status-badge--${job.state}`}>{job.state}</span>
        </div>
        <div className="data-grid">
          <div className="data-item"><label>Autonomy</label><span>{job.autonomy_level}</span></div>
          <div className="data-item"><label>Worker</label><span>{job.worker_id ?? "—"}</span></div>
          {reviewStatus && (
            <div className="data-item">
              <label>Review</label>
              <span className={`status-badge status-badge--${reviewStatus}`}>{reviewStatus}</span>
            </div>
          )}
        </div>
        <div className="button-row">
          <button type="button" onClick={() => pauseMutation.mutate()} disabled={pauseMutation.isPending}>Pause</button>
          <button type="button" onClick={() => resumeMutation.mutate()} disabled={resumeMutation.isPending}>Resume</button>
          <button type="button" className="btn-danger" onClick={() => cancelMutation.mutate()} disabled={cancelMutation.isPending}>Cancel</button>
          <Link to={`/jobs/${jobId}/diff`} className="btn-secondary">Review Diff</Link>
        </div>
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
              <li key={check.name}>
                <strong>{check.name}</strong> — exit {check.exit_code}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <h2>Event Timeline</h2>
        <ul className="event-timeline">
          {events.map((e) => (
            <li key={e.id} className={`event-item event-item--${e.event_type}`}>
              <span className="event-seq">#{e.sequence}</span>
              <strong>{e.event_type}</strong>
              <pre>{e.payload_json}</pre>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
