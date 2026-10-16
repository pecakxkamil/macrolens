import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { fetchLeadLag, type LeadLagPair, type LeadLagResponse, type MarketAssetId, type MciHistoryMode } from "../api/macrolens";
import { formatNumber } from "../format";

export const lagLabel = (k: number) => k === 0 ? "0: same month" : k > 0 ? `+${k}: MCI precedes return` : `${k}: return precedes MCI`;
const number = (value: number | null) => value === null ? "Unavailable" : formatNumber(value, 3);
export function ScatterDetails({ pair }: { pair?: LeadLagPair }) {
  if (!pair) return null;
  return <div className="chart-tooltip"><strong>{pair.asset_name} ({pair.asset_id})</strong><p>MCI anchor month: {pair.anchor_date}</p><p>Asset return month: {pair.return_date}</p><p>Delta MCI: {formatNumber(pair.mci_change, 2)} index points</p><p>Asset return: {formatNumber(pair.asset_return, 2)}%</p></div>;
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
  return <section className="market-chart-panel lead-lag-analysis" aria-label="Lead / Lag Analysis">
    <h2>Lead / Lag Analysis</h2>
    <p><strong>Corr(delta MCI at t, asset return at t+k).</strong> Positive lag: MCI change precedes return. Negative lag: return precedes MCI change. Zero: same month.</p>
    <p className="market-note">Uses the macro history and reporting range selected above. {macro === "point_in_time" ? "Point-in-time" : "Current-vintage"} macro history.</p>
    <div className="market-controls">
      <label>Analysis asset <select aria-label="Analysis asset" value={asset} onChange={(event) => setAsset(event.target.value as MarketAssetId)}><option value="NASDAQCOM">Nasdaq Composite</option><option value="CBBTCUSD">Bitcoin</option></select></label>
      <label>Lag (calendar months) <select aria-label="Lag (calendar months)" value={lag} onChange={(event) => setLag(Number(event.target.value))}>{Array.from({ length: 13 }, (_, i) => i - 6).map((k) => <option key={k} value={k}>{lagLabel(k)}</option>)}</select></label>
      <label>Rolling window <select aria-label="Rolling window" value={window} onChange={(event) => setWindow(Number(event.target.value))}><option value={24}>24 calendar months</option><option value={36}>36 calendar months</option></select></label>
    </div>
    {!response ? <p className="loading-panel">Loading lead/lag analysis...</p> : response.error ? <div role="alert"><p>Unable to load lead/lag analysis.</p><button onClick={() => setRetry((value) => value + 1)}>Retry analysis</button></div> : data && selected && series ? <>
      <p>Selected lag: <strong>{lagLabel(lag)}</strong>. Pearson r: {number(selected.correlation)}. N: {selected.n}. First valid anchor: {selected.first_anchor_date ?? "Unavailable"}. Last valid anchor: {selected.last_anchor_date ?? "Unavailable"}.</p>
      <p className="market-note">Missing pairs: {selected.missing_anchor_count} of {data.anchor_count} anchor months. Missing MCI changes: {data.coverage.missing_mci_change_dates.length}. Prices older than {data.maximum_price_age_days} days are unavailable.</p>
      <h3>Correlation across all 13 lags</h3>
      <div className="lead-lag-chart" aria-label="Lag correlation bar chart"><ResponsiveContainer width="100%" height={280}><BarChart data={series.lags} margin={{ bottom: 35, left: 10, right: 20 }}><CartesianGrid stroke="#29384a" /><XAxis dataKey="lag" interval={0} tickFormatter={(k: number) => k > 0 ? `+${k}` : String(k)} label={{ value: "Lag k: + MCI precedes return / - return precedes MCI", position: "bottom" }} /><YAxis domain={[-1, 1]} /><ReferenceLine y={0} stroke="#728499" /><Tooltip content={({ payload }) => { const row = payload?.[0]?.payload; return row ? <div className="chart-tooltip">{lagLabel(row.lag)}<p>Pearson r: {number(row.correlation)}</p><p>N: {row.n}</p></div> : null; }} /><Bar dataKey="correlation" fill="#94a9c5" /></BarChart></ResponsiveContainer></div>
      <details><summary>All lag correlations and sample counts</summary><table><thead><tr><th>Lag k</th><th>Pearson r</th><th>N</th></tr></thead><tbody>{series.lags.map((item) => <tr key={item.lag}><td>{lagLabel(item.lag)}</td><td>{number(item.correlation)}</td><td>{item.n}</td></tr>)}</tbody></table></details>
      <h3>Rolling stability: {window} calendar months</h3>
      {!selected.rolling.some((point) => point.correlation !== null) ? <p className="chart-state">No complete rolling windows with nonzero variance. Missing months remain gaps.</p> : <div className="lead-lag-chart"><ResponsiveContainer width="100%" height={280}><LineChart data={selected.rolling}><CartesianGrid stroke="#29384a" /><XAxis dataKey="anchor_date" /><YAxis domain={[-1, 1]} /><Tooltip /><Line dataKey="correlation" stroke="#a8b8ce" dot={false} connectNulls={false} isAnimationActive={false} /></LineChart></ResponsiveContainer></div>}
      <h3>Delta MCI versus lagged monthly return</h3>
      {!selected.pairs.length ? <p className="chart-state">No valid paired observations for this lag and range.</p> : <div className="lead-lag-chart"><ResponsiveContainer width="100%" height={300}><ScatterChart margin={{ bottom: 35, left: 25, right: 25 }}><CartesianGrid stroke="#29384a" /><XAxis type="number" dataKey="mci_change" name="Delta MCI" label={{ value: "Delta MCI at t (index points)", position: "bottom" }} /><YAxis type="number" dataKey="asset_return" name="Monthly return" label={{ value: `Return at t${lag >= 0 ? "+" : ""}${lag} (%)`, angle: -90, position: "insideLeft" }} /><Tooltip content={({ payload }) => <ScatterDetails pair={payload?.[0]?.payload} />} /><Scatter data={selected.pairs} fill="#94a9c5" /></ScatterChart></ResponsiveContainer></div>}
      {selected.correlation === null ? <p className="market-note">Correlation unavailable: at least three valid pairs and nonzero variance are required.</p> : null}
      <details open><summary>Lead/lag methodology and limitations</summary>
        <p>Delta MCI = MCI_t - MCI_(t-1), in index points. Return = 100 * (P_t / P_(t-1) - 1), in percent. Prices are not correlated with MCI levels in this analysis.</p>
        <p>Pairing uses actual calendar months, never sequential row shifting or nearest-month matching. Missing macro or price months invalidate the change or return; no interpolation or multi-month bridging.</p>
        <p>{data.boundary_policy}</p><p>{data.rolling_policy}</p>
        <p>Positive-lag rolling correlations use market returns after the window anchor: retrospective analysis, not an investable signal. Full calendar windows are required; missing months produce null correlations.</p>
        <p>{data.limitations}</p><p>All 13 lags are displayed consistently; none is selected as an optimal lag. Correlation is statistical, not causal. Same-month correlation is not a prediction.</p>
      </details>
    </> : <p className="chart-state">No analysis coverage is available.</p>}
  </section>;
}
