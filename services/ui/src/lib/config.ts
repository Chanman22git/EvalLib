// Browser-facing service URLs. Injected at build time via VITE_* env vars, with
// localhost defaults for `npm run dev` against a locally running stack.
export const GOVERNANCE_API_URL =
  import.meta.env.VITE_GOVERNANCE_API_URL ?? "http://localhost:8001";
export const ORCHESTRATOR_URL =
  import.meta.env.VITE_ORCHESTRATOR_URL ?? "http://localhost:8002";
export const PHOENIX_URL = import.meta.env.VITE_PHOENIX_URL ?? "http://localhost:6006";

/** Deep link into Phoenix's native trace UI for a given trace. */
export function phoenixTraceUrl(traceId: string): string {
  return `${PHOENIX_URL}/projects/default?selectedTraceId=${encodeURIComponent(traceId)}`;
}
