import { useEffect, useState } from "react";
import { useApp } from "../context/AppContext";
import { apiGetArtifacts } from "../api";
import type { Artifact } from "../types";
import EmptyState from "../components/EmptyState";
import LoadingState from "../components/LoadingState";

export default function Artifacts() {
  const { build } = useApp();
  const [artifacts, setArtifacts] = useState<Artifact[] | null>(null);

  useEffect(() => {
    if (!build) return;
    apiGetArtifacts(build.id).then(setArtifacts).catch(() => setArtifacts([]));
  }, [build?.id]);

  if (!build) return <EmptyState title="No build" message="Start a build to generate artifacts." />;
  if (!artifacts) return <LoadingState />;
  if (artifacts.length === 0) {
    return <EmptyState title="No artifacts yet" message="Artifacts appear here once a build completes." />;
  }

  return (
    <div className="page">
      <h1>Artifacts</h1>
      <div className="grid">
        {artifacts.map((a) => (
          <div key={a.id} className="card">
            <h3>{a.name}</h3>
            <p className="muted">{(a.size_bytes / 1024 / 1024).toFixed(2)} MB</p>
            <p className="mono small">SHA256: {a.sha256.slice(0, 16)}…</p>
            <p className="muted">Verified: {a.verified ? "✓" : "✗"}</p>
            <p className="muted">
              Created: {new Date(a.created_at).toLocaleString()}
            </p>
            <a className="btn primary" href={`/api/artifacts/${a.id}/download`}>
              Download
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
