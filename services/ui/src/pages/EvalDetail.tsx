import { useParams } from "react-router-dom";
import { Link } from "react-router-dom";

import { EvalGovernanceActions } from "@/components/EvalGovernanceActions";
import { JsonButton } from "@/components/JsonButton";
import { LocalTime } from "@/components/LocalTime";
import { PageHeader } from "@/components/PageHeader";
import { ReviewStatusBadge } from "@/components/StatusBadge";
import { VerdictBadge } from "@/components/VerdictBadge";
import { ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PassRateChart } from "@/components/PassRateChart";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useAgents,
  useAuditLog,
  useCalibrationSets,
  useEval,
  useEvalAgentMappings,
  useEvalResults,
} from "@/api/hooks";
import { formatPct, formatScore, shortId } from "@/lib/format";
import { dailyPassRate } from "@/lib/series";

function TemplateViewer({ template }: { template: string }) {
  const parts = template.split(/(\{[^}]+\})/g);
  return (
    <pre className="overflow-auto rounded-md bg-muted p-3 text-xs font-mono leading-relaxed">
      {parts.map((p, i) =>
        /^\{[^}]+\}$/.test(p) ? (
          <span key={i} className="rounded bg-primary/15 px-1 font-semibold text-primary">
            {p}
          </span>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </pre>
  );
}

export function EvalDetail() {
  const { id } = useParams();
  const ev = useEval(id);
  const mappings = useEvalAgentMappings({ eval_id: id });
  const agents = useAgents();
  const calibrationSets = useCalibrationSets();
  const audit = useAuditLog({ entity_type: "eval", entity_id: id });
  const results = useEvalResults({ eval_id: ev.data?.eval_id, limit: 100 });

  if (ev.isLoading) return <LoadingRows rows={6} />;
  if (ev.isError) return <ErrorState error={ev.error} />;
  if (!ev.data) return null;
  const e = ev.data;

  const agentById = new Map((agents.data ?? []).map((a) => [a.id, a]));
  const calibration = (calibrationSets.data ?? []).find((c) => c.id === e.calibration_set_id);
  const agreementOk =
    e.last_judge_human_agreement != null && e.last_judge_human_agreement >= e.agreement_threshold;

  return (
    <div>
      <PageHeader
        title={e.eval_id}
        description={e.criterion_description}
        actions={
          <div className="flex items-center gap-2">
            <ReviewStatusBadge status={e.review_status} />
            <JsonButton data={e} title="Eval JSON" />
          </div>
        }
      />

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Governance</CardTitle>
        </CardHeader>
        <CardContent>
          <EvalGovernanceActions ev={e} />
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader><CardTitle>Metadata</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Field label="Version">{e.version}</Field>
            <Field label="Evaluator type">{e.evaluator_type.replace(/_/g, " ")}</Field>
            <Field label="Owner team">{e.owner_team}</Field>
            <Field label="Approver">{e.approver_email ?? "—"}</Field>
            <Field label="Judge model">{(e.judge_config as Record<string, unknown>)?.model as string ?? "—"}</Field>
            <Field label="Approved at"><LocalTime iso={e.approved_at} /></Field>
            <Field label="Expires at"><LocalTime iso={e.expires_at} /></Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Calibration</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {calibration ? (
              <>
                <Field label="Set">{calibration.name}</Field>
                <Field label="Examples">{calibration.examples.length}</Field>
              </>
            ) : (
              <p className="text-muted-foreground">No calibration set attached.</p>
            )}
            <Field label="Threshold">{formatPct(e.agreement_threshold, 0)}</Field>
            <Field label="Agreement">
              {e.last_judge_human_agreement != null ? formatPct(e.last_judge_human_agreement, 0) : "—"}
            </Field>
            <Field label="Gate">
              {e.last_judge_human_agreement == null ? (
                <Badge className="bg-muted text-muted-foreground border-border">untested</Badge>
              ) : agreementOk ? (
                <Badge className="bg-verdict-pass/15 text-verdict-pass border-verdict-pass/30">pass</Badge>
              ) : (
                <Badge className="bg-verdict-fail/15 text-verdict-fail border-verdict-fail/30">below threshold</Badge>
              )}
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Attached agents</CardTitle></CardHeader>
          <CardContent>
            {!mappings.data?.length ? (
              <p className="text-sm text-muted-foreground">Not attached to any agents.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {mappings.data.map((m) => {
                  const ag = agentById.get(m.agent_id);
                  return (
                    <li key={m.id} className="flex items-center justify-between">
                      {ag ? (
                        <Link to={`/agents/${ag.id}`} className="text-primary hover:underline">{ag.name}</Link>
                      ) : (
                        shortId(m.agent_id)
                      )}
                      <span className="num text-muted-foreground">{formatPct(m.sample_rate, 0)}</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {e.prompt_template && (
        <Card className="mt-6">
          <CardHeader><CardTitle>Prompt template</CardTitle></CardHeader>
          <CardContent><TemplateViewer template={e.prompt_template} /></CardContent>
        </Card>
      )}

      <Card className="mt-6">
        <CardHeader><CardTitle>Score · last 7 days</CardTitle></CardHeader>
        <CardContent>
          {results.isLoading ? <LoadingRows rows={3} /> : <PassRateChart data={dailyPassRate(results.data ?? [], 7)} />}
        </CardContent>
      </Card>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Recent results</CardTitle></CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Trace</TableHead>
                  <TableHead>Verdict</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                  <TableHead>When</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(results.data ?? []).slice(0, 20).map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>
                      <Link to={`/traces/${r.trace_id}`} className="font-mono text-xs text-primary hover:underline">
                        {shortId(r.trace_id, 10)}
                      </Link>
                    </TableCell>
                    <TableCell><VerdictBadge verdict={r.verdict} /></TableCell>
                    <TableCell className="num">{formatScore(r.score)}</TableCell>
                    <TableCell className="text-xs text-muted-foreground"><LocalTime iso={r.evaluated_at} /></TableCell>
                  </TableRow>
                ))}
                {results.data?.length === 0 && (
                  <TableRow><TableCell colSpan={4} className="py-6 text-center text-muted-foreground">No results yet.</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Audit trail</CardTitle></CardHeader>
          <CardContent>
            {audit.isLoading ? (
              <LoadingRows rows={3} />
            ) : !audit.data?.length ? (
              <p className="text-sm text-muted-foreground">No audit entries.</p>
            ) : (
              <ul className="space-y-3">
                {audit.data.map((entry) => (
                  <li key={entry.id} className="border-l-2 border-border pl-3">
                    <div className="flex items-center gap-2">
                      <Badge className="bg-muted text-muted-foreground border-border">{entry.action}</Badge>
                      <span className="text-xs text-muted-foreground">{entry.actor}</span>
                      <span className="text-xs text-muted-foreground"><LocalTime iso={entry.timestamp} /></span>
                    </div>
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
