import * as React from "react";
import { Link } from "react-router-dom";

import { JsonButton } from "@/components/JsonButton";
import { LocalTime } from "@/components/LocalTime";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { useAgents, useRegressionAlerts, useUpdateRegressionStatus } from "@/api/hooks";
import type { RegressionAlert } from "@/api/types";
import { formatPct, formatScore } from "@/lib/format";

const STATUSES = ["open", "investigating", "resolved", "dismissed"];

export function Regressions() {
  const [status, setStatus] = React.useState("");
  const alerts = useRegressionAlerts(status ? { status } : undefined);
  const agents = useAgents();
  const agentById = new Map((agents.data ?? []).map((a) => [a.id, a]));

  return (
    <div>
      <PageHeader
        title="Regression Alerts"
        description="Detected eval-score regressions with ranked candidate causes."
      />

      <div className="mb-4 flex gap-2">
        <Select
          value={status}
          onValueChange={setStatus}
          placeholder="All statuses"
          options={STATUSES.map((s) => ({ label: s, value: s }))}
        />
      </div>

      {alerts.isLoading ? (
        <LoadingRows rows={3} />
      ) : alerts.isError ? (
        <ErrorState error={alerts.error} />
      ) : !alerts.data?.length ? (
        <EmptyState message="No regression alerts. Agents are behaving." />
      ) : (
        <div className="space-y-4">
          {alerts.data.map((alert) => (
            <AlertCard key={alert.id} alert={alert} agentName={alert.agent_id ? agentById.get(alert.agent_id)?.name : undefined} />
          ))}
        </div>
      )}
    </div>
  );
}

function AlertCard({ alert, agentName }: { alert: RegressionAlert; agentName?: string }) {
  const update = useUpdateRegressionStatus(alert.id);
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            {alert.eval_id}
            <Badge className="bg-verdict-fail/15 text-verdict-fail border-verdict-fail/30">
              {formatPct(alert.delta, 1)}
            </Badge>
          </CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">
            {alert.agent_id ? (
              <Link to={`/agents/${alert.agent_id}`} className="text-primary hover:underline">
                {agentName ?? "agent"}
              </Link>
            ) : (
              "—"
            )}{" "}
            · detected <LocalTime iso={alert.detected_at} />
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={alert.status}
            onValueChange={(v) => update.mutate(v)}
            options={STATUSES.map((s) => ({ label: s, value: s }))}
          />
          <JsonButton data={alert} title="Alert JSON" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-3 flex gap-6 text-sm">
          <span>Baseline: <span className="num font-medium">{formatScore(alert.baseline_score)}</span></span>
          <span>Current: <span className="num font-medium text-verdict-fail">{formatScore(alert.current_score)}</span></span>
        </div>
        <div>
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Candidate causes (ranked by temporal proximity)
          </div>
          {!alert.candidate_causes?.length ? (
            <p className="text-sm text-muted-foreground">No candidate causes identified.</p>
          ) : (
            <ol className="space-y-1">
              {(alert.candidate_causes as Array<Record<string, unknown>>).map((c, i) => (
                <li key={i} className="flex items-center gap-2 text-sm">
                  <Badge className="bg-muted text-muted-foreground border-border">#{(c.rank as number) ?? i + 1}</Badge>
                  <span className="font-medium">{String(c.event_type ?? "event")}</span>
                  <span className="text-muted-foreground">{String(c.reason ?? "")}</span>
                  {c.proximity_hours != null && (
                    <span className="text-xs text-muted-foreground">(~{String(c.proximity_hours)}h before)</span>
                  )}
                </li>
              ))}
            </ol>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
