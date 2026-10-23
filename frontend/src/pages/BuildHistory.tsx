import { useEffect, useState } from "react";
import {
  apiListBuilds, apiResumeBuild, apiCancelBuild, apiRetryBuild,
} from "../api";
import type { BuildSummary } from "../types";
import StatusBadge from "../components/StatusBadge";
import EmptyState from "../components/EmptyState";
import LoadingState from "../components/LoadingState";

export default function BuildHistory() {
  const [builds, setBuilds] = useState<BuildSummary[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = () => apiListBuilds().then(setBuilds).catch(() => setBuilds([]));
  useEffect(() => { load(); }, []);

  const action = async (id: string, kind: "resume" | "cancel" | "retry") => {
    setBusy(id);
    try {
      if (kind === "resume") await apiResumeBuild(id);
      if (kind === "cancel") await apiCancelBuild(id);
      if (kind === "retry") await apiRetryBuild(id);
      await load();
    } catch (e) {
      alert(`Action failed: ${e instanceof Error ? e.message : e}`);
    } finally {
      setBusy(null);
    }
  };

  if (!builds) return <LoadingState />;
  if (builds.length === 0) return <EmptyState title="No builds" message="Start your first build." />;

  return (
    <div className="page">
      <h1>Build History</h1>
      <table>
        <thead>
          <tr>
            <th>Build ID</th>
            <th>Status</th>
            <th>Progress</th>
            <th>Started</th>
            <th>Duration</th>
            <th>Error</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {builds.map((b) => (
            <tr key={b.id}>
              <td className="mono">{b.id.slice(0, 8)}</td>
              <td><StatusBadge status={b.status} /></td>
              <td>{b.overall_progress.toFixed(0)}%</td>
              <td>{b.started_at ? new Date(b.started_at).toLocaleString() : "—"}</td>
              <td>{b.duration_seconds ? `${b.duration_seconds.toFixed(0)}s` : "—"}</td>
              <td className="error-cell" title={b.error_summary ?? ""}>
                {b.error_summary ? b.error_summary.slice(0, 30) + "…" : "—"}
              </td>
              <td className="actions">
                {["FAILED", "CANCELLED", "WARNING"].includes(b.status) && (
                  <button
                    className="btn small"
                    disabled={busy === b.id}
                    onClick={() => action(b.id, "resume")}
                  >
                    Resume
                  </button>
                )}
                {["PREPARING", "TRAINING", "EVALUATING", "EXPORTING", "VERIFYING"].includes(b.status) && (
                  <button
                    className="btn small"
                    disabled={busy === b.id}
                    onClick={() => action(b.id, "cancel")}
                  >
                    Cancel
                  </button>
                )}
                {["FAILED", "CANCELLED"].includes(b.status) && (
                  <button
                    className="btn small"
                    disabled={busy === b.id}
                    onClick={() => action(b.id, "retry")}
                  >
                    Retry
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
