// Convenient aliases over the auto-generated OpenAPI schemas (NFR-5 / AC-10).
// Regenerate the *.gen.ts files with `npm run gen:types` after API changes.
import type { components as Gov } from "./governance.gen";
import type { components as Orch } from "./orchestrator.gen";

type GovSchemas = Gov["schemas"];
type OrchSchemas = Orch["schemas"];

export type Agent = GovSchemas["AgentOut"];
export type AgentCreate = GovSchemas["AgentCreate"];
export type AgentUpdate = GovSchemas["AgentUpdate"];

export type Eval = GovSchemas["EvalOut"];
export type EvalCreate = GovSchemas["EvalCreate"];
export type EvalUpdate = GovSchemas["EvalUpdate"];

export type CalibrationSet = GovSchemas["CalibrationSetOut"];
export type CalibrationSetCreate = GovSchemas["CalibrationSetCreate"];

export type EvalAgentMapping = GovSchemas["EvalAgentMappingOut"];
export type EvalAgentMappingCreate = GovSchemas["EvalAgentMappingCreate"];

export type ChangeEvent = GovSchemas["ChangeEventOut"];
export type EvalResult = GovSchemas["EvalResultOut"];
export type EvalResultAggregate = GovSchemas["EvalResultAggregate"];
export type RegressionAlert = GovSchemas["RegressionAlertOut"];
export type AuditLogEntry = GovSchemas["AuditLogOut"];

export type RunEvalRequest = OrchSchemas["RunEvalRequest"];
export type RunEvalResponse = OrchSchemas["RunEvalResponse"];
export type EvalVerdict = OrchSchemas["EvalVerdict"];

export type ReviewStatus = "draft" | "in_review" | "approved" | "deprecated" | "expired";
export type Criticality = "low" | "medium" | "high" | "critical";
