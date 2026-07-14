import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { projectsApi } from "@/api/client";
import type { Project } from "@/api/types";

type WizardStep = "form" | "registering" | "result";

function PreflightSummary({ project }: { project: Project }) {
  const preflight = project.preflight;
  if (!preflight) return null;

  return (
    <div className="card">
      <h2>Preflight Results</h2>
      <div className="data-grid">
        <div className="data-item">
          <label>Status</label>
          <span className={`status-badge status-badge--${preflight.status}`}>
            {preflight.status}
          </span>
        </div>
        <div className="data-item">
          <label>Git</label>
          <span>{preflight.git.is_git_repo ? "Yes" : "No"}</span>
        </div>
        <div className="data-item">
          <label>Branch</label>
          <span>{preflight.git.branch ?? "—"}</span>
        </div>
        <div className="data-item">
          <label>Revision</label>
          <span>{preflight.git.revision ?? "—"}</span>
        </div>
        <div className="data-item">
          <label>Files</label>
          <span>{preflight.inventory.file_count}</span>
        </div>
        <div className="data-item">
          <label>Manifests</label>
          <span>
            {preflight.inventory.manifest_files.length > 0
              ? preflight.inventory.manifest_files.join(", ")
              : "none detected"}
          </span>
        </div>
      </div>
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
  );
}

export function AddProjectPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<WizardStep>("form");
  const [name, setName] = useState("");
  const [sourcePath, setSourcePath] = useState("");
  const [tags, setTags] = useState("");
  const [result, setResult] = useState<Project | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const registerMutation = useMutation({
    mutationFn: () =>
      projectsApi.register({
        name,
        source_path: sourcePath,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        require_git: true,
      }),
    onMutate: () => {
      setStep("registering");
      setErrorMsg(null);
    },
    onSuccess: (project) => {
      setResult(project);
      setStep("result");
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (err: unknown) => {
      setStep("form");
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Registration failed");
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    registerMutation.mutate();
  };

  return (
    <>
      <header className="page-header">
        <h1>Add Project</h1>
        <p>Register a local Git repository for FADE management</p>
      </header>

      {step === "form" && (
        <form className="card wizard-form" onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="name">Project name</label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Project"
              required
            />
          </div>
          <div className="form-field">
            <label htmlFor="path">Source path</label>
            <input
              id="path"
              type="text"
              value={sourcePath}
              onChange={(e) => setSourcePath(e.target.value)}
              placeholder="/home/user/projects/my-app"
              required
            />
            <span className="form-hint">Absolute path to a local Git repository</span>
          </div>
          <div className="form-field">
            <label htmlFor="tags">Tags (optional)</label>
            <input
              id="tags"
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="python, web"
            />
          </div>
          {errorMsg && <div className="error-state">{errorMsg}</div>}
          <button type="submit" className="btn-primary" disabled={!name || !sourcePath}>
            Register &amp; Run Preflight
          </button>
        </form>
      )}

      {step === "registering" && (
        <div className="loading card">
          <p>Running preflight checks…</p>
          <p className="form-hint">Scanning files, Git metadata, and manifests</p>
        </div>
      )}

      {step === "result" && result && (
        <>
          <div className="card">
            <h2>Project Registered</h2>
            <p>
              <strong>{result.name}</strong> is now{" "}
              <span className={`status-badge status-badge--${result.status}`}>
                {result.status}
              </span>
            </p>
          </div>
          <PreflightSummary project={result} />
          <div className="wizard-actions">
            <button type="button" className="btn-secondary" onClick={() => navigate("/")}>
              Back to Portfolio
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => navigate(`/projects/${result.id}`)}
            >
              View Project
            </button>
          </div>
        </>
      )}
    </>
  );
}
