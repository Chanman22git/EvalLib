import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { TONE_CLASSES, verdictTone } from "@/lib/verdict";

export function VerdictBadge({ verdict }: { verdict: string | null | undefined }) {
  const tone = verdictTone(verdict);
  return <Badge className={cn(TONE_CLASSES[tone])}>{verdict ?? "—"}</Badge>;
}
