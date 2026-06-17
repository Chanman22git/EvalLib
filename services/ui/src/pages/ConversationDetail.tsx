import { ExternalLink } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { JsonButton } from "@/components/JsonButton";
import { LocalTime } from "@/components/LocalTime";
import { PageHeader } from "@/components/PageHeader";
import { VerdictBadge } from "@/components/VerdictBadge";
import { EmptyState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAgents, useEvalResults } from "@/api/hooks";
import type { EvalResult } from "@/api/types";
import { phoenixTraceUrl } from "@/lib/config";
import { formatScore, shortId } from "@/lib/format";
import { isSessionRow } from "@/pages/Conversations";

interface Turn {
  traceId: string;
  at: string;
  results: EvalResult[];
}

function groupTurns(rows: EvalResult[]): Turn[] {
  const byTrace = new Map<string, EvalResult[]>();
  for (const r of rows) {
    const list = byTrace.get(r.trace_id) ?? [];
    list.push(r);
    byTrace.set(r.trace_id, list);
  }
  const turns: Turn[] = [];
  for (const [traceId, results] of byTrace) {
    const at = results.reduce((m, r) => (r.evaluated_at < m ? r.evaluated_at : m), results[0].evaluated_at);
    turns.push({ traceId, at, results });
  }
  // Oldest first — reads top-to-bottom like the conversation happened.
  return turns.sort((a, b) => (a.at < b.at ? -1 : 1));
}

function VerdictRow({ r }: { r: EvalResult }) {
  return (
    <li className="rounded-md border p-3">
      <div className="flex items-center justify-between">
        <span className="font-medium">{r.eval_id}</span>
        <div className="flex items-center gap-2">
          <VerdictBadge verdict={r.verdict} />
          <span className="num text-sm">{formatScore(r.score)}</span>
        </div>
      </div>
      {r.reasoning && <p className="mt-2 text-sm text-muted-foreground">{r.reasoning}</p>}
      <div className="mt-2 flex gap-4 text-xs text-muted-foreground">
        <span>judge: {r.judge_model ?? "—"}</span>
        <span>v{r.eval_version}</span>
        <LocalTime iso={r.evaluated_at} />
      </div>
    </li>
  );
}

export function ConversationDetail() {
  const { sessionId } = useParams();
  const results = useEvalResults({ session_id: sessionId, limit: 500 });
  const agents = useAgents();

  const rows = results.data ?? [];
  const sessionVerdicts = rows.filter(isSessionRow);
  const turns = groupTurns(rows.filter((r) => !isSessionRow(r)));

  const agentById = new Map((agents.data ?? []).map((a) => [a.id, a]));
  const agentId = rows.find((r) => r.agent_id)?.agent_id;
  const agent = agentId ? agentById.get(agentId) : undefined;

  return (
    <div>
      <PageHeader
        title="Conversation"
        description={sessionId}
        actions={results.data?.length ? <JsonButton data={results.data} title="Session results JSON" /> : undefined}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader><CardTitle>Session context</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">Session ID</span>
              <span className="font-mono text-xs break-all">{sessionId}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Turns</span>
              <span>{turns.length}</span>
            </div>
            {agent ? (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Agent</span>
                <Link to={`/agents/${agent.id}`} className="text-primary hover:underline">{agent.name}</Link>
              </div>
            ) : null}
            <p className="pt-2 text-xs text-muted-foreground">
              Turn text lives in Phoenix — EvalLib stores verdicts, not conversation content.
            </p>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Session-scoped verdicts</CardTitle></CardHeader>
          <CardContent>
            {results.isLoading ? (
              <LoadingRows rows={2} />
            ) : sessionVerdicts.length === 0 ? (
              <EmptyState message="This conversation has not been scored at the session level yet." />
            ) : (
              <ul className="space-y-3">
                {sessionVerdicts.map((r) => <VerdictRow key={r.id} r={r} />)}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader><CardTitle>Turns</CardTitle></CardHeader>
        <CardContent>
          {results.isLoading ? (
            <LoadingRows rows={3} />
          ) : turns.length === 0 ? (
            <EmptyState message="No per-turn eval results for this session." />
          ) : (
            <ol className="space-y-4">
              {turns.map((t, i) => (
                <li key={t.traceId} className="rounded-md border p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-sm font-medium">
                      Turn {i + 1}
                      <Link to={`/traces/${t.traceId}`} className="ml-2 font-mono text-xs text-primary hover:underline">
                        {shortId(t.traceId, 12)}
                      </Link>
                    </span>
                    <Button variant="outline" size="sm" asChild>
                      <a href={phoenixTraceUrl(t.traceId)} target="_blank" rel="noreferrer" title="Open turn in Phoenix">
                        <ExternalLink className="h-3.5 w-3.5" /> Phoenix
                      </a>
                    </Button>
                  </div>
                  <ul className="space-y-2">
                    {t.results.map((r) => <VerdictRow key={r.id} r={r} />)}
                  </ul>
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
