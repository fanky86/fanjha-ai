import { useEffect, useState } from "react";
import { apiGetSettings, apiUpdateSettings } from "../api";
import LoadingState from "../components/LoadingState";

export default function Settings() {
  const [settings, setSettings] = useState<Record<string, unknown> | null>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    apiGetSettings().then(setSettings).catch(() => {});
  }, []);

  const save = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      await apiUpdateSettings(settings);
      setMsg("Saved");
    } catch (e) {
      setMsg(`Error: ${e instanceof Error ? e.message : e}`);
    } finally {
      setSaving(false);
      setTimeout(() => setMsg(null), 3000);
    }
  };

  if (!settings) return <LoadingState />;

  const update = (k: string, v: unknown) =>
    setSettings((s) => ({ ...s!, [k]: v }));

  return (
    <div className="page">
      <h1>Settings</h1>
      <div className="card">
        <label className="field">
          <span>Model name</span>
          <input
            value={String(settings.default_model_name ?? "")}
            onChange={(e) => update("default_model_name", e.target.value)}
          />
        </label>
        <label className="field">
          <span>Max train steps</span>
          <input
            type="number"
            min={1}
            value={Number(settings.default_max_train_steps ?? 20)}
            onChange={(e) => update("default_max_train_steps", Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span>Batch size</span>
          <input
            type="number"
            min={1}
            value={Number(settings.default_batch_size ?? 2)}
            onChange={(e) => update("default_batch_size", Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span>Learning rate</span>
          <input
            type="number"
            step="0.00001"
            value={Number(settings.default_learning_rate ?? 0.00005)}
            onChange={(e) => update("default_learning_rate", Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span>Max sequence length</span>
          <input
            type="number"
            min={8}
            value={Number(settings.default_max_seq_length ?? 128)}
            onChange={(e) => update("default_max_seq_length", Number(e.target.value))}
          />
        </label>
        <div className="field">
          <button className="btn primary" onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save Settings"}
          </button>
          {msg && <span className="muted" style={{ marginLeft: 12 }}>{msg}</span>}
        </div>
        <p className="muted small">
          These defaults are used for new builds. The current build is not affected.
        </p>
      </div>
    </div>
  );
}
