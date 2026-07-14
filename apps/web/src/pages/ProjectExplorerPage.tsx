import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { projectsApi } from "@/api/client";
import type { ExplorerNode } from "@/api/types";

function ExplorerTree({ node, depth = 0 }: { node: ExplorerNode; depth?: number }) {
  const [open, setOpen] = useState(depth < 2);

  if (node.is_dir) {
    return (
      <div className="explorer-node" style={{ paddingLeft: depth * 12 }}>
        <button type="button" className="explorer-toggle" onClick={() => setOpen(!open)}>
          {open ? "▾" : "▸"} {node.path}
        </button>
        {open && node.children.map((child) => (
          <ExplorerTree key={child.path} node={child} depth={depth + 1} />
        ))}
      </div>
    );
  }

  return (
    <div className="explorer-file" style={{ paddingLeft: depth * 12 }}>
      <span className="explorer-file-name">{node.path}</span>
      {node.symbols.length > 0 && (
        <ul className="symbol-list">
          {node.symbols.map((s) => (
            <li key={`${s.name}-${s.line}`}>
              <code>{s.kind}</code> {s.name} <span className="text-muted">L{s.line}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ProjectExplorerPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [query, setQuery] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["projects", projectId, "explorer", query],
    queryFn: () => projectsApi.explorer(projectId!, query || undefined),
    enabled: !!projectId,
  });

  if (isLoading) return <div className="loading">Loading explorer…</div>;
  if (isError || !data) return <div className="error-state">Failed to load explorer.</div>;

  return (
    <>
      <header className="page-header">
        <Link to={`/projects/${projectId}`}>← Overview</Link>
        <h1>Project Explorer</h1>
        <nav className="sub-nav">
          <Link to={`/projects/${projectId}`}>Overview</Link>
          <Link to={`/projects/${projectId}/explorer`} className="active">Explorer</Link>
          <Link to={`/projects/${projectId}/goals`}>Goals & Plan</Link>
        </nav>
      </header>

      <div className="card">
        <input
          type="search"
          placeholder="Filter symbols…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="search-input"
        />
        <ExplorerTree node={data.root} />
      </div>
    </>
  );
}
