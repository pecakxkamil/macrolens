import { tText, tLabel, getLocale } from "../i18n/language";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { fetchLeadLag, type LeadLagPair, type LeadLagResponse, type MarketAssetId, type MciHistoryMode } from "../api/macrolens";
import { formatNumber } from "../format";

export const lagLabel = (k: number) => k === 0 ? "0: same month" : k > 0 ? `+${k}: MCI precedes return` : `${k}: return precedes MCI`;
const number = (value: number | null) => value === null ? "Unavailable" : formatNumber(value, 3);
export function ScatterDetails({ pair }: { pair?: LeadLagPair }) {
  if (!pair) return null;
  return <div className="chart-tooltip"><strong>{tText(pair.asset_name)} {tText(" (")}{tText(pair.asset_id)}{tText(")")}</strong><p>{tText("MCI anchor month: ")}{tText(pair.anchor_date)}</p><p>{tText("Asset return month: ")}{tText(pair.return_date)}</p><p>{tText("Delta MCI: ")}{tText(formatNumber(pair.mci_change, 2))} {tText(" index points")}</p><p>{tText("Asset return: ")}{tText(formatNumber(pair.asset_return, 2))}{tText("%")}</p></div>;
}

export function LeadLagAnalysis({ macro, startDate }: { macro: MciHistoryMode; startDate?: string }) {
  const [asset, setAsset] = useState<MarketAssetId>("NASDAQCOM");
  const [lag, setLag] = useState(0);
  const [window, setWindow] = useState(24);
  const [retry, setRetry] = useState(0);
  const [result, setResult] = useState<{ key: string; data?: LeadLagResponse; error?: boolean }>();
  const key = `${asset}|${macro}|${startDate}|${window}|${retry}`;
  useEffect(() => {
    const controller = new AbortController();
    fetchLeadLag({ asset, macroHistoryType: macro, startDate, rollingWindow: window, signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setResult({ key, data }); })
      .catch(() => { if (!controller.signal.aborted) setResult({ key, error: true }); });
    return () => controller.abort();
  }, [key]);
  const response = result?.key === key ? result : undefined;
  const data = response?.data;
  const series = data?.assets.find((item) => item.asset_id === asset);
  const selected = series?.lags.find((item) => item.lag === lag);
  return <section className="market-chart-panel lead-lag-analysis" aria-label={tLabel("Lead / Lag Analysis")}>
    <h2>{tText("Lead / Lag Analysis")}</h2>
    <p><strong>{tText("Corr(delta MCI at t, asset return at t+k).")}</strong> {tText(" Positive lag: MCI change precedes return. Negative lag: return precedes MCI change. Zero: same month.")}</p>
    <p className="market-note">{tText("Uses the macro history and reporting range selected above. ")}{tText(macro === "point_in_time" ? "Point-in-time" : "Current-vintage")} {tText(" macro history.")}</p>
    <div className="market-controls">
      <label>{tText("Analysis asset ")}<select aria-label={tLabel("Analysis asset")} value={asset} onChange={(event) => setAsset(event.target.value as MarketAssetId)}><option value="NASDAQCOM">{tText("Nasdaq Composite")}</option><option value="CBBTCUSD">{tText("Bitcoin")}</option></select></label>
      <label>{tText("Lag (calendar months) ")}<select aria-label={tLabel("Lag (calendar months)")} value={lag} onChange={(event) => setLag(Number(event.target.value))}>{Array.from({ length: 13 }, (_, i) => i - 6).map((k) => <option key={k} value={k}>{tText(lagLabel(k))}</option>)}</select></label>
      <label>{tText("Rolling window ")}<select aria-label={tLabel("Rolling window")} value={window} onChange={(event) => setWindow(Number(event.target.value))}><option value={24}>{tText("24 calendar months")}</option><option value={36}>{tText("36 calendar months")}</option></select></label>
    </div>
    {!response ? <p className="loading-panel">{tText("Loading lead/lag analysis...")}</p> : response.error ? <div role="alert"><p>{tText("Unable to load lead/lag analysis.")}</p><button onClick={() => setRetry((value) => value + 1)}>{tText("Retry analysis")}</button></div> : data && selected && series ? <>
      <p>{tText("Selected lag: ")}<strong>{tText(lagLabel(lag))}</strong>{tText(". Pearson r: ")}{tText(number(selected.correlation))}{tText(". N: ")}{tText(selected.n)}{tText(". First valid anchor: ")}{tText(selected.first_anchor_date ?? "Unavailable")}{tText(". Last valid anchor: ")}{tText(selected.last_anchor_date ?? "Unavailable")}{tText(".")}</p>
      <p className="market-note">{tText("Missing pairs: ")}{tText(selected.missing_anchor_count)} {tText(" of ")}{tText(data.anchor_count)} {tText(" anchor months. Missing MCI changes: ")}{tText(data.coverage.missing_mci_change_dates.length)}{tText(". Prices older than ")}{tText(data.maximum_price_age_days)} {tText(" days are unavailable.")}</p>
      <h3>{tText("Correlation across all 13 lags")}</h3>
      <div className="lead-lag-chart" aria-label={tLabel("Lag correlation bar chart")}><ResponsiveContainer width="100%" height={280}><BarChart data={series.lags} margin={{ bottom: 35, left: 10, right: 20 }}><CartesianGrid stroke="#29384a" /><XAxis dataKey="lag" interval={0} tickFormatter={(k: number) => k > 0 ? `+${k}` : String(k)} label={tLabel({ value: "Lag k: + MCI precedes return / - return precedes MCI", position: "bottom" })} /><YAxis domain={[-1, 1]} tickFormatter={(value: number) => new Intl.NumberFormat(getLocale()).format(value)} /><ReferenceLine y={0} stroke="#728499" /><Tooltip content={({ payload }) => { const row = payload?.[0]?.payload; return row ? <div className="chart-tooltip">{tText(lagLabel(row.lag))}<p>{tText("Pearson r: ")}{tText(number(row.correlation))}</p><p>{tText("N: ")}{tText(row.n)}</p></div> : null; }} /><Bar dataKey="correlation" fill="#94a9c5" /></BarChart></ResponsiveContainer></div>
      <details><summary>{tText("All lag correlations and sample counts")}</summary><table><thead><tr><th>{tText("Lag k")}</th><th>{tText("Pearson r")}</th><th>{tText("N")}</th></tr></thead><tbody>{series.lags.map((item) => <tr key={item.lag}><td>{tText(lagLabel(item.lag))}</td><td>{tText(number(item.correlation))}</td><td>{tText(item.n)}</td></tr>)}</tbody></table></details>
      <h3>{tText("Rolling stability: ")}{tText(window)} {tText(" calendar months")}</h3>
      {!selected.rolling.some((point) => point.correlation !== null) ? <p className="chart-state">{tText("No complete rolling windows with nonzero variance. Missing months remain gaps.")}</p> : <div className="lead-lag-chart"><ResponsiveContainer width="100%" height={280}><LineChart data={selected.rolling}><CartesianGrid stroke="#29384a" /><XAxis dataKey="anchor_date" /><YAxis domain={[-1, 1]} tickFormatter={(value: number) => new Intl.NumberFormat(getLocale()).format(value)} /><Tooltip formatter={(value) => typeof value === "number" ? new Intl.NumberFormat(getLocale(), { maximumFractionDigits: 3 }).format(value) : value ?? "-"} /><Line name={tLabel("Pearson r")} dataKey="correlation" stroke="#a8b8ce" dot={false} connectNulls={false} isAnimationActive={false} /></LineChart></ResponsiveContainer></div>}
      <h3>{tText("Delta MCI versus lagged monthly return")}</h3>
      {!selected.pairs.length ? <p className="chart-state">{tText("No valid paired observations for this lag and range.")}</p> : <div className="lead-lag-chart"><ResponsiveContainer width="100%" height={300}><ScatterChart margin={{ bottom: 35, left: 25, right: 25 }}><CartesianGrid stroke="#29384a" /><XAxis type="number" tickFormatter={(value: number) => new Intl.NumberFormat(getLocale()).format(value)} dataKey="mci_change" name={tLabel("Delta MCI")} label={tLabel({ value: "Delta MCI at t (index points)", position: "bottom" })} /><YAxis type="number" tickFormatter={(value: number) => new Intl.NumberFormat(getLocale()).format(value)} dataKey="asset_return" name={tLabel("Monthly return")} label={tLabel({ value: `Return at t${lag >= 0 ? "+" : ""}${lag} (%)`, angle: -90, position: "insideLeft" })} /><Tooltip content={({ payload }) => <ScatterDetails pair={payload?.[0]?.payload} />} /><Scatter data={selected.pairs} fill="#94a9c5" /></ScatterChart></ResponsiveContainer></div>}
      {selected.correlation === null ? <p className="market-note">{tText("Correlation unavailable: at least three valid pairs and nonzero variance are required.")}</p> : null}
      <details open><summary>{tText("Lead/lag methodology and limitations")}</summary>
        <p>{tText("Delta MCI = MCI_t - MCI_(t-1), in index points. Return = 100 * (P_t / P_(t-1) - 1), in percent. Prices are not correlated with MCI levels in this analysis.")}</p>
        <p>{tText("Pairing uses actual calendar months, never sequential row shifting or nearest-month matching. Missing macro or price months invalidate the change or return; no interpolation or multi-month bridging.")}</p>
        <p>{tText(data.boundary_policy)}</p><p>{tText(data.rolling_policy)}</p>
        <p>{tText("Positive-lag rolling correlations use market returns after the window anchor: retrospective analysis, not an investable signal. Full calendar windows are required; missing months produce null correlations.")}</p>
        <p>{tText(data.limitations)}</p><p>{tText("All 13 lags are displayed consistently; none is selected as an optimal lag. Correlation is statistical, not causal. Same-month correlation is not a prediction.")}</p>
      </details>
    </> : <p className="chart-state">{tText("No analysis coverage is available.")}</p>}
  </section>;
}
