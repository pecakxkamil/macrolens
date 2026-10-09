import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { MciDomainKey, MciHistoryObservation } from "../api/macrolens";

export const mciDomains: Array<{ key: MciDomainKey; label: string; color: string }> = [
  { key: "labor", label: "Labor", color: "#8eadd1" },
  { key: "inflation", label: "Inflation", color: "#b6a2d8" },
  { key: "growth", label: "Growth", color: "#b5c7de" },
  { key: "consumer", label: "Consumer", color: "#718baf" },
  { key: "housing", label: "Housing", color: "#a6a4bb" },
  { key: "financial_conditions", label: "Financial Conditions", color: "#7e9bb1" },
];

export function MciHistoryChart({ rows, visible }: { rows: MciHistoryObservation[]; visible: MciDomainKey[] }) {
  return <div className="mci-history-plot" role="region" aria-label="Macro Conditions Index historical line chart">
    <ResponsiveContainer width="100%" height="100%">
      <LineChart accessibilityLayer data={rows} margin={{ top: 15, right: 18, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="#2b3746" strokeDasharray="3 4" vertical={false} />
        <XAxis dataKey="observation_date" tickFormatter={(value: string) => value.slice(0, 7)} minTickGap={30} tick={{ fill: "#9eacbd", fontSize: 11 }} tickLine={false} />
        <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} allowDataOverflow width={40} tick={{ fill: "#9eacbd", fontSize: 11 }} tickLine={false} axisLine={false} />
        <ReferenceLine y={50} stroke="#7f8fa3" strokeDasharray="4 4" />
        <Tooltip isAnimationActive={false} content={({ active, label, payload }) => {
          if (!active || !payload?.length) return null;
          return <div className="chart-tooltip"><strong>{String(label)}</strong>{payload.map((entry) => typeof entry.value === "number" ? <div key={String(entry.dataKey)}>
            <span style={{ color: entry.color }}>{entry.name}</span><b>{entry.value.toFixed(1)} / 100</b>
          </div> : null)}</div>;
        }} />
        <Line type="linear" dataKey="mci" name="MCI" stroke="#dce8f8" strokeWidth={3} dot={false} connectNulls={false} isAnimationActive={false} />
        {mciDomains.filter((item) => visible.includes(item.key)).map((item, index) => <Line
          key={item.key} type="linear" dataKey={item.key} name={item.label} stroke={item.color}
          strokeDasharray={index % 2 ? "5 3" : undefined} strokeWidth={1.8}
          dot={false} connectNulls={false} isAnimationActive={false}
        />)}
      </LineChart>
    </ResponsiveContainer>
  </div>;
}
