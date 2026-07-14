import { useQuery } from "@tanstack/react-query";
import { policiesApi } from "@/api/client";

export function PoliciesPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["policies"],
    queryFn: () => policiesApi.list(),
  });

  if (isLoading) return <div className="loading">Loading policies…</div>;
  if (isError || !data) return <div className="error-state">Failed to load policies.</div>;

  return (
    <>
      <header className="page-header">
        <h1>Guardian Policies</h1>
        <p className="text-muted">{data.total} effective rules configured</p>
      </header>

      <div className="card">
        <table className="policy-table">
          <thead>
            <tr>
              <th>Rule</th>
              <th>Scope</th>
              <th>Effect</th>
              <th>Enabled</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((policy) => (
              <tr key={policy.id}>
                <td><code>{policy.rule_type}</code></td>
                <td>{policy.scope_type}{policy.scope_id ? `:${policy.scope_id}` : ""}</td>
                <td>
                  <span className={`status-badge status-badge--${policy.effect}`}>
                    {policy.effect}
                  </span>
                </td>
                <td>{policy.enabled ? "yes" : "no"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
