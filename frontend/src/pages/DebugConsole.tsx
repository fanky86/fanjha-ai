import { useEffect, useRef, useState, useCallback } from "react";
import { useApp } from "../context/AppContext";
import { useWebSocket } from "../hooks/useWebSocket";
import { apiGetLogs } from "../api";
import type { LogEntry } from "../types";
import EmptyState from "../components/EmptyState";

const SEVERITIES = ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] as const;
type Sev = typeof SEVERITIES[number];

export default function DebugConsole() {
  const { build } = useApp();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [severity, setSeverity] = useState<Sev>("ALL");
  const [search, setSearch] = useState("");
  const [paused, setPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const pausedRef = useRef(paused);
  pausedRef.current = paused;

  useEffect(() => {
    if (!build) return;
    setLoading(true);
    apiGetLogs(build.id, 0, 1000)
      .then((r) => setLogs(r.logs))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [build?.id]);

  useWebSocket(build?.id ?? null, (e) => {
    if (e.event === "log" && !pausedRef.current) {
      setLogs((prev) => [
        ...prev,
        {
          id: -Date.now(),
          timestamp: e.timestamp ?? new Date().toISOString(),
          severity: e.severity,
          component: e.component,
          message: e.message,
          stack_trace: e.stack_trace,
        } as LogEntry,
      ]);
    }
  });

  useEffect(() => {
    if (autoScroll) bottomRef.current?.scrollIntoView({ behavior: "auto" });
  }, [logs, autoScroll]);

  const filtered = logs.filter((l) => {
    if (severity !== "ALL" && l.severity !== severity) return false;
    if (search) {
      const s = search.toLowerCase();
      return (
        l.message.toLowerCase().includes(s) ||
        l.component.toLowerCase().includes(s)
      );
    }
    return true;
  });

  const download = useCallback(() => {
    const text = filtered
      .map((l) => `[${l.timestamp}] [${l.severity}] [${l.component}] ${l.message}`)
      .join("\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `fanjha-logs-${build?.id.slice(0, 8) ?? "unknown"}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [filtered, build?.id]);

  if (!build) return <EmptyState title="No build" message="Start a build to see logs." />;

  return (
    <div className="page">
      <h1>Debug Console</h1>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Search logs…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={severity} onChange={(e) => setSeverity(e.target.value as Sev)}>
          {SEVERITIES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <button className="btn" onClick={() => setPaused((p) => !p)}>
          {paused ? "Resume" : "Pause"}
        </button>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
          /> Auto-scroll
        </label>
        <button className="btn" onClick={download}>Download</button>
        <button className="btn" onClick={() => setLogs([])}>Clear view</button>
      </div>
      <div className="console">
        {loading && <p className="muted">Loading logs…</p>}
        {filtered.length === 0 && !loading && (
          <p className="muted">No logs match the current filter.</p>
        )}
        {filtered.map((l, i) => (
          <div key={`${l.id}-${i}`} className={`log-line ${l.severity.toLowerCase()}`}>
            <span className="ts">
              {new Date(l.timestamp).toLocaleTimeString()}
            </span>
            <span className="sev">[{l.severity}]</span>
            <span className="comp">[{l.component}]</span>
            <span className="msg">{l.message}</span>
            {l.stack_trace && <pre className="stack">{l.stack_trace}</pre>}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
