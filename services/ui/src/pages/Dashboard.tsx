import { Bot, GitCompareArrows, ListChecks, Play } from "lucide-react";
import { Link } from "react-router-dom";

import { KpiCard } from "@/components/KpiCard";
import { LocalTime } from "@/components/LocalTime";
import { PageHeader } from "@/components/PageHeader";
import { PassRateChart } from "@/components/PassRateChart";
import { ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useAgents,
  useChangeEvents,
  useEvalResults,
  useEvals,
  useRegressionAlerts,
} from "@/api/hooks";
import { formatPct } from "@/lib/format";
import { dailyPassRate } from "@/lib/series";

export function Dashboard() {
  const agents = useAgents({ status: "active" });
  const evals = useEvals({ status: "approved" });
  const results = useEvalResults({ limit: 2000 });
  const regressions = useRegressionAlerts({ status: "open" });
  const changes = useChangeEvents({ limit: 10 });

  const dayMs = 24 * 60 * 60 * 1000;
  const since24h = Date.now() - dayMs;
  const runs24h = (results.data ?? []).filter(
    (r) => r.evaluated_at && new Date(r.evaluated_at).getTime() >= since24h,
  ).length;

  const series = dailyPassRate(results.data ?? [], 7);
  const overallPass = series.reduce((a, p) => a + p.passRate * p.count, 0);
  const overallCount = series.reduce((a, p) => a + p.count, 0);

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Governance health across all agents and evals."
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Active agents" value={agents.data?.length ?? "—"} icon={<Bot className="h-7 w-7" />} />
        <KpiCard
          label="Approved evals"
          value={evals.data?.length ?? "—"}
          icon={<ListChecks className="h-7 w-7" />}
        />
        <KpiCard label="Evals run · 24h" value={runs24h} icon={<Play className="h-7 w-7" />} />
        <KpiCard
          label="Open regressions"
          value={regressions.data?.length ?? "—"}
          tone={(regressions.data?.length ?? 0) > 0 ? "danger" : "default"}
          icon={<GitCompareArrows className="h-7 w-7" />}
        />
      </div>

      <Card className="mb-6">
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Aggregate eval pass-rate · last 7 days</CardTitle>
          <span className="text-sm text-muted-foreground">
            {overallCount ? `${formatPct(overallPass / overallCount, 1)} overall` : "no data"}
          </span>
        </CardHeader>
        <CardContent>
          {results.isLoading ? (
            <LoadingRows rows={4} />
          ) : results.isError ? (
            <ErrorState error={results.error} />
          ) : (
            <PassRateChart data={series} />
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent regression alerts</CardTitle>
          </CardHeader>
          <CardContent>
            {regressions.isLoading ? (
              <LoadingRows rows={3} />
            ) : !regressions.data?.length ? (
              <p className="text-sm text-muted-foreground">No open regressions. 🎉</p>
            ) : (
              <ul className="divide-y">
                {regressions.data.slice(0, 5).map((r) => (
                  <li key={r.id} className="flex items-center justify-between py-2">
                    <Link to="/regressions" className="text-sm font-medium hover:underline">
                      {r.eval_id}
                    </Link>
                    <Badge className="bg-verdict-fail/15 text-verdict-fail border-verdict-fail/30">
                      {formatPct(r.delta, 1)}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent change events</CardTitle>
          </CardHeader>
          <CardContent>
            {changes.isLoading ? (
              <LoadingRows rows={4} />
            ) : !changes.data?.length ? (
              <p className="text-sm text-muted-foreground">No change events.</p>
            ) : (
              <ul className="divide-y">
                {changes.data.slice(0, 10).map((c) => (
                  <li key={c.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                    <span className="flex items-center gap-2">
                      <Badge className="bg-muted text-muted-foreground border-border">
                        {c.event_type.replace(/_/g, " ")}
                      </Badge>
                      <span className="text-muted-foreground">{c.reason ?? ""}</span>
                    </span>
                    <span className="text-muted-foreground">
                      <LocalTime iso={c.timestamp} />
                    </span>
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
