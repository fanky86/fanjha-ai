export default function StatCard({
  label, value, hint,
}: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="card stat">
      <span className="stat-label">{label}</span>
      <b className="stat-value">{value}</b>
      {hint && <span className="stat-hint">{hint}</span>}
    </div>
  );
}
