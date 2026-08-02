import { useQuery } from "@tanstack/react-query";
import { systemApi } from "@/api/client";
import type { DoctorResponse, HealthResponse } from "@/api/types";

function StatusBadge({ status }: { status: string }) {
  const className = `status-badge status-badge--${status}`;
  return <span className={className}>{status}</span>;
}

function HealthCard({ data }: { data: HealthResponse }) {
  return (
    <div className="card">
      <h2>Health</h2>
      <div className="data-grid">
        <div className="data-item">
          <label>Status</label>
          <span><StatusBadge status={data.status} /></span>
        </div>
        <div className="data-item">
          <label>Version</label>
          <span>{data.version}</span>
        </div>
        <div className="data-item">
          <label>Environment</label>
          <span>{data.environment}</span>
        </div>
        <div className="data-item">
          <label>Database</label>
          <span>{data.database.connected ? "Connected" : "Disconnected"}</span>
        </div>
        <div className="data-item">
          <label>WAL Mode</label>
          <span>{data.database.wal_mode === null ? "—" : data.database.wal_mode ? "Yes" : "No"}</span>
        </div>
        <div className="data-item">
          <label>Projects</label>
          <span>{data.database.project_count ?? 0}</span>
        </div>
      </div>
    </div>
  );
}

function CapabilitiesCard({ capabilities }: { capabilities: Record<string, boolean> }) {
  return (
    <div className="card">
      <h2>Capabilities</h2>
      <ul className="capability-list">
        {Object.entries(capabilities).map(([name, available]) => (
          <li key={name}>
            <span className={`dot ${available ? "dot--available" : "dot--planned"}`} />
            {name.replace(/_/g, " ")}
            {!available && " (planned)"}
          </li>
        ))}
      </ul>
    </div>
  );
}

function DoctorCard({ data }: { data: DoctorResponse }) {
  return (
    <div className="card">
      <h2>Doctor Diagnostics</h2>
      <div className="data-item" style={{ marginBottom: "1rem" }}>
        <label>Overall</label>
        <span><StatusBadge status={data.status} /></span>
      </div>
      {data.issues.length === 0 ? (
        <p className="empty-state">No issues detected.</p>
      ) : (
        <ul className="issue-list">
          {data.issues.map((issue) => (
            <li key={issue.code} className={`severity-${issue.severity}`}>
              <strong>{issue.code}</strong>: {issue.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function SystemStatusPage() {
  const healthQuery = useQuery({
    queryKey: ["system", "health"],
    queryFn: systemApi.health,
    retry: 1,
  });

  const doctorQuery = useQuery({
    queryKey: ["system", "doctor"],
    queryFn: systemApi.doctor,
    retry: 1,
  });

  const isLoading =
    (healthQuery.isLoading || doctorQuery.isLoading) &&
    !healthQuery.isError &&
    !doctorQuery.isError;
  const hasError = healthQuery.isError || doctorQuery.isError;

  return (
    <>
      <header className="page-header">
        <h1>System Status</h1>
        <p>FADE platform health and diagnostics (Milestone 0)</p>
      </header>

      {isLoading && <div className="loading">Loading system status…</div>}

      {hasError && !isLoading && (
        <div className="error-state">
          Failed to load system status. Ensure the API is running on port 8000.
          {healthQuery.error && (
            <p>{healthQuery.error instanceof Error ? healthQuery.error.message : "Unknown error"}</p>
          )}
        </div>
      )}

      {!isLoading && !hasError && healthQuery.data && (
        <>
          <HealthCard data={healthQuery.data} />
          <CapabilitiesCard capabilities={healthQuery.data.capabilities} />
        </>
      )}

      {!isLoading && !hasError && doctorQuery.data && (
        <DoctorCard data={doctorQuery.data} />
      )}

      {!isLoading && !hasError && doctorQuery.data?.model_providers?.length ? (
        <div className="card">
          <h2>Model Providers</h2>
          <ul className="capability-list">
            {doctorQuery.data.model_providers.map((provider) => (
              <li key={`${provider.provider_id}-${provider.model_id}`}>
                <span
                  className={`dot ${provider.available ? "dot--available" : "dot--planned"}`}
                />
                {provider.provider_id} / {provider.model_id}
                {!provider.available && provider.reason ? ` — ${provider.reason}` : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  );
}
