import { MessagesSquare } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { LocalTime } from "@/components/LocalTime";
import { PageHeader } from "@/components/PageHeader";
import { VerdictBadge } from "@/components/VerdictBadge";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAgents, useEvalResults } from "@/api/hooks";
import type { EvalResult } from "@/api/types";
import { shortId } from "@/lib/format";

// A session-scoped result is persisted with trace_id === session_id (see the
// orchestrator's score_session). Everything else in a session is a per-turn row.
export const isSessionRow = (r: EvalResult) => r.trace_id === r.session_id;

export interface Conversation {
  sessionId: string;
  agentId: string | null;
  turnCount: number;
  lastAt: string;
  sessionVerdicts: EvalResult[];
}

export function groupConversations(results: EvalResult[]): Conversation[] {
  const bySession = new Map<string, EvalResult[]>();
  for (const r of results) {
    if (!r.session_id) continue; // legacy per-turn rows without a thread
    const list = bySession.get(r.session_id) ?? [];
    list.push(r);
    bySession.set(r.session_id, list);
  }

  const convos: Conversation[] = [];
  for (const [sessionId, rows] of bySession) {
    const turnTraces = new Set(rows.filter((r) => !isSessionRow(r)).map((r) => r.trace_id));
    const agentId = rows.find((r) => r.agent_id)?.agent_id ?? null;
    const lastAt = rows.reduce((m, r) => (r.evaluated_at > m ? r.evaluated_at : m), rows[0].evaluated_at);
    convos.push({
      sessionId,
      agentId,
      turnCount: turnTraces.size,
      lastAt,
      sessionVerdicts: rows.filter(isSessionRow),
    });
  }
  return convos.sort((a, b) => (a.lastAt < b.lastAt ? 1 : -1));
}

export function Conversations() {
  const [agentId, setAgentId] = React.useState("");

  const agents = useAgents();
  const results = useEvalResults({ agent_id: agentId || undefined, limit: 2000 });

  const agentById = new Map((agents.data ?? []).map((a) => [a.id, a]));
  const conversations = groupConversations(results.data ?? []);

  return (
    <div>
      <PageHeader
        title="Conversations"
        description="Multi-turn sessions grouped by thread, with per-turn and whole-conversation eval verdicts. For span-level detail, open a turn in Phoenix."
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <Select
          value={agentId}
          onValueChange={setAgentId}
          placeholder="All agents"
          options={(agents.data ?? []).map((a) => ({ label: a.name, value: a.id }))}
        />
      </div>

      <Card>
        <CardContent className="p-0">
          {results.isLoading ? (
            <div className="p-4"><LoadingRows /></div>
          ) : results.isError ? (
            <ErrorState error={results.error} />
          ) : conversations.length === 0 ? (
            <EmptyState message="No multi-turn sessions yet. Run the multi-turn agent (`make chat`) to create one." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Session</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead className="text-right">Turns</TableHead>
                  <TableHead>Session verdicts</TableHead>
                  <TableHead>Last activity</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {conversations.slice(0, 200).map((c) => {
                  const ag = c.agentId ? agentById.get(c.agentId) : undefined;
                  return (
                    <TableRow key={c.sessionId}>
                      <TableCell>
                        <Link
                          to={`/conversations/${c.sessionId}`}
                          className="font-mono text-xs text-primary hover:underline"
                        >
                          {shortId(c.sessionId, 12)}
                        </Link>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{ag?.name ?? "—"}</TableCell>
                      <TableCell className="num">{c.turnCount}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {c.sessionVerdicts.length === 0 ? (
                            <span className="text-xs text-muted-foreground">not scored</span>
                          ) : (
                            c.sessionVerdicts.map((v) => (
                              <span key={v.id} className="inline-flex items-center gap-1" title={v.eval_id}>
                                <VerdictBadge verdict={v.verdict} />
                              </span>
                            ))
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        <LocalTime iso={c.lastAt} />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <p className="mt-4 flex items-center justify-center gap-1 text-center text-xs text-muted-foreground">
        <MessagesSquare className="h-3.5 w-3.5" />
        Session-scoped evals (coherence, resolution) judge the whole transcript; per-turn evals stay on each turn.
      </p>
    </div>
  );
}
