import { useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ChartDefinition } from "./chartDefinitions";
import type { ChartRow } from "./chartData";
import { formatChartDate, formatChartValue } from "./chartFormat";

interface TooltipEntry {
  dataKey?: string | number;
  value?: number | string;
  color?: string;
}

export function TimeSeriesChart({ definition, rows }: { definition: ChartDefinition; rows: ChartRow[] }) {
  const [hidden, setHidden] = useState<string[]>([]);
  const visible = definition.series.filter((series) => !hidden.includes(series.id));

  return (
    <>
      <div className="chart-legend" role="group" aria-label={`${definition.title} series visibility`}>
        {definition.series.map((series) => {
          const isVisible = !hidden.includes(series.id);
          const latest = [...rows].reverse().find((row) => typeof row[series.id] === "number");
          return (
            <button
              key={series.id}
              type="button"
              className={`chart-legend__button${isVisible ? " is-active" : ""}`}
              aria-pressed={isVisible}
              aria-label={`${isVisible ? "Hide" : "Show"} ${series.label}`}
              onClick={() => setHidden((current) => current.includes(series.id)
                ? current.filter((id) => id !== series.id) : [...current, series.id])}
            >
              <span className="chart-legend__swatch" style={{ backgroundColor: series.color }} />
              <span>{series.label}</span>
              {latest ? <span className="chart-legend__latest">{formatChartValue(latest[series.id] as number, definition.unit)} · {formatChartDate(latest.observation_date, definition)}</span> : null}
            </button>
          );
        })}
      </div>
      {visible.length === 0 ? <p className="chart-state">Select a series above to display it.</p> : (
        <div className="chart-plot" role="region" aria-label={`${definition.title} time series chart`}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart accessibilityLayer data={rows} margin={{ top: 12, right: 12, left: 2, bottom: 6 }}>
              <CartesianGrid stroke="#2b3746" strokeDasharray="3 4" vertical={false} />
              <XAxis dataKey="observation_date" tickFormatter={(value: string) => formatChartDate(value, definition)} minTickGap={30} tick={{ fill: "#9eacbd", fontSize: 11 }} axisLine={{ stroke: "#425165" }} tickLine={false} />
              <YAxis width={64} tickFormatter={(value: number) => formatChartValue(value, definition.unit, true)} tick={{ fill: "#9eacbd", fontSize: 11 }} axisLine={false} tickLine={false} domain={["auto", "auto"]} />
              {definition.referenceLine !== undefined ? <ReferenceLine y={definition.referenceLine} stroke="#8795a8" strokeDasharray="4 4" /> : null}
              <Tooltip
                isAnimationActive={false}
                cursor={{ stroke: "#708197", strokeDasharray: "3 3" }}
                content={({ active, label, payload }) => {
                  if (!active || !label || !payload?.length) return null;
                  return (
                    <div className="chart-tooltip">
                      <strong>{formatChartDate(String(label), definition)}</strong>
                      {(payload as readonly TooltipEntry[]).map((entry) => {
                        const series = definition.series.find((item) => item.id === entry.dataKey);
                        return series && typeof entry.value === "number" ? (
                          <div key={series.id}><span style={{ color: entry.color }}>{series.label}</span><b>{formatChartValue(entry.value, definition.unit)}</b></div>
                        ) : null;
                      })}
                    </div>
                  );
                }}
              />
              {visible.map((series) => <Line key={series.id} type="linear" dataKey={series.id} name={series.label} stroke={series.color} strokeWidth={2} dot={false} activeDot={{ r: 4 }} connectNulls={false} isAnimationActive={false} />)}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </>
  );
}
