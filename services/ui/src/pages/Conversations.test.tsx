import { describe, expect, it } from "vitest";

import type { EvalResult } from "@/api/types";
import { groupConversations, isSessionRow } from "@/pages/Conversations";

function result(partial: Partial<EvalResult>): EvalResult {
  return {
    id: crypto.randomUUID(),
    trace_id: "t",
    span_id: null,
    session_id: null,
    eval_id: "e",
    eval_version: "1.0.0",
    verdict: "compliant",
    score: 1,
    reasoning: null,
    judge_model: null,
    evaluated_at: "2026-06-16T00:00:00Z",
    agent_id: null,
    ...partial,
  };
}

describe("isSessionRow", () => {
  it("treats trace_id === session_id as the session-scoped row", () => {
    expect(isSessionRow(result({ trace_id: "s1", session_id: "s1" }))).toBe(true);
    expect(isSessionRow(result({ trace_id: "t1", session_id: "s1" }))).toBe(false);
  });
});

describe("groupConversations", () => {
  it("groups by session, counts distinct turns, and collects session verdicts", () => {
    const rows: EvalResult[] = [
      // session s1: two turns (t1, t2), one session-scoped verdict (trace_id = s1)
      result({ session_id: "s1", trace_id: "t1", agent_id: "a1", evaluated_at: "2026-06-16T00:01:00Z" }),
      result({ session_id: "s1", trace_id: "t2", agent_id: "a1", evaluated_at: "2026-06-16T00:02:00Z" }),
      result({ session_id: "s1", trace_id: "s1", eval_id: "multi_turn_coherence", evaluated_at: "2026-06-16T00:03:00Z" }),
      // a legacy row with no session_id is ignored
      result({ session_id: null, trace_id: "t9" }),
      // session s0: older, single turn
      result({ session_id: "s0", trace_id: "t0", evaluated_at: "2026-06-15T00:00:00Z" }),
    ];

    const convos = groupConversations(rows);

    expect(convos.map((c) => c.sessionId)).toEqual(["s1", "s0"]); // newest first
    const s1 = convos[0];
    expect(s1.turnCount).toBe(2);
    expect(s1.agentId).toBe("a1");
    expect(s1.sessionVerdicts.map((v) => v.eval_id)).toEqual(["multi_turn_coherence"]);
    expect(s1.lastAt).toBe("2026-06-16T00:03:00Z");
  });
});
