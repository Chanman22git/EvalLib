import { ExternalLink } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { JsonButton } from "@/components/JsonButton";
import { LocalTime } from "@/components/LocalTime";
import { PageHeader } from "@/components/PageHeader";
import { PassRateChart } from "@/components/PassRateChart";
import { CriticalityBadge } from "@/components/StatusBadge";
import { VerdictBadge } from "@/components/VerdictBadge";
import { ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useAgent,
  useChangeEvents,
  useEvalAgentMappings,
  useEvalResults,
  useEvalResultsAggregate,
  useEvals,
} from "@/api/hooks";
import { PHOENIX_URL, phoenixTraceUrl } from "@/lib/config";
import { formatPct, formatScore, shortId } from "@/lib/format";
import { dailyPassRate } from "@/lib/series";

export function AgentDetail() {
  const { id } = useParams();
  const agent = useAgent(id);
  const mappings = useEvalAgentMappings({ agent_id: id });
  const evals = useEvals();
  const aggregate = useEvalResultsAggregate({ agent_id: id });
  const results = useEvalResults({ agent_id: id, limit: 1000 });
  const changes = useChangeEvents({ agent_id: id });

  const evalById = new Map((evals.data ?? []).map((e) => [e.id, e]));
  const aggByEvalId = new Map((aggregate.data ?? []).map((a) => [a.eval_id, a]));

  if (agent.isLoading) return <LoadingRows rows={6} />;
  if (agent.isError) return <ErrorState error={agent.error} />;
  if (!agent.data) return null;
  const a = agent.data;

  return (
    <div>
      <PageHeader
        title={a.name}
        description={a.description ?? undefined}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <a href={PHOENIX_URL} target="_blank" rel="noreferrer">
                <ExternalLink className="h-4 w-4" /> Open in Phoenix
              </a>
            </Button>
            <JsonButton data={a} title="Agent JSON" />
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Metadata</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Field label="Criticality"><CriticalityBadge criticality={a.criticality} /></Field>
            <Field label="Data classification">{a.data_classification}</Field>
            <Field label="Framework">{a.framework}</Field>
            <Field label="Business unit">{a.business_unit}</Field>
            <Field label="Owner team">{a.owner_team}</Field>
            <Field label="Owner email">{a.owner_email || "—"}</Field>
            <Field label="Third-party">{a.is_third_party ? "Yes" : "No"}</Field>
            <Field label="Status">
              <Badge className="bg-muted text-muted-foreground border-border">{a.status}</Badge>
            </Field>
            <Field label="Registered"><LocalTime iso={a.created_at} /></Field>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Eval pass-rate · last 7 days</CardTitle>
          </CardHeader>
          <CardContent>
            {results.isLoading ? (
              <LoadingRows rows={4} />
            ) : (
              <PassRateChart data={dailyPassRate(results.data ?? [], 7)} />
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Attached evals</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {mappings.isLoading ? (
            <div className="p-4"><LoadingRows rows={3} /></div>
          ) : !mappings.data?.length ? (
            <p className="p-4 text-sm text-muted-foreground">No evals attached to this agent.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Eval</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Sample rate</TableHead>
                  <TableHead className="text-right">Pass rate</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mappings.data.map((m) => {
                  const ev = evalById.get(m.eval_id);
                  const agg = ev ? aggByEvalId.get(ev.eval_id) : undefined;
                  return (
                    <TableRow key={m.id}>
                      <TableCell>
                        {ev ? (
                          <Link to={`/evals/${ev.id}`} className="font-medium text-primary hover:underline">
                            {ev.eval_id}
                          </Link>
                        ) : (
                          shortId(m.eval_id)
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{ev?.review_status ?? "—"}</TableCell>
                      <TableCell className="num">{formatPct(m.sample_rate, 0)}</TableCell>
                      <TableCell className="num">{agg ? formatPct(agg.pass_rate, 0) : "—"}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent traces</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {results.isLoading ? (
              <div className="p-4"><LoadingRows rows={4} /></div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Trace</TableHead>
                    <TableHead>Verdict</TableHead>
                    <TableHead className="text-right">Score</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(results.data ?? []).slice(0, 8).map((r) => (
                    <TableRow key={r.id}>
                      <TableCell>
                        <Link to={`/traces/${r.trace_id}`} className="font-mono text-xs text-primary hover:underline">
                          {shortId(r.trace_id, 12)}
                        </Link>
                      </TableCell>
                      <TableCell><VerdictBadge verdict={r.verdict} /></TableCell>
                      <TableCell className="num">{formatScore(r.score)}</TableCell>
                      <TableCell className="text-right">
                        <a href={phoenixTraceUrl(r.trace_id)} target="_blank" rel="noreferrer" title="Open in Phoenix">
                          <ExternalLink className="inline h-3.5 w-3.5 text-muted-foreground" />
                        </a>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Change events</CardTitle>
          </CardHeader>
          <CardContent>
            {changes.isLoading ? (
              <LoadingRows rows={3} />
            ) : !changes.data?.length ? (
              <p className="text-sm text-muted-foreground">No change events for this agent.</p>
            ) : (
              <ul className="space-y-3">
                {changes.data.map((c) => (
                  <li key={c.id} className="border-l-2 border-border pl-3">
                    <div className="flex items-center gap-2">
                      <Badge className="bg-muted text-muted-foreground border-border">
                        {c.event_type.replace(/_/g, " ")}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        <LocalTime iso={c.timestamp} />
                      </span>
                    </div>
                    {c.reason && <p className="mt-1 text-sm">{c.reason}</p>}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium">{children}</span>
    </div>
  );
}
