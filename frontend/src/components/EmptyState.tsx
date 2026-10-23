export default function EmptyState({
  title, message, action,
}: { title: string; message: string; action?: React.ReactNode }) {
  return (
    <div className="empty">
      <h2>{title}</h2>
      <p>{message}</p>
      {action}
    </div>
  );
}
