import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { MarketComparisonResponse, MarketComparisonRow, MarketDisplayMode } from "../api/macrolens";
import { formatNumber } from "../format";

const colors: Record<string, string> = { NASDAQCOM: "#86b6d8", CBBTCUSD: "#c0a1dc" };
const longDate = (day: string) => new Intl.DateTimeFormat("en-US", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" }).format(new Date(`${day}T00:00:00Z`));

export function MarketTooltip({ row, response, mode }: { row: MarketComparisonRow; response: MarketComparisonResponse; mode: MarketDisplayMode }) {
  return <div className="chart-tooltip market-tooltip">
    <strong>{longDate(row.as_of_date)}</strong>
    <div><span>Macro Conditions Index</span><b>{row.mci === null ? "Unavailable" : `${formatNumber(row.mci, 1)} / 100`}</b></div>
    <p>{response.macro_history_type === "point_in_time" ? "PIT as of" : "Current-vintage month-end"} {longDate(row.as_of_date)}</p>
    {response.series.filter((series) => series.series_id !== "MCI").map((series) => {
      const value = row[series.series_id]; const indexed = row[`${series.series_id}_indexed`];
      return <section key={series.series_id}>
        <b style={{ color: colors[series.series_id] }}>{series.name}</b>
        {mode === "indexed" ? <p>Indexed: {typeof indexed === "number" ? formatNumber(indexed, 1) : "Unavailable"}</p> : null}
        <p>Actual: {typeof value === "number" ? `${formatNumber(value)} ${series.unit}` : "Unavailable"}</p>
        <p>Market observation: {typeof row[`${series.series_id}_observation_date`] === "string" ? longDate(String(row[`${series.series_id}_observation_date`])) : "Unavailable"}</p>
      </section>;
    })}
  </div>;
}

export function MarketComparisonChart({ response, mode }: { response: MarketComparisonResponse; mode: MarketDisplayMode }) {
  const assets = response.series.filter((series) => series.series_id !== "MCI");
  return <>
    <div className="relationship-chart-legend" aria-label="Comparison chart series">
      <span><i style={{ background: "#dce8f8" }} />{response.macro_history_type === "point_in_time" ? "Point-in-time MCI" : "Current-vintage MCI"} / 100</span>
      {assets.map((asset) => <span key={asset.series_id}><i style={{ background: colors[asset.series_id] }} />{asset.name} / {mode === "indexed" ? "indexed, base = 100" : asset.unit}</span>)}
    </div>
    <div className="market-chart-scroll"><div className="market-chart" role="region" aria-label="Macro and market historical comparison chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart accessibilityLayer data={response.rows} margin={{ top: 20, right: 22, bottom: 20, left: 12 }}>
          <CartesianGrid stroke="#2b3746" strokeDasharray="3 4" vertical={false} />
          <XAxis dataKey="as_of_date" tickFormatter={(day: string) => day.slice(0, 7)} minTickGap={35} tick={{ fill: "#9eacbd", fontSize: 11 }} />
          <YAxis yAxisId="mci" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} width={65} allowDataOverflow tick={{ fill: "#b7c6d8", fontSize: 11 }} label={{ value: "MCI (0-100)", angle: -90, position: "insideLeft", fill: "#b7c6d8", fontSize: 11 }} />
          {mode === "indexed" ? <YAxis yAxisId="assets" orientation="right" width={80} domain={["auto", "auto"]} tick={{ fill: "#9eacbd", fontSize: 11 }} label={{ value: "Assets (base = 100)", angle: 90, position: "insideRight", fill: "#9eacbd", fontSize: 11 }} />
            : assets.map((asset) => <YAxis key={asset.series_id} yAxisId={asset.series_id} orientation="right" width={90} domain={["auto", "auto"]} tickFormatter={(value: number) => new Intl.NumberFormat("en-US", { notation: "compact" }).format(value)} tick={{ fill: colors[asset.series_id], fontSize: 11 }} label={{ value: asset.unit, angle: 90, position: "insideRight", fill: colors[asset.series_id], fontSize: 11 }} />)}
          <Tooltip isAnimationActive={false} content={({ active, label }) => {
            const row = response.rows.find((item) => item.as_of_date === label);
            return active && row ? <MarketTooltip row={row} response={response} mode={mode} /> : null;
          }} />
          <Line yAxisId="mci" dataKey="mci" name={response.macro_history_type === "point_in_time" ? "PIT MCI" : "Current-vintage MCI"} stroke="#dce8f8" strokeWidth={3} type="linear" dot={false} connectNulls={false} isAnimationActive={false} />
          {assets.map((asset) => <Line key={asset.series_id} yAxisId={mode === "indexed" ? "assets" : asset.series_id} dataKey={mode === "indexed" ? `${asset.series_id}_indexed` : asset.series_id} name={asset.name} stroke={colors[asset.series_id]} strokeWidth={2} type="linear" dot={false} connectNulls={false} isAnimationActive={false} />)}
        </LineChart>
      </ResponsiveContainer>
    </div></div>
  </>;
}
