import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { gov, orchestrator } from "./client";
import type {
  Agent,
  AgentCreate,
  AuditLogEntry,
  CalibrationSet,
  CalibrationSetCreate,
  ChangeEvent,
  Eval,
  EvalAgentMapping,
  EvalAgentMappingCreate,
  EvalCreate,
  EvalResult,
  EvalResultAggregate,
  RegressionAlert,
  RunEvalRequest,
  RunEvalResponse,
} from "./types";

// ── Agents ────────────────────────────────────────────────────────────────
export const useAgents = (params?: Record<string, unknown>) =>
  useQuery({ queryKey: ["agents", params], queryFn: () => gov.get<Agent[]>("/agents", params) });

export const useAgent = (id?: string) =>
  useQuery({ queryKey: ["agent", id], queryFn: () => gov.get<Agent>(`/agents/${id}`), enabled: !!id });

export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AgentCreate) => gov.post<Agent>("/agents", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents"] }),
  });
}

// ── Evals ─────────────────────────────────────────────────────────────────
export const useEvals = (params?: Record<string, unknown>) =>
  useQuery({ queryKey: ["evals", params], queryFn: () => gov.get<Eval[]>("/evals", params) });

export const useEval = (id?: string) =>
  useQuery({ queryKey: ["eval", id], queryFn: () => gov.get<Eval>(`/evals/${id}`), enabled: !!id });

export function useCreateEval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EvalCreate) => gov.post<Eval>("/evals", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["evals"] }),
  });
}

type EvalAction = "submit-for-review" | "approve" | "deprecate";

export function useEvalAction(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ action, body }: { action: EvalAction; body?: Record<string, unknown> }) =>
      gov.post<Eval>(`/evals/${id}/${action}`, body ?? {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["eval", id] });
      qc.invalidateQueries({ queryKey: ["evals"] });
      qc.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

export function useAttachCalibration(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (calibration_set_id: string) =>
      gov.post<Eval>(`/evals/${id}/calibration`, { calibration_set_id }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["eval", id] });
      qc.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

// ── Calibration sets ────────────────────────────────────────────────────────
export const useCalibrationSets = () =>
  useQuery({ queryKey: ["calibration-sets"], queryFn: () => gov.get<CalibrationSet[]>("/calibration-sets") });

export function useCreateCalibrationSet() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CalibrationSetCreate) => gov.post<CalibrationSet>("/calibration-sets", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calibration-sets"] }),
  });
}

// ── Eval-agent mapping ──────────────────────────────────────────────────────
export const useEvalAgentMappings = (params?: Record<string, unknown>) =>
  useQuery({
    queryKey: ["eval-agent-mapping", params],
    queryFn: () => gov.get<EvalAgentMapping[]>("/eval-agent-mapping", params),
  });

export function useCreateMapping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EvalAgentMappingCreate) =>
      gov.post<EvalAgentMapping>("/eval-agent-mapping", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["eval-agent-mapping"] }),
  });
}

// ── Change events ───────────────────────────────────────────────────────────
export const useChangeEvents = (params?: Record<string, unknown>) =>
  useQuery({
    queryKey: ["change-events", params],
    queryFn: () => gov.get<ChangeEvent[]>("/change-events", params),
  });

// ── Eval results ────────────────────────────────────────────────────────────
export const useEvalResults = (params?: Record<string, unknown>) =>
  useQuery({
    queryKey: ["eval-results", params],
    queryFn: () => gov.get<EvalResult[]>("/eval-results", params),
  });

export const useEvalResultsAggregate = (params?: Record<string, unknown>) =>
  useQuery({
    queryKey: ["eval-results-aggregate", params],
    queryFn: () => gov.get<EvalResultAggregate[]>("/eval-results/aggregate", params),
  });

// ── Regression alerts ───────────────────────────────────────────────────────
export const useRegressionAlerts = (params?: Record<string, unknown>) =>
  useQuery({
    queryKey: ["regression-alerts", params],
    queryFn: () => gov.get<RegressionAlert[]>("/regression-alerts", params),
  });

export const useRegressionAlert = (id?: string) =>
  useQuery({
    queryKey: ["regression-alert", id],
    queryFn: () => gov.get<RegressionAlert>(`/regression-alerts/${id}`),
    enabled: !!id,
  });

export function useUpdateRegressionStatus(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (status: string) => gov.patch<RegressionAlert>(`/regression-alerts/${id}`, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["regression-alert", id] });
      qc.invalidateQueries({ queryKey: ["regression-alerts"] });
    },
  });
}

// ── Audit log ───────────────────────────────────────────────────────────────
export const useAuditLog = (params?: Record<string, unknown>) =>
  useQuery({
    queryKey: ["audit-log", params],
    queryFn: () => gov.get<AuditLogEntry[]>("/audit-log", params),
  });

// ── Orchestrator ────────────────────────────────────────────────────────────
export function useRunEval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RunEvalRequest) => orchestrator.post<RunEvalResponse>("/run-eval", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["eval-results"] }),
  });
}
