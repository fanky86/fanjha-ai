export default function Toast({
  message, kind = "info", onClose,
}: { message: string; kind?: "info" | "success" | "error"; onClose: () => void }) {
  return (
    <div className={`toast toast-${kind}`} onClick={onClose}>
      {message}
    </div>
  );
}
