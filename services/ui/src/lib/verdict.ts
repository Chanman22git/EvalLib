// Consistent verdict + status color coding (FR-UI-2).
// green = compliant/correct, yellow = ambiguous/partial, red = non-compliant,
// gray = insufficient context / unknown.

export type VerdictTone = "pass" | "partial" | "fail" | "unknown";

const PASS = new Set([
  "compliant",
  "correct",
  "grounded",
  "pass",
  "passed",
  "helpful",
  "safe",
  "yes",
]);
const PARTIAL = new Set(["ambiguous", "partial", "uncertain", "maybe"]);
const FAIL = new Set([
  "non_compliant",
  "noncompliant",
  "incorrect",
  "hallucinated",
  "fail",
  "failed",
  "unsafe",
  "judge_error",
  "no",
]);

export function verdictTone(verdict: string | null | undefined): VerdictTone {
  if (!verdict) return "unknown";
  const v = verdict.toLowerCase();
  if (PASS.has(v)) return "pass";
  if (PARTIAL.has(v)) return "partial";
  if (FAIL.has(v)) return "fail";
  return "unknown";
}

export const TONE_CLASSES: Record<VerdictTone, string> = {
  pass: "bg-verdict-pass/15 text-verdict-pass border-verdict-pass/30",
  partial: "bg-verdict-partial/15 text-verdict-partial border-verdict-partial/40",
  fail: "bg-verdict-fail/15 text-verdict-fail border-verdict-fail/30",
  unknown: "bg-verdict-unknown/15 text-verdict-unknown border-verdict-unknown/30",
};

// Governance review-status badge tones.
export const REVIEW_STATUS_CLASSES: Record<string, string> = {
  draft: "bg-muted text-muted-foreground border-border",
  in_review: "bg-verdict-partial/15 text-verdict-partial border-verdict-partial/40",
  approved: "bg-verdict-pass/15 text-verdict-pass border-verdict-pass/30",
  deprecated: "bg-verdict-unknown/15 text-verdict-unknown border-verdict-unknown/30",
  expired: "bg-verdict-fail/15 text-verdict-fail border-verdict-fail/30",
};

export const CRITICALITY_CLASSES: Record<string, string> = {
  low: "bg-verdict-unknown/10 text-verdict-unknown border-verdict-unknown/30",
  medium: "bg-sky-100 text-sky-700 border-sky-200",
  high: "bg-verdict-partial/15 text-verdict-partial border-verdict-partial/40",
  critical: "bg-verdict-fail/15 text-verdict-fail border-verdict-fail/30",
};
