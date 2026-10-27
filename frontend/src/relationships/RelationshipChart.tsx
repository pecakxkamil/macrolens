import { tText, tLabel, getLocale } from "../i18n/language";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { RelationshipKey, RelationshipResponse } from "../api/macrolens";
import { relationshipAxisPlan, relationshipAxisDomain, isIsmPmiLevel, isIsmPmiPair, shortUnit } from "./relationshipAxes";
import { relationshipChartRows } from "./relationshipData";

export type ComparisonMode = "actual" | "indexed";

const colors: Record<RelationshipKey, string> = {
  left: "#83a9d5",
  right: "#d9af75",
  third: "#b6a2d8",
};



export function RelationshipChart({ response, labels, mode }: {
  response: RelationshipResponse;
  labels: Record<RelationshipKey, string>;
  mode: ComparisonMode;
}) {
  const numberFormat = new Intl.NumberFormat(getLocale(), { maximumFractionDigits: 2 });
  const rows = relationshipChartRows(response);
  const indexed = mode === "indexed";
  const showPmiReference = !indexed && isIsmPmiPair(response.indicators);
  const domainRows = showPmiReference ? [...rows, { [response.indicators[0].key]: 50 }] : rows;
  const axisUnit = (key: RelationshipKey) => {
    const indicator = response.indicators.find(item => item.key === key)!;
    return tText(isIsmPmiLevel(indicator) ? "points" : shortUnit(indicator.unit));
  };
  const { axes, axisFor } = relationshipAxisPlan(response.indicators, mode);

  return (
    <>
      <div className="relationship-chart-legend" aria-label={tLabel("Chart series")}>
        {response.indicators.map((indicator) => <span key={indicator.key}>
          <span className="relationship-chart-legend__swatch" style={{ backgroundColor: colors[indicator.key] }} />
          {tText(labels[indicator.key])}{tText(indexed ? " · index" : ` · ${isIsmPmiLevel(indicator) ? "points" : shortUnit(indicator.unit)}`)}
        </span>)}
      </div>
      <div className="relationship-chart-plot" role="region" aria-label={tLabel("Aligned relationship time series chart")}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart accessibilityLayer data={rows} margin={{ top: 26, right: 8, left: 0, bottom: 6 }}>
            <CartesianGrid stroke="#2b3746" strokeDasharray="3 4" vertical={false} />
            <XAxis dataKey="period" minTickGap={28} tick={{ fill: "#9eacbd", fontSize: 11 }} axisLine={{ stroke: "#425165" }} tickLine={false} />
            {axes.map((axis) => <YAxis key={axis.id} yAxisId={axis.id} orientation={axis.orientation} width={indexed ? 58 : 60} tickFormatter={(value: number) => new Intl.NumberFormat(getLocale(), { notation: "compact", maximumFractionDigits: 2 }).format(value)} label={{ value: indexed ? "100" : axisUnit(axis.members[0]), position: "insideTop", offset: 0, dy: -18, fill: axis.members.length === 1 ? colors[axis.members[0]] : "#9eacbd", fontSize: 10 }} tick={{ fill: indexed || axis.members.length > 1 ? "#9eacbd" : colors[axis.members[0]], fontSize: 11 }} axisLine={false} tickLine={false} domain={relationshipAxisDomain(domainRows, axis.members, mode)} allowDataOverflow />)}
            {showPmiReference ? <ReferenceLine y={50} yAxisId={axisFor[response.indicators[0].key]} stroke="#708197" strokeOpacity={0.65} strokeDasharray="4 4" label={{ value: "50", position: "insideBottomRight", fill: "#9eacbd", fontSize: 10 }} /> : null}
            <Tooltip isAnimationActive={false} cursor={{ stroke: "#708197", strokeDasharray: "3 3" }} content={({ active, label, payload }) => {
              if (!active || !label || !payload?.length) return null;
              return <div className="chart-tooltip"><strong>{tText(String(label))}</strong>{payload.map((entry) => {
                const key = String(entry.dataKey).replace(/_index$/, "") as RelationshipKey;
                const indicator = response.indicators.find((item) => item.key === key);
                return indicator && typeof entry.value === "number" ? <div key={key} className="relationship-tooltip-row">
                  <span style={{ color: colors[key] }}>{tText(labels[key])}</span>
                  <b>{tText(numberFormat.format(entry.value))}{tText(indexed ? "" : indicator.unit === "percent" ? "%" : "")}</b>
                  <small>{tText("Source observation")}: {String(entry.payload?.[`${key}_date`] ?? "\u2014")}</small>
                </div> : null;
              })}</div>;
            }} />
            {response.indicators.map((indicator) => <Line
              key={indicator.key}
              yAxisId={axisFor[indicator.key]}
              type="linear"
              dataKey={indexed ? `${indicator.key}_index` : indicator.key}
              name={tLabel(labels[indicator.key])}
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
