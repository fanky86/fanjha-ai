import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Legend,
} from "recharts";
import { useApp } from "../context/AppContext";
import { useWebSocket } from "../hooks/useWebSocket";
import { usePolling } from "../hooks/usePolling";
import { apiGetMetrics } from "../api";
import StatCard from "../components/StatCard";
import EmptyState from "../components/EmptyState";
import type { Metric } from "../types";

export default function LiveTraining() {
  const { build } = useApp();
  const [metrics, setMetrics] = useState<Metric[]>([]);

  useEffect(() => {
    if (!build) return;
    apiGetMetrics(build.id).then(setMetrics).catch(() => {});
  }, [build?.id]);

  const { state } = useWebSocket(build?.id ?? null, (e) => {
    if (e.event === "metric" && build && e.build_id === build.id) {
      setMetrics((prev) => [...prev, e as Metric]);
    }
  });

  const polled = usePolling<Metric[]>(
    async () => (build ? apiGetMetrics(build.id) : []),
    3000,
    state !== "connected" && !!build
  );

  useEffect(() => {
    if (polled.data) setMetrics(polled.data);
  }, [polled.data]);

  if (!build) return <EmptyState title="No build" message="Start a build to see training metrics." />;

  const last = metrics[metrics.length - 1] ?? {};
  const chartData = metrics
    .filter((m) => m.train_loss != null || m.val_loss != null)
    .map((m) => ({
      step: m.global_step ?? 0,
      train: m.train_loss ?? null,
      val: m.val_loss ?? null,
    }));

  return (
    <div className="page">
      <h1>Live Training</h1>
      <div className="grid">
        <StatCard label="Epoch" value={last.epoch ?? "N/A"} />
        <StatCard label="Global Step" value={last.global_step ?? "N/A"} />
        <StatCard
          label="Train Loss"
          value={fmtNum(last.train_loss, 4)}
        />
        <StatCard
          label="Val Loss"
          value={fmtNum(last.val_loss, 4)}
        />
        <StatCard
          label="Perplexity"
          value={fmtNum(last.perplexity, 2)}
        />
        <StatCard
          label="Learning Rate"
          value={fmtNum(last.learning_rate, 8)}
        />
        <StatCard
          label="Tokens/sec"
          value={fmtNum(last.throughput_tokens_per_sec, 0)}
        />
      </div>

      <div className="card chart-card">
        <h3>Loss Curve</h3>
        {chartData.length === 0 ? (
          <p className="muted">No metric data yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={340}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="step" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip
                contentStyle={{
                  background: "#1e293b",
                  border: "1px solid #334155",
                  color: "#e2e8f0",
                }}
              />
              <Legend />
              <Line type="monotone" dataKey="train" stroke="#10b981" dot={false} name="Train Loss" />
              <Line type="monotone" dataKey="val" stroke="#f59e0b" dot={false} name="Val Loss" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

function fmtNum(v: number | null | undefined, digits: number): string {
  if (v === null || v === undefined) return "N/A";
  return Number(v).toFixed(digits);
}
