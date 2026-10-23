export default function ProgressBar({
  value, label,
}: { value: number; label?: string }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="progress-wrap">
      <div className="progress">
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="progress-label">{label ?? `${pct.toFixed(1)}%`}</span>
    </div>
  );
}
