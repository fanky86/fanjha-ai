import type { BuildStatus } from "../types";

const COLORS: Record<BuildStatus, string> = {
  IDLE: "#64748b",
  PREPARING: "#f59e0b",
  COLLECTING_DATA: "#3b82f6",
  PREPROCESSING: "#3b82f6",
  TOKENIZING: "#8b5cf6",
  TRAINING: "#10b981",
  EVALUATING: "#06b6d4",
  EXPORTING: "#f97316",
  VERIFYING: "#eab308",
  SUCCESS: "#22c55e",
  WARNING: "#f59e0b",
  FAILED: "#ef4444",
  CANCELLED: "#6b7280",
};

export default function StatusBadge({ status }: { status: BuildStatus }) {
  return (
    <span
      className="status-badge"
      style={{ background: COLORS[status] ?? "#64748b" }}
    >
      {status}
    </span>
  );
}
