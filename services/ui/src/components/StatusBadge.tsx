import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { CRITICALITY_CLASSES, REVIEW_STATUS_CLASSES } from "@/lib/verdict";

export function ReviewStatusBadge({ status }: { status: string }) {
  return (
    <Badge className={cn(REVIEW_STATUS_CLASSES[status] ?? REVIEW_STATUS_CLASSES.draft)}>
      {status.replace(/_/g, " ")}
    </Badge>
  );
}

export function CriticalityBadge({ criticality }: { criticality: string }) {
  return (
    <Badge className={cn(CRITICALITY_CLASSES[criticality] ?? CRITICALITY_CLASSES.low)}>
      {criticality}
    </Badge>
  );
}
