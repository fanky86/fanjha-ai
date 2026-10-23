const BASE = (import.meta as any).env?.VITE_API_BASE ?? "";

let csrfToken: string | null = null;

async function ensureCsrf(): Promise<string> {
  if (csrfToken) return csrfToken;
  const res = await fetch(`${BASE}/api/system/csrf`);
  if (!res.ok) throw new Error("Failed to fetch CSRF token");
  const data = await res.json();
  csrfToken = data.token;
  return csrfToken as string;
}

export async function api<T>(path: string, init?: RequestInit & { csrf?: boolean }): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (init?.csrf) {
    headers["X-CSRF-Token"] = await ensureCsrf();
  }
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string>) },
  });
  if (!res.ok) {
    let msg = `${res.status}`;
    try {
      const body = await res.json();
      msg = body.detail ?? msg;
    } catch {
      msg = await res.text().catch(() => msg);
    }
    throw new Error(msg);
  }
  return res.json();
}

export const apiListBuilds = () => api<import("./types").BuildSummary[]>("/api/builds");
export const apiGetBuild = (id: string) => api<import("./types").Build>(`/api/builds/${id}`);

export const apiCreateBuild = () =>
  api<{ build_id: string }>("/api/builds", {
    method: "POST",
    body: JSON.stringify({}),
    csrf: true,
  });

export const apiStartBuild = (id: string) =>
  api(`/api/builds/${id}/start`, { method: "POST", csrf: true });
export const apiCancelBuild = (id: string) =>
  api(`/api/builds/${id}/cancel`, { method: "POST", csrf: true });
export const apiResumeBuild = (id: string) =>
  api(`/api/builds/${id}/resume`, { method: "POST", csrf: true });
export const apiRetryBuild = (id: string) =>
  api(`/api/builds/${id}/retry`, { method: "POST", csrf: true });

export const apiGetLogs = (id: string, cursor = 0, limit = 500, severity?: string, search?: string) => {
  const params = new URLSearchParams({ cursor: String(cursor), limit: String(limit) });
  if (severity) params.set("severity", severity);
  if (search) params.set("search", search);
  return api<{ logs: import("./types").LogEntry[]; next_cursor: number; total: number }>(
    `/api/builds/${id}/logs?${params.toString()}`
  );
};

export const apiGetMetrics = (id: string) =>
  api<import("./types").Metric[]>(`/api/builds/${id}/metrics`);
export const apiGetArtifacts = (id: string) =>
  api<import("./types").Artifact[]>(`/api/builds/${id}/artifacts`);

export const apiGetResources = () => api<import("./types").SystemResources>("/api/system/resources");
export const apiHealth = () => api<{ status: string }>("/api/system/health");
export const apiListDatasets = () => api<import("./types").DatasetInfo[]>("/api/datasets");
export const apiPreviewDataset = (path: string) =>
  api<{ path: string; preview: string[] }>(`/api/datasets/preview?path=${encodeURIComponent(path)}`);

export const apiGetSettings = () => api<Record<string, unknown>>("/api/system/settings");
export const apiUpdateSettings = (payload: Record<string, unknown>) =>
  api("/api/system/settings", { method: "POST", body: JSON.stringify(payload), csrf: true });
