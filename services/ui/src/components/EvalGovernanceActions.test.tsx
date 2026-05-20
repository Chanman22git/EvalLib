import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EvalGovernanceActions } from "./EvalGovernanceActions";
import type { Eval } from "@/api/types";

// The component fetches calibration sets on mount; stub fetch so tests are offline.
beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response("[]", { status: 200, headers: { "content-type": "application/json" } })),
  );
});

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

function makeEval(overrides: Partial<Eval>): Eval {
  return {
    id: "eval-1",
    eval_id: "refund_policy_compliance",
    version: "1.0.0",
    criterion_description: "",
    evaluator_type: "llm_as_judge",
    judge_config: {},
    prompt_template: null,
    output_schema: {},
    retrieval_config: null,
    calibration_set_id: null,
    last_judge_human_agreement: null,
    agreement_threshold: 0.75,
    execution_modes: {},
    owner_team: "t",
    owner_email: "o@example.com",
    approver_email: null,
    review_status: "draft",
    approved_at: null,
    expires_at: null,
    created_at: "2026-05-12T00:00:00Z",
    updated_at: "2026-05-12T00:00:00Z",
    ...overrides,
  } as Eval;
}

describe("EvalGovernanceActions", () => {
  it("offers 'Submit for review' in draft and the calibration attach control", () => {
    render(<EvalGovernanceActions ev={makeEval({ review_status: "draft" })} />, { wrapper });
    expect(screen.getByRole("button", { name: /submit for review/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run agreement test/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^approve$/i })).not.toBeInTheDocument();
  });

  it("offers 'Approve' while in review", () => {
    render(<EvalGovernanceActions ev={makeEval({ review_status: "in_review" })} />, { wrapper });
    expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /submit for review/i })).not.toBeInTheDocument();
  });

  it("offers 'Deprecate' once approved and hides the editable controls", () => {
    render(<EvalGovernanceActions ev={makeEval({ review_status: "approved" })} />, { wrapper });
    expect(screen.getByRole("button", { name: /deprecate/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /run agreement test/i })).not.toBeInTheDocument();
  });

  it("shows an immutability notice when deprecated", () => {
    render(<EvalGovernanceActions ev={makeEval({ review_status: "deprecated" })} />, { wrapper });
    expect(screen.getByText(/immutable/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /deprecate/i })).not.toBeInTheDocument();
  });
});
