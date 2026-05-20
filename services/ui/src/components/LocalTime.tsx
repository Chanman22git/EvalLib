import { formatLocal, utcTooltip } from "@/lib/format";

/** Timestamp in the user's local TZ with a UTC tooltip (FR-UI-2). */
export function LocalTime({ iso }: { iso: string | null | undefined }) {
  return (
    <time dateTime={iso ?? undefined} title={utcTooltip(iso)} className="whitespace-nowrap">
      {formatLocal(iso)}
    </time>
  );
}
