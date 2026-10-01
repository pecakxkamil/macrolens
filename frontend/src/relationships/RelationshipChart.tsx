import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { RelationshipKey, RelationshipResponse } from "../api/macrolens";
import { relationshipAxisPlan } from "./relationshipAxes";
import { relationshipChartRows } from "./relationshipData";

export type ComparisonMode = "actual" | "indexed";

const colors: Record<RelationshipKey, string> = {
  left: "#83a9d5",
  right: "#d9af75",
  third: "#b6a2d8",
};

const numberFormat = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });

export function RelationshipChart({ response, labels, mode }: {
  response: RelationshipResponse;
  labels: Record<RelationshipKey, string>;
  mode: ComparisonMode;
}) {
  const rows = relationshipChartRows(response);
  const indexed = mode === "indexed";
  const { axes, axisFor } = relationshipAxisPlan(response.indicators, mode);

  return (
    <>
      <div className="relationship-chart-legend" aria-label="Chart series">
        {response.indicators.map((indicator) => <span key={indicator.key}>
          <span className="relationship-chart-legend__swatch" style={{ backgroundColor: colors[indicator.key] }} />
          {labels[indicator.key]}{indexed ? " · index" : ` · ${indicator.unit}`}
        </span>)}
      </div>
      <div className="relationship-chart-plot" role="region" aria-label="Aligned relationship time series chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart accessibilityLayer data={rows} margin={{ top: 12, right: 8, left: 0, bottom: 6 }}>
            <CartesianGrid stroke="#2b3746" strokeDasharray="3 4" vertical={false} />
            <XAxis dataKey="period" minTickGap={28} tick={{ fill: "#9eacbd", fontSize: 11 }} axisLine={{ stroke: "#425165" }} tickLine={false} />
            {axes.map((axis) => <YAxis key={axis.id} yAxisId={axis.id} orientation={axis.orientation} width={indexed ? 58 : 60} tickFormatter={(value: number) => numberFormat.format(value)} tick={{ fill: indexed || axis.members.length > 1 ? "#9eacbd" : colors[axis.members[0]], fontSize: 11 }} axisLine={false} tickLine={false} domain={["auto", "auto"]} />)}
            <Tooltip isAnimationActive={false} cursor={{ stroke: "#708197", strokeDasharray: "3 3" }} content={({ active, label, payload }) => {
              if (!active || !label || !payload?.length) return null;
              return <div className="chart-tooltip"><strong>{String(label)}</strong>{payload.map((entry) => {
                const key = String(entry.dataKey).replace(/_index$/, "") as RelationshipKey;
                const indicator = response.indicators.find((item) => item.key === key);
                return indicator && typeof entry.value === "number" ? <div key={key}>
                  <span style={{ color: colors[key] }}>{labels[key]}</span>
                  <b>{numberFormat.format(entry.value)}{indexed ? "" : indicator.unit === "percent" ? "%" : ""}</b>
                </div> : null;
              })}</div>;
            }} />
            {response.indicators.map((indicator) => <Line
              key={indicator.key}
              yAxisId={axisFor[indicator.key]}
              type="linear"
              dataKey={indexed ? `${indicator.key}_index` : indicator.key}
              name={labels[indicator.key]}
              stroke={colors[indicator.key]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls={false}
              isAnimationActive={false}
            />)}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}
