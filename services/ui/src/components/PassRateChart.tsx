import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { DayPoint } from "@/lib/series";

export function PassRateChart({ data, height = 240 }: { data: DayPoint[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id="passGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="hsl(142 71% 45%)" stopOpacity={0.4} />
            <stop offset="95%" stopColor="hsl(142 71% 45%)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 12 }} stroke="hsl(215 16% 47%)" />
        <YAxis
          domain={[0, 1]}
          tickFormatter={(v) => `${Math.round(v * 100)}%`}
          tick={{ fontSize: 12 }}
          stroke="hsl(215 16% 47%)"
        />
        <Tooltip
          formatter={(v: number, name) =>
            name === "passRate" ? [`${(v * 100).toFixed(1)}%`, "Pass rate"] : [v, name]
          }
          labelClassName="text-xs"
          contentStyle={{ fontSize: 12, borderRadius: 8 }}
        />
        <Area
          type="monotone"
          dataKey="passRate"
          stroke="hsl(142 71% 45%)"
          strokeWidth={2}
          fill="url(#passGrad)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
