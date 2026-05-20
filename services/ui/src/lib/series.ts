import type { EvalResult } from "@/api/types";
import { verdictTone } from "@/lib/verdict";

export interface DayPoint {
  day: string; // YYYY-MM-DD
  label: string; // e.g. "May 14"
  passRate: number;
  avgScore: number;
  count: number;
}

function dayKey(iso: string): string {
  return iso.slice(0, 10);
}

/** Bucket eval results into per-day pass-rate + avg-score over the last `days`. */
export function dailyPassRate(results: EvalResult[], days = 7): DayPoint[] {
  const buckets = new Map<string, { pass: number; total: number; scoreSum: number }>();

  // Seed empty buckets for each of the last `days` days so the chart is contiguous.
  const today = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    buckets.set(d.toISOString().slice(0, 10), { pass: 0, total: 0, scoreSum: 0 });
  }

  for (const r of results) {
    if (!r.evaluated_at) continue;
    const key = dayKey(r.evaluated_at);
    const b = buckets.get(key);
    if (!b) continue; // outside the window
    b.total += 1;
    b.scoreSum += r.score ?? 0;
    if (verdictTone(r.verdict) === "pass") b.pass += 1;
  }

  return Array.from(buckets.entries()).map(([day, b]) => ({
    day,
    label: new Date(`${day}T00:00:00`).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    }),
    passRate: b.total ? b.pass / b.total : 0,
    avgScore: b.total ? b.scoreSum / b.total : 0,
    count: b.total,
  }));
}
