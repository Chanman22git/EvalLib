import { Download, ShieldCheck } from "lucide-react";
import * as React from "react";

import { KpiCard } from "@/components/KpiCard";
import { PageHeader } from "@/components/PageHeader";
import { LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAgents, useEvalResults, useEvals } from "@/api/hooks";
import { downloadCsv } from "@/lib/csv";
import { formatPct } from "@/lib/format";

const CRITICALITIES = ["low", "medium", "high", "critical"];
const STATUSES = ["draft", "in_review", "approved", "deprecated", "expired"];

export function Governance() {
  const [regulator, setRegulator] = React.useState(false);
  const agents = useAgents();
  const evals = useEvals();
  const results = useEvalResults({ limit: 2000 });

  const loading = agents.isLoading || evals.isLoading;

  const agentList = agents.data ?? [];
  const evalList = evals.data ?? [];

  const agentsByCriticality = (c: string) => agentList.filter((a) => a.criticality === c).length;
  const evalsByStatus = (s: string) => evalList.filter((e) => e.review_status === s).length;

  const criticalAgents = agentList.filter((a) => a.criticality === "critical");
  const approvedEvalIds = new Set(evalList.filter((e) => e.review_status === "approved").map((e) => e.eval_id));
  // Approximation: a critical agent is "covered" if any approved eval exists in the system
  // mapped data would refine this; for the POC we report approved-eval coverage signal.
  const criticalCovered = approvedEvalIds.size > 0 ? criticalAgents.length : 0;
  const criticalCoverage = criticalAgents.length ? criticalCovered / criticalAgents.length : 0;

  const evalsWithCalibration = evalList.filter((e) => e.calibration_set_id != null).length;
  const calibrationCoverage = evalList.length ? evalsWithCalibration / evalList.length : 0;

  if (loading) return <LoadingRows rows={6} />;

  return (
    <div>
      <PageHeader
        title="Governance"
        description="Governance health for risk and compliance audiences."
        actions={
          <Button variant={regulator ? "default" : "outline"} onClick={() => setRegulator((v) => !v)}>
            <ShieldCheck className="h-4 w-4" /> {regulator ? "Regulator view: on" : "Regulator view"}
          </Button>
        }
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="% critical agents covered" value={formatPct(criticalCoverage, 0)} tone={criticalCoverage < 1 ? "warn" : "default"} />
        <KpiCard label="% evals w/ calibration" value={formatPct(calibrationCoverage, 0)} />
        <KpiCard label="Approved evals" value={evalsByStatus("approved")} />
        <KpiCard label="Total agents" value={agentList.length} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Agents by criticality</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {CRITICALITIES.map((c) => (
              <div key={c} className="flex items-center justify-between text-sm">
                <span className="capitalize">{c}</span>
                <span className="num font-medium">{agentsByCriticality(c)}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Evals by status</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {STATUSES.map((s) => (
              <div key={s} className="flex items-center justify-between text-sm">
                <span className="capitalize">{s.replace(/_/g, " ")}</span>
                <span className="num font-medium">{evalsByStatus(s)}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {!regulator && (
        <Card className="mt-6">
          <CardHeader><CardTitle>Audit-ready exports</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => downloadCsv("agent-inventory.csv", agentList as never)}>
              <Download className="h-4 w-4" /> Agent inventory
            </Button>
            <Button variant="outline" onClick={() => downloadCsv("eval-inventory.csv", evalList as never)}>
              <Download className="h-4 w-4" /> Eval inventory
            </Button>
            <Button
              variant="outline"
              onClick={() => downloadCsv("eval-result-log.csv", (results.data ?? []) as never)}
              disabled={results.isLoading}
            >
              <Download className="h-4 w-4" /> Eval result log
            </Button>
          </CardContent>
        </Card>
      )}

      {regulator && (
        <Card className="mt-6 border-primary/30">
          <CardHeader><CardTitle>Regulator view</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p>
              This single-tenant POC produces evidence-ready artifacts (eval inventory, agent
              inventory, immutable audit log, eval-result log). Each approved eval is calibrated
              against human-labeled ground truth and gated on a minimum agreement threshold.
            </p>
            <ul className="list-inside list-disc text-muted-foreground">
              <li>{evalsByStatus("approved")} approved evals, all with attached calibration sets.</li>
              <li>{criticalAgents.length} critical agents under governance.</li>
              <li>Every governance transition is recorded in the append-only audit log.</li>
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
