import * as React from "react";

import { LocalTime } from "@/components/LocalTime";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useAgents, useChangeEvents } from "@/api/hooks";

const EVENT_TYPES = [
  "model_version_change",
  "prompt_change",
  "routing_change",
  "tool_change",
  "agent_lifecycle",
  "eval_lifecycle",
];

function DiffView({ before, after }: { before: unknown; after: unknown }) {
  return (
    <div className="grid grid-cols-2 gap-2 text-xs">
      <div className="rounded-md border border-verdict-fail/30 bg-verdict-fail/5 p-2">
        <div className="mb-1 font-medium text-verdict-fail">before</div>
        <pre className="overflow-auto font-mono">{JSON.stringify(before ?? {}, null, 2)}</pre>
      </div>
      <div className="rounded-md border border-verdict-pass/30 bg-verdict-pass/5 p-2">
        <div className="mb-1 font-medium text-verdict-pass">after</div>
        <pre className="overflow-auto font-mono">{JSON.stringify(after ?? {}, null, 2)}</pre>
      </div>
    </div>
  );
}

export function Changes() {
  const [eventType, setEventType] = React.useState("");
  const [actor, setActor] = React.useState("");

  const params: Record<string, unknown> = { limit: 200 };
  if (eventType) params.event_type = eventType;
  if (actor) params.actor = actor;

  const changes = useChangeEvents(params);
  const agents = useAgents();
  const agentById = new Map((agents.data ?? []).map((a) => [a.id, a]));

  return (
    <div>
      <PageHeader
        title="Change Events"
        description="Model, prompt, routing, tool, and lifecycle changes captured from the gateway."
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <Select
          value={eventType}
          onValueChange={setEventType}
          placeholder="All event types"
          options={EVENT_TYPES.map((t) => ({ label: t.replace(/_/g, " "), value: t }))}
        />
        <Input
          placeholder="Filter by actor…"
          value={actor}
          onChange={(e) => setActor(e.target.value)}
          className="w-48"
        />
      </div>

      {changes.isLoading ? (
        <LoadingRows rows={5} />
      ) : changes.isError ? (
        <ErrorState error={changes.error} />
      ) : !changes.data?.length ? (
        <EmptyState message="No change events match these filters." />
      ) : (
        <div className="space-y-3">
          {changes.data.map((c) => (
            <Card key={c.id}>
              <CardContent className="p-4">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge className="bg-muted text-muted-foreground border-border">
                    {c.event_type.replace(/_/g, " ")}
                  </Badge>
                  <span className="text-sm font-medium">{c.reason ?? ""}</span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {c.actor} · <LocalTime iso={c.timestamp} />
                    {c.agent_id && agentById.get(c.agent_id) ? ` · ${agentById.get(c.agent_id)!.name}` : ""}
                  </span>
                </div>
                <DiffView before={c.before} after={c.after} />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
