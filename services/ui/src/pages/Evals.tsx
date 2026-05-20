import { Plus } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/PageHeader";
import { ReviewStatusBadge } from "@/components/StatusBadge";
import { ErrorState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input, Textarea } from "@/components/ui/input";
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
import { useCreateEval, useEvals } from "@/api/hooks";
import type { EvalCreate } from "@/api/types";
import { formatPct } from "@/lib/format";

const STATUSES = ["draft", "in_review", "approved", "deprecated", "expired"];
const EVALUATOR_TYPES = ["llm_as_judge", "deterministic", "embedding", "hybrid"];

export function Evals() {
  const [status, setStatus] = React.useState("");
  const [evaluatorType, setEvaluatorType] = React.useState("");

  const params: Record<string, unknown> = {};
  if (status) params.status = status;
  if (evaluatorType) params.evaluator_type = evaluatorType;
  const evals = useEvals(params);

  return (
    <div>
      <PageHeader
        title="Eval Registry"
        description="Versioned, owned, and governance-gated evaluations."
        actions={<CreateEvalDialog />}
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <Select
          value={status}
          onValueChange={setStatus}
          placeholder="All statuses"
          options={STATUSES.map((s) => ({ label: s.replace(/_/g, " "), value: s }))}
        />
        <Select
          value={evaluatorType}
          onValueChange={setEvaluatorType}
          placeholder="All evaluator types"
          options={EVALUATOR_TYPES.map((t) => ({ label: t.replace(/_/g, " "), value: t }))}
        />
      </div>

      <Card>
        <CardContent className="p-0">
          {evals.isLoading ? (
            <div className="p-4"><LoadingRows /></div>
          ) : evals.isError ? (
            <ErrorState error={evals.error} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Eval ID</TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead>Criterion</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead className="text-right">Agreement</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {evals.data?.map((e) => (
                  <TableRow key={e.id}>
                    <TableCell>
                      <Link to={`/evals/${e.id}`} className="font-medium text-primary hover:underline">
                        {e.eval_id}
                      </Link>
                    </TableCell>
                    <TableCell className="num text-muted-foreground">{e.version}</TableCell>
                    <TableCell className="max-w-sm truncate text-muted-foreground" title={e.criterion_description}>
                      {e.criterion_description}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{e.evaluator_type.replace(/_/g, " ")}</TableCell>
                    <TableCell className="text-muted-foreground">{e.owner_team}</TableCell>
                    <TableCell className="num">
                      {e.last_judge_human_agreement != null ? formatPct(e.last_judge_human_agreement, 0) : "—"}
                    </TableCell>
                    <TableCell><ReviewStatusBadge status={e.review_status} /></TableCell>
                  </TableRow>
                ))}
                {evals.data?.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                      No evals match these filters.
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

function CreateEvalDialog() {
  const [open, setOpen] = React.useState(false);
  const create = useCreateEval();
  const [form, setForm] = React.useState<EvalCreate>({
    eval_id: "",
    version: "1.0.0",
    criterion_description: "",
    evaluator_type: "llm_as_judge",
    prompt_template: "Criterion: {criterion}\nInput: {input}\nOutput: {output}\nReturn JSON with verdict, score, reasoning, passed.",
    agreement_threshold: 0.75,
    owner_team: "",
    owner_email: "",
  });
  const set = (k: keyof EvalCreate, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    create.mutate(form, { onSuccess: () => setOpen(false) });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4" /> Create New Eval
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Eval</DialogTitle>
        </DialogHeader>
        <form onSubmit={submit} className="grid gap-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="eval_id">Eval ID</Label>
              <Input id="eval_id" required placeholder="refund_policy_compliance" value={form.eval_id} onChange={(e) => set("eval_id", e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="version">Version</Label>
              <Input id="version" value={form.version ?? ""} onChange={(e) => set("version", e.target.value)} />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="criterion">Criterion</Label>
            <Textarea id="criterion" value={form.criterion_description ?? ""} onChange={(e) => set("criterion_description", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label>Evaluator type</Label>
              <Select
                value={form.evaluator_type ?? "llm_as_judge"}
                onValueChange={(v) => set("evaluator_type", v)}
                options={EVALUATOR_TYPES.map((t) => ({ label: t.replace(/_/g, " "), value: t }))}
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="threshold">Agreement threshold</Label>
              <Input
                id="threshold"
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={form.agreement_threshold ?? 0.75}
                onChange={(e) => set("agreement_threshold", Number(e.target.value))}
              />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="tpl">Prompt template</Label>
            <Textarea id="tpl" className="font-mono text-xs" rows={5} value={form.prompt_template ?? ""} onChange={(e) => set("prompt_template", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="oteam">Owner team</Label>
              <Input id="oteam" value={form.owner_team ?? ""} onChange={(e) => set("owner_team", e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="oemail">Owner email</Label>
              <Input id="oemail" type="email" value={form.owner_email ?? ""} onChange={(e) => set("owner_email", e.target.value)} />
            </div>
          </div>
          {create.isError && <ErrorState error={create.error} />}
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? "Creating…" : "Create eval (as draft)"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
