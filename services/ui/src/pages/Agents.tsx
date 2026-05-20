import { Plus } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { CriticalityBadge } from "@/components/StatusBadge";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
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
  useCreateAgent,
  useEvalAgentMappings,
  useEvalResultsAggregate,
} from "@/api/hooks";
import type { AgentCreate } from "@/api/types";
import { formatPct } from "@/lib/format";

const CRITICALITIES = ["low", "medium", "high", "critical"];
const CLASSIFICATIONS = ["public", "internal", "confidential", "restricted"];
const FRAMEWORKS = ["langgraph", "crewai", "custom", "vendor"];

export function Agents() {
  const [criticality, setCriticality] = React.useState("");
  const [framework, setFramework] = React.useState("");
  const [thirdParty, setThirdParty] = React.useState("");

  const params: Record<string, unknown> = {};
  if (criticality) params.criticality = criticality;
  if (framework) params.framework = framework;
  if (thirdParty) params.is_third_party = thirdParty;

  const agents = useAgents(params);
  const mappings = useEvalAgentMappings();
  const aggregate = useEvalResultsAggregate();

  const evalCount = (agentId: string) =>
    (mappings.data ?? []).filter((m) => m.agent_id === agentId).length;

  const passRate = (agentId: string) => {
    const rows = (aggregate.data ?? []).filter((a) => a.agent_id === agentId);
    if (!rows.length) return null;
    const total = rows.reduce((a, r) => a + r.count, 0);
    const weighted = rows.reduce((a, r) => a + r.pass_rate * r.count, 0);
    return total ? weighted / total : null;
  };

  return (
    <div>
      <PageHeader
        title="Agent Registry"
        description="Every agent that calls through the gateway, with its governance metadata."
        actions={<RegisterAgentDialog />}
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <Select
          value={criticality}
          onValueChange={setCriticality}
          placeholder="All criticalities"
          options={CRITICALITIES.map((c) => ({ label: c, value: c }))}
        />
        <Select
          value={framework}
          onValueChange={setFramework}
          placeholder="All frameworks"
          options={FRAMEWORKS.map((f) => ({ label: f, value: f }))}
        />
        <Select
          value={thirdParty}
          onValueChange={setThirdParty}
          placeholder="Any provenance"
          options={[
            { label: "Third-party", value: "true" },
            { label: "First-party", value: "false" },
          ]}
        />
      </div>

      <Card>
        <CardContent className="p-0">
          {agents.isLoading ? (
            <div className="p-4">
              <LoadingRows />
            </div>
          ) : agents.isError ? (
            <ErrorState error={agents.error} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Framework</TableHead>
                  <TableHead>Criticality</TableHead>
                  <TableHead>Data class</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Evals</TableHead>
                  <TableHead className="text-right">Pass rate</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agents.data?.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell>
                      <Link to={`/agents/${a.id}`} className="font-medium text-primary hover:underline">
                        {a.name}
                      </Link>
                      {a.is_third_party && (
                        <Badge className="ml-2 bg-muted text-muted-foreground border-border">3p</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{a.framework}</TableCell>
                    <TableCell>
                      <CriticalityBadge criticality={a.criticality} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">{a.data_classification}</TableCell>
                    <TableCell className="text-muted-foreground">{a.owner_team}</TableCell>
                    <TableCell>
                      <Badge className="bg-muted text-muted-foreground border-border">{a.status}</Badge>
                    </TableCell>
                    <TableCell className="num">{evalCount(a.id)}</TableCell>
                    <TableCell className="num">{formatPct(passRate(a.id), 0)}</TableCell>
                  </TableRow>
                ))}
                {agents.data?.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                      No agents match these filters.
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

function RegisterAgentDialog() {
  const [open, setOpen] = React.useState(false);
  const create = useCreateAgent();
  const [form, setForm] = React.useState<AgentCreate>({
    name: "",
    framework: "custom",
    criticality: "low",
    data_classification: "internal",
    business_unit: "",
    owner_team: "",
    owner_email: "",
    is_third_party: false,
  });

  const set = (k: keyof AgentCreate, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    create.mutate(form, { onSuccess: () => setOpen(false) });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4" /> Register New Agent
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Register New Agent</DialogTitle>
        </DialogHeader>
        <form onSubmit={submit} className="grid gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="name">Name</Label>
            <Input id="name" required value={form.name} onChange={(e) => set("name", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label>Framework</Label>
              <Select
                value={form.framework ?? "custom"}
                onValueChange={(v) => set("framework", v)}
                options={FRAMEWORKS.map((f) => ({ label: f, value: f }))}
              />
            </div>
            <div className="grid gap-1.5">
              <Label>Criticality</Label>
              <Select
                value={form.criticality ?? "low"}
                onValueChange={(v) => set("criticality", v)}
                options={CRITICALITIES.map((c) => ({ label: c, value: c }))}
              />
            </div>
            <div className="grid gap-1.5">
              <Label>Data classification</Label>
              <Select
                value={form.data_classification ?? "internal"}
                onValueChange={(v) => set("data_classification", v)}
                options={CLASSIFICATIONS.map((c) => ({ label: c, value: c }))}
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="bu">Business unit</Label>
              <Input id="bu" value={form.business_unit ?? ""} onChange={(e) => set("business_unit", e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="team">Owner team</Label>
              <Input id="team" value={form.owner_team ?? ""} onChange={(e) => set("owner_team", e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="email">Owner email</Label>
              <Input id="email" type="email" value={form.owner_email ?? ""} onChange={(e) => set("owner_email", e.target.value)} />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_third_party ?? false}
              onChange={(e) => set("is_third_party", e.target.checked)}
            />
            Third-party / vendor agent
          </label>
          {create.isError && <ErrorState error={create.error} />}
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? "Registering…" : "Register agent"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
