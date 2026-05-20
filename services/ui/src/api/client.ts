import { GOVERNANCE_API_URL, ORCHESTRATOR_URL } from "@/lib/config";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(base: string, path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail: unknown;
    let message = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? body;
      if (typeof body?.detail === "string") message = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, message, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function withQuery(path: string, params?: Record<string, unknown>): string {
  if (!params) return path;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  }
  const s = qs.toString();
  return s ? `${path}?${s}` : path;
}

export const gov = {
  get: <T>(path: string, params?: Record<string, unknown>) =>
    request<T>(GOVERNANCE_API_URL, withQuery(path, params)),
  post: <T>(path: string, body?: unknown) =>
    request<T>(GOVERNANCE_API_URL, path, { method: "POST", body: JSON.stringify(body ?? {}) }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(GOVERNANCE_API_URL, path, { method: "PATCH", body: JSON.stringify(body ?? {}) }),
  del: <T>(path: string) => request<T>(GOVERNANCE_API_URL, path, { method: "DELETE" }),
};

export const orchestrator = {
  post: <T>(path: string, body?: unknown) =>
    request<T>(ORCHESTRATOR_URL, path, { method: "POST", body: JSON.stringify(body ?? {}) }),
};
