import { useEffect, useState } from "react";
import { apiListDatasets, apiPreviewDataset } from "../api";
import type { DatasetInfo } from "../types";
import LoadingState from "../components/LoadingState";
import EmptyState from "../components/EmptyState";

export default function DatasetExplorer() {
  const [datasets, setDatasets] = useState<DatasetInfo[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [preview, setPreview] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiListDatasets()
      .then(setDatasets)
      .catch((e) => setError(String(e)));
  }, []);

  const loadPreview = async (path: string) => {
    setSelected(path);
    setPreview(null);
    try {
      const r = await apiPreviewDataset(path);
      setPreview(r.preview);
    } catch (e) {
      setPreview([`Error: ${e instanceof Error ? e.message : e}`]);
    }
  };

  if (error) return <div className="page"><h1>Datasets</h1><p className="error-box">{error}</p></div>;
  if (!datasets) return <LoadingState />;
  if (datasets.length === 0) {
    return <EmptyState title="No datasets" message="Add .jsonl, .txt, .json, or .csv files to data/" />;
  }

  return (
    <div className="page">
      <h1>Dataset Explorer</h1>
      <table>
        <thead>
          <tr>
            <th>Path</th>
            <th>Size</th>
            <th>Documents</th>
            <th>Est. Tokens</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {datasets.map((d) => (
            <tr key={d.path}>
              <td className="mono">{d.path}</td>
              <td>{(d.size_bytes / 1024).toFixed(1)} KB</td>
              <td>{d.documents ?? "N/A"}</td>
              <td>{d.estimated_tokens ?? "N/A"}</td>
              <td>
                <button className="btn" onClick={() => loadPreview(d.path)}>Preview</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {selected && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Preview: {selected}</h3>
          {preview === null ? (
            <LoadingState label="Loading preview" />
          ) : (
            <pre className="mono" style={{ whiteSpace: "pre-wrap" }}>
              {preview.join("\n\n")}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
