import { useEffect, useState } from "react";
import { apiGetResources } from "../api";
import type { SystemResources } from "../types";
import LoadingState from "../components/LoadingState";
import ProgressBar from "../components/ProgressBar";
import StatCard from "../components/StatCard";

const GB = 1e9;

export default function HardwareMonitor() {
  const [res, setRes] = useState<SystemResources | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await apiGetResources();
        if (!cancelled) {
          setRes(data);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    };
    load();
    const id = setInterval(load, 3000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (error) return <div className="page"><h1>Hardware</h1><p className="error-box">{error}</p></div>;
  if (!res) return <LoadingState />;

  const ramPct = (res.ram_used / res.ram_total) * 100;
  const diskPct = (res.disk_used / res.disk_total) * 100;

  return (
    <div className="page">
      <h1>Hardware Monitor</h1>
      <div className="grid">
        <div className="card">
          <h3>CPU</h3>
          <ProgressBar value={res.cpu_percent} label={`${res.cpu_percent.toFixed(1)}% (${res.cpu_count} cores)`} />
        </div>
        <div className="card">
          <h3>RAM</h3>
          <ProgressBar value={ramPct} label={`${(res.ram_used / GB).toFixed(1)} / ${(res.ram_total / GB).toFixed(1)} GB`} />
          <p className="muted">Available: {(res.ram_available / GB).toFixed(1)} GB</p>
        </div>
        <div className="card">
          <h3>Disk</h3>
          <ProgressBar value={diskPct} label={`${(res.disk_used / GB).toFixed(1)} / ${(res.disk_total / GB).toFixed(1)} GB`} />
          <p className="muted">Free: {(res.disk_free / GB).toFixed(1)} GB</p>
        </div>
        <StatCard
          label="Process RAM"
          value={res.process_ram_used != null ? `${(res.process_ram_used / 1e6).toFixed(1)} MB` : "Unavailable"}
        />
        <div className="card">
          <h3>GPU</h3>
          <pre className="mono">
            {typeof res.gpu === "string" ? res.gpu : JSON.stringify(res.gpu, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
