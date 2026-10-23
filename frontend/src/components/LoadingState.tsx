export default function LoadingState({ label }: { label?: string }) {
  return (
    <div className="loading">
      <div className="spinner" />
      <span>{label ?? "Loading…"}</span>
    </div>
  );
}
