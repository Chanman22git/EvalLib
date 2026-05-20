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
import { PHOENIX_URL, phoenixTraceUrl } from "@/lib/config";
import { formatScore } from "@/lib/format";

export function TraceDetail() {
  const { traceId } = useParams();
  const results = useEvalResults({ trace_id: traceId, limit: 100 });
  const agents = useAgents();

  const agentById = new Map((agents.data ?? []).map((a) => [a.id, a]));
  const agentId = results.data?.find((r) => r.agent_id)?.agent_id;
  const agent = agentId ? agentById.get(agentId) : undefined;

  return (
    <div>
      <PageHeader
        title="Trace detail"
        description={traceId}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <a href={phoenixTraceUrl(traceId ?? "")} target="_blank" rel="noreferrer">
                <ExternalLink className="h-4 w-4" /> Open in Phoenix
              </a>
            </Button>
            <Button variant="outline" disabled title="Configure Datadog to enable">
              <ExternalLink className="h-4 w-4" /> Open in Datadog
            </Button>
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader><CardTitle>Trace context</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">Trace ID</span>
              <span className="font-mono text-xs break-all">{traceId}</span>
            </div>
            {agent ? (
              <>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Agent</span>
                  <Link to={`/agents/${agent.id}`} className="text-primary hover:underline">{agent.name}</Link>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Criticality</span>
                  <span>{agent.criticality}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Data class</span>
                  <span>{agent.data_classification}</span>
                </div>
              </>
            ) : (
              <p className="text-muted-foreground">Agent metadata not available for this trace.</p>
            )}
            <p className="pt-2 text-xs text-muted-foreground">
              The full span tree (latency, tokens, cost) lives in Phoenix — EvalLib does not duplicate it.
            </p>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>Eval results for this trace</CardTitle>
            {results.data?.length ? <JsonButton data={results.data} title="Eval results JSON" /> : null}
          </CardHeader>
          <CardContent>
            {results.isLoading ? (
              <LoadingRows rows={3} />
            ) : !results.data?.length ? (
              <EmptyState message="No evals have been run on this trace yet." />
            ) : (
              <ul className="space-y-3">
                {results.data.map((r) => (
                  <li key={r.id} className="rounded-md border p-3">
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
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <p className="mt-4 text-center text-xs text-muted-foreground">
        Phoenix: <a className="text-primary hover:underline" href={PHOENIX_URL} target="_blank" rel="noreferrer">{PHOENIX_URL}</a>
      </p>
    </div>
  );
}
