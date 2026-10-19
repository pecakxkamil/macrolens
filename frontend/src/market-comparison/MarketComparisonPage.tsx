import { tText, tLabel } from "../i18n/language";
import { useEffect, useRef, useState } from "react";
import { fetchMarketComparison, type MarketAssetId, type MarketComparisonResponse, type MarketDisplayMode, type MciHistoryMode } from "../api/macrolens";
import { rangeStartDate } from "../charts/chartData";
import { formatNumber } from "../format";
import { LeadLagAnalysis } from "./LeadLagAnalysis";
import { MarketComparisonChart } from "./MarketComparisonChart";

const choices: Array<{ id: MarketAssetId; name: string }> = [{ id: "NASDAQCOM", name: "Nasdaq Composite" }, { id: "CBBTCUSD", name: "Bitcoin" }];
const ranges = ["1Y", "3Y", "5Y", "10Y", "Max"] as const;
type Range = typeof ranges[number];
type LoadState = { status: "loading" } | { status: "error" } | { status: "ready"; data: MarketComparisonResponse };
const correlation = (value: number | null) => value === null ? "Unavailable" : `${value > 0 ? "+" : ""}${formatNumber(value, 2)}`;

export function MarketComparisonPage({ embedded = false }: { embedded?: boolean } = {}) {
  const Heading = embedded ? "h2" : "h1";
  const [macro, setMacro] = useState<MciHistoryMode>("point_in_time");
  const [assets, setAssets] = useState<MarketAssetId[]>(["NASDAQCOM"]);
  const [range, setRange] = useState<Range>("5Y");
  const [mode, setMode] = useState<MarketDisplayMode>("indexed");
  const [retry, setRetry] = useState(0);
  const [fallback, setFallback] = useState(false);
  const initialRange = useRef(true);
  const requestKey = `${macro}|${assets.join(",")}|${range}|${mode}|${retry}`;
  const [response, setResponse] = useState<{ key: string; state: LoadState }>({ key: "", state: { status: "loading" } });
  useEffect(() => {
    if (!assets.length) return;
    const controller = new AbortController();
    setResponse({ key: requestKey, state: { status: "loading" } });
    fetchMarketComparison({ assets, macroHistoryType: macro, mode,
      startDate: range === "Max" ? undefined : rangeStartDate(Number(range.slice(0, -1))), signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        if (initialRange.current) {
          initialRange.current = false;
          const fiveYearsAvailable = data.available_overlap_start !== null && data.available_overlap_start <= rangeStartDate(5);
          if (range === "5Y" && !fiveYearsAvailable) { setRange("Max"); setFallback(true); return; }
        }
        setResponse({ key: requestKey, state: { status: "ready", data } });
      }).catch(() => { if (!controller.signal.aborted) setResponse({ key: requestKey, state: { status: "error" } }); });
    return () => controller.abort();
  }, [requestKey]);
  const state = response.key === requestKey ? response.state : { status: "loading" } as const;
  return <main className="market-comparison-page">
    <header><p className="eyebrow">{tText("MacroLens")}</p><Heading>{tText("Macro-Market Analysis")}</Heading><p className="subtitle">{tText("Compare point-in-time macro conditions with historical market behavior.")}</p></header>
    <section className="research-question" aria-label={tLabel("Research question")}>
      <h3>{tText("How do macro conditions and their changes relate to Nasdaq and Bitcoin returns?")}</h3>
      <p>{tText("Compare monthly MCI levels and changes with market returns, then inspect lead/lag correlations and rolling windows below. Statistics describe only the selected sample; gaps and sample sizes remain visible.")}</p>
    </section>
    <div className="charts-notice">
      <strong>{tText(macro === "point_in_time" ? "Point-in-time MCI uses economic vintages available at each historical month-end." : "Current-vintage MCI uses today's stored revised values.")}</strong>
      <span>{tText("Descriptive comparison only. This is not a trading signal, forecasting model, backtest engine, or investment recommendation.")}</span>
      <span>{tText("Correlation describes historical co-movement. It does not imply causation or predictive power.")}</span>
    </div>
    <section className="market-controls" aria-label={tLabel("Market comparison controls")}>
      <div role="group" aria-label={tLabel("Macro history")} className="charts-range"><span>{tText("Macro history")}</span>{(["point_in_time", "current_vintage"] as const).map((value) => <button key={value} aria-pressed={macro === value} className={macro === value ? "is-active" : ""} onClick={() => setMacro(value)}>{tText(value === "point_in_time" ? "Point-in-time" : "Current-vintage")}</button>)}</div>
      <div role="group" aria-label={tLabel("Comparison range")} className="charts-range"><span>{tText("Range")}</span>{ranges.map((value) => <button key={value} aria-pressed={range === value} className={range === value ? "is-active" : ""} onClick={() => { initialRange.current = false; setRange(value); setFallback(false); }}>{tText(value)}</button>)}</div>
      <fieldset className="market-asset-controls"><legend>{tText("Assets")}</legend>{choices.map((asset) => <label key={asset.id}><input type="checkbox" checked={assets.includes(asset.id)} onChange={() => setAssets((previous) => previous.includes(asset.id) ? previous.filter((id) => id !== asset.id) : [...previous, asset.id])} />{tText(asset.name)}</label>)}</fieldset>
      <div role="group" aria-label={tLabel("Display mode")} className="charts-range">{(["indexed", "actual"] as const).map((value) => <button key={value} aria-pressed={mode === value} className={mode === value ? "is-active" : ""} onClick={() => setMode(value)}>{tText(value === "indexed" ? "MCI level + indexed assets" : "Actual values")}</button>)}</div>
      {fallback ? <p className="market-note">{tText("Less than five years of shared valid data; showing maximum available overlap.")}</p> : null}
    </section>
    {!assets.length ? <p className="chart-state">{tText("Select at least one asset to compare.")}</p> : state.status === "loading" ? <p className="loading-panel">{tText("Loading market comparison...")}</p> : state.status === "error" ? <div className="error-panel" role="alert"><p>{tText("Unable to load market comparison. Check the backend and refresh market data.")}</p><button onClick={() => setRetry((value) => value + 1)}>{tText("Retry comparison")}</button></div> : <>
      <section aria-label={tLabel("Historical comparison")} className="market-chart-panel"><h2>{tText(macro === "point_in_time" ? "Point-in-time MCI" : "Current-vintage MCI")} {tText(" and market assets")}</h2>
        <p className="market-note">{tText(mode === "indexed" ? "MCI remains on its native 0-100 axis. Assets share an indexed axis." : "MCI, Nasdaq index points, and Bitcoin USD use separate axes. Numeric magnitudes are not directly comparable.")}</p>
        {state.data.base_date ? <p>{tText("Common base date: ")}{tText(state.data.base_date)}{tText(". ")}{tText(assets.map((id) => `${choices.find((choice) => choice.id === id)?.name}: ${formatNumber(state.data.base_values[id])}`).join("; "))}{tText(". MCI is not rebased.")}</p> : null}
        {state.data.status === "insufficient_overlap" ? <p className="chart-state">{tText(state.data.message)}</p> : <MarketComparisonChart response={state.data} mode={mode} />}
      </section>
      <section aria-label={tLabel("Relationship statistics")}><h2>{tText("Relationship statistics")}</h2><p className="market-note">{tText("Contemporaneous monthly relationships. At least ")}{tText(state.data.minimum_correlation_observations)} {tText(" paired observations and nonzero variance are required.")}</p>
        <div className="market-statistics">{state.data.statistics.map((item) => {
          const asset = state.data.series.find((series) => series.series_id === item.asset_id)!;
          const last = state.data.rows[state.data.rows.length - 1];
          const monthlyReturn = last?.[`${item.asset_id}_return_1m`];
          return <article key={item.asset_id} aria-label={tLabel(`${asset.name} relationship statistics`)}><h3>{tText(asset.name)}</h3>
            <p>{tText("Latest aligned monthly return: ")}<b>{tText(typeof monthlyReturn === "number" ? `${formatNumber(monthlyReturn, 2)}%` : "Unavailable")}</b></p>
            <div><h4>{tText("MCI level vs monthly return")}</h4><p>{tText("Correlation: ")}<b>{tText(correlation(item.mci.correlation))}</b></p><p>{tText("Observations: ")}{tText(item.mci.overlapping_observations)}</p></div>
            <div><h4>{tText("Monthly MCI change vs monthly return")}</h4><p>{tText("Correlation: ")}<b>{tText(correlation(item.mci_change.correlation))}</b></p><p>{tText("Observations: ")}{tText(item.mci_change.overlapping_observations)}</p></div>
            <details><summary>{tText("Variable definitions")}</summary><p>{tText(item.mci.variable_definitions.macro)}</p><p>{tText(item.mci_change.variable_definitions.macro)}</p><p>{tText(item.mci.variable_definitions.market)}</p></details>
          </article>;
        })}</div>
      </section>
      <section className="mci-methodology" aria-label={tLabel("Market comparison methodology")}><h2>{tText("Methodology and sources")}</h2>
        <p>{tText("Point-in-time MCI uses economic vintages available at each historical month-end. PIT availability is date-level rather than intraday.")}</p>
        <p>{tText("Market alignment uses the last finite positive market observation on or before each MCI month-end. Weekends and holidays use the earlier available observation, never a future price. The tooltip shows its actual observation date.")}</p>
        <p>{tText("Market assets are rebased to 100 at the first shared valid date: 100 * price / base price. The common base requires MCI and every selected asset. MCI stays on its native 0-100 scale; it is never ratio-indexed.")}</p>
        <p>{tText("Monthly returns use consecutive aligned month-end prices. MCI monthly change is measured in points. Pearson correlation pairs each month's MCI level or change with that same month's asset return, omitting missing pairs.")}</p>
        <p>{tText(state.data.limitations)}</p>
        {state.data.series.filter((series) => series.series_id !== "MCI").map((series) => <details key={series.series_id}><summary>{tText(series.name)}{tText(": source and coverage")}</summary><p><a href={series.source_url} target="_blank" rel="noreferrer">{tText(series.source)} {tText(" / ")}{tText(series.source_organization)}</a></p><p>{tText(series.price_convention)}{tText(". Coverage: ")}{tText(series.first_observation ?? "Unavailable")} {tText(" to ")}{tText(series.last_observation ?? "Unavailable")}{tText(".")}</p><p>{tText(series.attribution)}</p></details>)}
      </section>
    </>}
    <LeadLagAnalysis macro={macro} startDate={range === "Max" ? undefined : rangeStartDate(Number(range.slice(0, -1)))} />
  </main>;
}
