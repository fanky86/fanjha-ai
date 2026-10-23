import { useEffect, useState } from "react";
import { useApp } from "../context/AppContext";
import { useWebSocket } from "../hooks/useWebSocket";
import { usePolling } from "../hooks/usePolling";
import { apiGetBuild, apiListBuilds } from "../api";
import StatusBadge from "../components/StatusBadge";
import ProgressBar from "../components/ProgressBar";
import EmptyState from "../components/EmptyState";
import LoadingState from "../components/LoadingState";
import StatCard from "../components/StatCard";
import type { Build, BuildSummary } from "../types";

const STAGES = [
  "PREPARING", "COLLECTING_DATA", "PREPROCESSING", "TOKENIZING",
  "TRAINING", "EVALUATING", "EXPORTING", "VERIFYING", "SUCCESS",
];

export default function Overview() {
  const { build, setBuild, loading } = useApp();
  const [history, setHistory] = useState<BuildSummary[]>([]);

  const loadHistory = async () => {
    const list = await apiListBuilds();
    setHistory(list);
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const { state } = useWebSocket(build?.id ?? null, (e) => {
    if (!build || e.build_id !== build.id) return;
    if (e.event === "status" && e.status) {
      setBuild({
        ...build,
        status: e.status,
        active_stage: e.stage ?? build.active_stage,
        overall_progress: e.overall_progress ?? build.overall_progress,
      });
    }
  });

  const polled = usePolling<Build | null>(
    async () => (build ? apiGetBuild(build.id) : null),
    3000,
    state !== "connected" && !!build
  );

  useEffect(() => {
    if (polled.data) setBuild(polled.data);
  }, [polled.data]);

  if (loading) return <LoadingState label="Loading build state" />;

  if (!build) {
    return (
      <EmptyState
        title="No build yet"
        message="Click START FULL BUILD in the top right to launch the automated pipeline."
      />
    );
  }

  const completedStages = computeCompletedStages(build);

  return (
    <div className="page">
      <h1>Overview</h1>

      <div className="grid">
        <div className="card">
          <h3>Pipeline</h3>
          <StatusBadge status={build.status} />
          <p className="muted">
            Active stage: <b>{build.active_stage ?? "—"}</b>
          </p>
          <ProgressBar value={build.overall_progress} />
          {build.error_summary && (
            <p className="error-box">{build.error_summary}</p>
          )}
          {build.is_resumed && <p className="muted">Resumed from checkpoint</p>}
        </div>

        <StatCard
          label="Started"
          value={build.started_at ? new Date(build.started_at).toLocaleString() : "N/A"}
        />
        <StatCard
          label="Duration"
          value={
            build.duration_seconds != null
              ? `${build.duration_seconds.toFixed(0)}s`
              : "N/A"
          }
        />
        <StatCard
          label="Epoch"
          value={build.current_epoch ?? "N/A"}
        />
        <StatCard
          label="Global Step"
          value={build.current_step ?? "N/A"}
        />
      </div>

      <h2>Stage Checklist</h2>
      <div className="card">
        {STAGES.map((s) => {
          const done = completedStages.includes(s);
          const active = build.active_stage === s;
          return (
            <div key={s} className={`check-row ${done ? "done" : ""} ${active ? "active" : ""}`}>
              <span>{s}</span>
              <span>{done ? "✓" : active ? "▶" : "—"}</span>
            </div>
          );
        })}
      </div>

      <h2>Recent Builds</h2>
      {history.length === 0 ? (
        <p className="muted">No builds yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Progress</th>
              <th>Started</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {history.slice(0, 10).map((b) => (
              <tr key={b.id}>
                <td className="mono">{b.id.slice(0, 8)}</td>
                <td><StatusBadge status={b.status} /></td>
                <td>{b.overall_progress.toFixed(0)}%</td>
                <td>{b.started_at ? new Date(b.started_at).toLocaleString() : "—"}</td>
                <td>{b.duration_seconds ? `${b.duration_seconds.toFixed(0)}s` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function computeCompletedStages(build: Build): string[] {
  if (build.status === "SUCCESS") return STAGES;
  if (build.status === "FAILED" || build.status === "CANCELLED") {
    const stage = build.active_stage ?? "";
    const idx = STAGES.indexOf(stage);
    return idx > 0 ? STAGES.slice(0, idx) : [];
  }
  const stage = build.active_stage ?? "";
  const idx = STAGES.indexOf(stage);
  return idx > 0 ? STAGES.slice(0, idx) : [];
}
