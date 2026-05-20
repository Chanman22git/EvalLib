import { ExternalLink } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { LocalTime } from "@/components/LocalTime";
import { PageHeader } from "@/components/PageHeader";
import { VerdictBadge } from "@/components/VerdictBadge";
import { ErrorState, LoadingRows } from "@/components/states";
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
import { PHOENIX_URL, phoenixTraceUrl } from "@/lib/config";
import { formatScore, shortId } from "@/lib/format";
import { verdictTone } from "@/lib/verdict";

const TONES = [
  { label: "Pass", value: "pass" },
  { label: "Partial", value: "partial" },
  { label: "Fail", value: "fail" },
];

export function Traces() {
  const [agentId, setAgentId] = React.useState("");
  const [tone, setTone] = React.useState("");

  const agents = useAgents();
  const results = useEvalResults({ agent_id: agentId || undefined, limit: 500 });

  const agentById = new Map((agents.data ?? []).map((a) => [a.id, a]));
  const rows = (results.data ?? []).filter((r) => !tone || verdictTone(r.verdict) === tone);

  return (
    <div>
      <PageHeader
        title="Trace Explorer"
        description="Evaluated traces with the enterprise governance overlay. For span-level detail, open the trace in Phoenix."
        actions={
          <a
            href={PHOENIX_URL}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
          >
            <ExternalLink className="h-4 w-4" /> Phoenix trace UI
          </a>
        }
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <Select
          value={agentId}
          onValueChange={setAgentId}
          placeholder="All agents"
          options={(agents.data ?? []).map((a) => ({ label: a.name, value: a.id }))}
        />
        <Select value={tone} onValueChange={setTone} placeholder="Any verdict" options={TONES} />
      </div>

      <Card>
        <CardContent className="p-0">
          {results.isLoading ? (
            <div className="p-4"><LoadingRows /></div>
          ) : results.isError ? (
            <ErrorState error={results.error} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Trace</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>Eval</TableHead>
                  <TableHead>Verdict</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                  <TableHead>When</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.slice(0, 200).map((r) => {
                  const ag = r.agent_id ? agentById.get(r.agent_id) : undefined;
                  return (
                    <TableRow key={r.id}>
                      <TableCell>
                        <Link to={`/traces/${r.trace_id}`} className="font-mono text-xs text-primary hover:underline">
                          {shortId(r.trace_id, 12)}
                        </Link>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{ag?.name ?? "—"}</TableCell>
                      <TableCell className="text-muted-foreground">{r.eval_id}</TableCell>
                      <TableCell><VerdictBadge verdict={r.verdict} /></TableCell>
                      <TableCell className="num">{formatScore(r.score)}</TableCell>
                      <TableCell className="text-xs text-muted-foreground"><LocalTime iso={r.evaluated_at} /></TableCell>
                      <TableCell className="text-right">
                        <a href={phoenixTraceUrl(r.trace_id)} target="_blank" rel="noreferrer" title="Open in Phoenix">
                          <ExternalLink className="inline h-3.5 w-3.5 text-muted-foreground" />
                        </a>
                      </TableCell>
                    </TableRow>
                  );
                })}
                {rows.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                      No traces match these filters.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
