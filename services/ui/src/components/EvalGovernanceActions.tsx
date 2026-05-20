import * as React from "react";

import { useAttachCalibration, useCalibrationSets, useEvalAction } from "@/api/hooks";
import type { Eval } from "@/api/types";
import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
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

const EDITABLE = new Set(["draft", "in_review"]);

/**
 * Renders the governance transitions available for an eval's current state and
 * surfaces guard failures (e.g. approval below agreement threshold) inline.
 * Extracted from the page so it can be unit-tested in isolation.
 */
export function EvalGovernanceActions({ ev }: { ev: Eval }) {
  const action = useEvalAction(ev.id);
  const attach = useAttachCalibration(ev.id);
  const calibrationSets = useCalibrationSets();

  const [approver, setApprover] = React.useState("");
  const [calId, setCalId] = React.useState("");
  const [approveOpen, setApproveOpen] = React.useState(false);

  const errMessage = (e: unknown) =>
    e instanceof ApiError ? e.message : e instanceof Error ? e.message : null;

  return (
    <div className="space-y-3" data-testid="eval-governance-actions">
      <div className="flex flex-wrap items-center gap-2">
        {ev.review_status === "draft" && (
          <Button
            onClick={() => action.mutate({ action: "submit-for-review", body: { actor: "ui" } })}
            disabled={action.isPending}
          >
            Submit for review
          </Button>
        )}

        {ev.review_status === "in_review" && (
          <Dialog open={approveOpen} onOpenChange={setApproveOpen}>
            <DialogTrigger asChild>
              <Button>Approve</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Approve {ev.eval_id}</DialogTitle>
              </DialogHeader>
              <div className="grid gap-3">
                <p className="text-sm text-muted-foreground">
                  Approval requires a calibration set with judge/human agreement ≥{" "}
                  {(ev.agreement_threshold * 100).toFixed(0)}%. Current:{" "}
                  {ev.last_judge_human_agreement != null
                    ? `${(ev.last_judge_human_agreement * 100).toFixed(0)}%`
                    : "not measured"}
                  .
                </p>
                <div className="grid gap-1.5">
                  <Label htmlFor="approver">Approver email</Label>
                  <Input
                    id="approver"
                    type="email"
                    placeholder="approver@example.com"
                    value={approver}
                    onChange={(e) => setApprover(e.target.value)}
                  />
                </div>
                {action.isError && (
                  <p className="text-sm text-destructive" role="alert">
                    {errMessage(action.error)}
                  </p>
                )}
                <Button
                  disabled={!approver || action.isPending}
                  onClick={() =>
                    action.mutate(
                      { action: "approve", body: { approver_email: approver, actor: "ui" } },
                      { onSuccess: () => setApproveOpen(false) },
                    )
                  }
                >
                  {action.isPending ? "Approving…" : "Confirm approval"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        )}

        {ev.review_status === "approved" && (
          <Button
            variant="destructive"
            onClick={() => action.mutate({ action: "deprecate", body: { actor: "ui" } })}
            disabled={action.isPending}
          >
            Deprecate
          </Button>
        )}

        {(ev.review_status === "deprecated" || ev.review_status === "expired") && (
          <span className="text-sm text-muted-foreground">
            This eval is {ev.review_status} and immutable. Create a new version to change it.
          </span>
        )}
      </div>

      {EDITABLE.has(ev.review_status) && (
        <div className="flex flex-wrap items-end gap-2 rounded-md border bg-muted/30 p-3">
          <div className="grid gap-1.5">
            <Label>Attach calibration set</Label>
            <Select
              value={calId}
              onValueChange={setCalId}
              placeholder="Select a calibration set"
              options={(calibrationSets.data ?? []).map((c) => ({ label: c.name, value: c.id }))}
            />
          </div>
          <Button
            variant="secondary"
            disabled={!calId || attach.isPending}
            onClick={() => attach.mutate(calId)}
          >
            {attach.isPending ? "Attaching…" : "Run agreement test"}
          </Button>
          {attach.isError && (
            <p className="text-sm text-destructive" role="alert">
              {errMessage(attach.error)}
            </p>
          )}
        </div>
      )}

      {action.isError && ev.review_status !== "in_review" && (
        <p className="text-sm text-destructive" role="alert">
          {errMessage(action.error)}
        </p>
      )}
    </div>
  );
}
