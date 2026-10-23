import type { WSState } from "../hooks/useWebSocket";

const LABELS: Record<WSState, string> = {
  connecting: "Connecting…",
  connected: "Live",
  reconnecting: "Reconnecting…",
  disconnected: "Offline",
};

const COLORS: Record<WSState, string> = {
  connecting: "#f59e0b",
  connected: "#22c55e",
  reconnecting: "#f59e0b",
  disconnected: "#ef4444",
};

export default function ConnectionStatus({ state }: { state: WSState }) {
  return (
    <div className="connection">
      <span className="dot" style={{ background: COLORS[state] }} />
      {LABELS[state]}
    </div>
  );
}
