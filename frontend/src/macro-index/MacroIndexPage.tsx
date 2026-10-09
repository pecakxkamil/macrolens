import { useEffect, useState } from "react";
import {
  fetchMciCurrent, fetchMciHistory, pitMciAuditUrl, type MciHistoryMode, type MciComponent, type MciCurrentResponse,
  type MciDomainKey, type MciHistoryResponse, type MciMethodology,
} from "../api/macrolens";
import { rangeStartDate } from "../charts/chartData";
import { formatNumber } from "../format";
import { MciHistoryChart, mciDomains } from "./MciHistoryChart";

const ranges = ["1Y", "3Y", "5Y", "10Y", "Max"] as const;
type Range = typeof ranges[number];
type LoadState<T> = { status: "loading" } | { status: "error" } | { status: "ready"; data: T };
const scoreText = (value: number | null) => value === null ? "Unavailable" : formatNumber(value, 1);
const weightText = (value: number) => `${formatNumber(value * 100, 2)}%`;

function ComponentDetails({ component }: { component: MciComponent }) {
  return <details className="mci-component-details">
    <summary>{component.label}: calculation and freshness</summary>
    <p>{component.rationale}</p>
    <p>Orientation: {component.orientation === "target_distance" ? "Proximity to 2%" : component.orientation === "higher" ? "Higher values raise the score" : "Lower values raise the score"}.</p>
    <ul>{component.inputs.map((input) => <li key={input.feature_name}>{component.series_id} / {input.feature_name}: {formatNumber(input.value)}</li>)}</ul>
    {component.features.length === 2 ? <p>Raw component = {component.features[0]} minus {component.features[1]}.</p> : null}
    <p>Source observation: {component.source_observation_date ?? "Unavailable"}. Feature freshness: {component.feature_as_of_date ?? "Unavailable"}.</p>
    <p>Effective month: {component.effective_month?.slice(0, 7) ?? "Unavailable"}{component.carried_forward ? " (carried forward)" : ""}.</p>
    {component.orientation !== "target_distance" ? <p>Expanding reference: {component.reference_sample_size} observations, {component.reference_start_date ?? "-"} to {component.reference_end_date ?? "-"}.</p> : null}
    {component.vintage_dates_used ? <p>Vintage dates used: {component.vintage_dates_used.join(", ") || "Unavailable"}.</p> : null}
    <p>Overall component weight: {weightText(component.overall_weight)}. Contribution to MCI: {scoreText(component.mci_contribution)} points.</p>
  </details>;
}

function Methodology({ data }: { data: MciMethodology }) {
  return <section className="mci-methodology" aria-label="Index methodology">
    <h2>Methodology v1</h2>
    <p>50 is the historically typical reference. Above 50 describes broader relatively favorable or strong conditions; below 50 describes broader relatively weak conditions. Inflation uses proximity to a fixed analytical reference instead of a historical percentile.</p>
    <p>Activity normalization: <code>{data.normalization.formula}</code>. Lower-oriented components use <code>{data.normalization.lower_orientation}</code>. The reference includes only component observations through the scored month, including that observation.</p>
    <p>Warm-up: {data.normalization.minimum_monthly_samples} monthly observations or {data.normalization.minimum_quarterly_samples} quarterly GDP observations. Constant reference samples score 50.</p>
    <p>Inflation stability: <code>{data.normalization.inflation_formula}</code>. The {data.normalization.inflation_reference_percent}% reference scores 100, a 2 percentage-point deviation scores 50, and a deviation of {data.normalization.inflation_zero_distance_pp} percentage points or more scores 0. Above- and below-reference deviations are penalized equally. This is an analytical reference for all three inflation measures.</p>
    <p>Components are equally weighted within each domain. The six domains each have a weight of 1/6. MCI is their weighted mean.</p>
    <p>{data.missing_data}</p>
    <p>{data.alignment.monthly_weekly} {data.alignment.gdp} {data.alignment.calendar}</p>
    <p>{data.current_selection}</p>
    <p>This is a descriptive analytical index. It provides no market prediction or recession probability.</p>
  </section>;
}

export function MacroIndexPage() {
  const [mode, setMode] = useState<MciHistoryMode>("point_in_time");
  const [range, setRange] = useState<Range>("3Y");
  const [visible, setVisible] = useState<MciDomainKey[]>([]);
  const [retry, setRetry] = useState(0);
  const [current, setCurrent] = useState<LoadState<MciCurrentResponse>>({ status: "loading" });
  const [history, setHistory] = useState<LoadState<MciHistoryResponse>>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    setCurrent({ status: "loading" });
    fetchMciCurrent(controller.signal, mode)
      .then((data) => { if (!controller.signal.aborted) setCurrent({ status: "ready", data }); })
      .catch(() => { if (!controller.signal.aborted) setCurrent({ status: "error" }); });
    return () => controller.abort();
  }, [retry, mode]);

  useEffect(() => {
    const controller = new AbortController();
    setHistory({ status: "loading" });
    fetchMciHistory({ startDate: range === "Max" ? undefined : rangeStartDate(Number(range.slice(0, -1))), signal: controller.signal }, mode)
      .then((data) => { if (!controller.signal.aborted) setHistory({ status: "ready", data }); })
      .catch(() => { if (!controller.signal.aborted) setHistory({ status: "error" }); });
    return () => controller.abort();
  }, [range, retry, mode]);

  const methodology = current.status === "ready" ? current.data : history.status === "ready" ? history.data : null;
  return <main className="macro-index-page">
    <header className="macro-index-header">
      <p className="eyebrow">MacroLens</p>
      <h1>Macro Conditions Index</h1>
      <p className="subtitle">Descriptive monthly US macroeconomic conditions, with six transparent domain subindices.</p>
    </header>
    <div className="charts-range mci-mode-controls" role="group" aria-label="Index history mode">
      {(["point_in_time", "current_vintage"] as const).map((item) => <button key={item} aria-pressed={mode === item}
        className={mode === item ? "is-active" : ""} onClick={() => {
          if (item !== mode) {
            setCurrent({ status: "loading" }); setHistory({ status: "loading" }); setMode(item);
          }
        }}>{item === "point_in_time" ? "Point-in-time" : "Current-vintage"}</button>)}
    </div>
    <div className="charts-notice">
      {mode === "point_in_time" ? <>
        <strong>Point-in-time uses only data vintages available by each historical month-end.</strong>
        <span>Availability is date-level. ALFRED vintage dates do not establish precise intraday publication times.</span>
      </> : <>
        <strong>Current-vintage history.</strong>
        <span>Current-vintage history uses today's stored revised values.</span>
        <span>Historical MCI values may differ from what could have been calculated in real time. Publication availability is not reconstructed.</span>
      </>}
      <span>This descriptive index is not an investable or backtest signal.</span>
    </div>
    {current.status === "loading" ? <div className="loading-panel">Loading current index...</div> : null}
    {current.status === "error" ? <div className="error-panel" role="alert"><p>Unable to load the current Macro Conditions Index.</p><button onClick={() => setRetry((value) => value + 1)}>Retry current index</button></div> : null}
    {current.status === "ready" ? <>
      <section className="mci-current" aria-label="Current Macro Conditions Index">
        <div><span>Macro Conditions Index ({mode === "point_in_time" ? "Point-in-time" : "Current-vintage"})</span><strong>{scoreText(current.data.mci)}{current.data.mci !== null ? " / 100" : ""}</strong></div>
        <div className="mci-scale" role="meter" aria-label="Current MCI score" aria-valuemin={0} aria-valuemax={100} aria-valuenow={current.data.mci ?? undefined} aria-valuetext={scoreText(current.data.mci)}>
          {current.data.mci !== null ? <span style={{ left: `${current.data.mci}%` }} /> : null}
        </div>
        <div className="mci-scale-labels"><span>0</span><span>50 reference</span><span>100</span></div>
        <p>{mode === "point_in_time" ? "As-of month" : "Index month"}: {current.data.observation_date ?? "Unavailable"} · Calculated as of: {current.data.as_of_date}</p>
        {current.data.observation_date !== current.data.latest_evaluated_month ? <p>Latest evaluated month: {current.data.latest_evaluated_month}. Current value uses the latest month with complete coverage.</p> : null}
        {current.data.mci === null ? <p>Complete coverage or sufficient reference history is unavailable. Missing inputs are not filled or reweighted.</p> : null}
      </section>
      {mode === "point_in_time" ? <section className="mci-pit-coverage" aria-label="Point-in-time coverage">
        <h2>Point-in-time coverage</h2>
        <p>First valid historical MCI: {history.status === "ready" ? history.data.coverage?.first_valid_as_of_date ?? "Unavailable" : "Loading coverage..."}. Backfilled through: {current.data.coverage?.backfilled_through ?? "Unavailable"}.</p>
        {current.data.coverage?.missing_series.length ? <p>Vintage history is missing for: {current.data.coverage.missing_series.join(", ")}. PIT scores remain unavailable until coverage is complete.</p> : null}
        <a href={pitMciAuditUrl(current.data.as_of_date)} target="_blank" rel="noreferrer">Inspect exact PIT inputs for {current.data.as_of_date}</a>
      </section> : null}
      <section aria-label="Domain subindices and component decomposition">
        <h2>Domain subindices</h2>
        <div className="mci-domain-grid">{mciDomains.map(({ key }) => {
          const domain = current.data.domains[key];
          return <article className="mci-domain-card" key={key} aria-label={domain.name}>
            <h3>{domain.name}</h3>
            <strong className="mci-domain-score">{scoreText(domain.score)}{domain.score !== null ? " / 100" : ""}</strong>
            <p>Domain weight: {weightText(domain.weight)} · MCI contribution: {scoreText(domain.contribution)} points</p>
            <p>Feature freshness: {domain.as_of_date ?? "Unavailable"}</p>
            <div className="mci-table-wrap"><table>
              <caption>{domain.name} component decomposition</caption>
              <thead><tr><th>Component</th><th>Raw value</th><th>Score / 100</th><th>Weight</th><th>Domain contribution</th></tr></thead>
              <tbody>{domain.components.map((item) => <tr key={item.key}>
                <th scope="row">{item.label}</th><td>{item.raw_value === null ? "Unavailable" : `${formatNumber(item.raw_value)} ${item.unit}`}</td>
                <td>{scoreText(item.score)}{item.status === "insufficient_history" ? <small>Insufficient reference history</small> : null}</td>
                <td>{weightText(item.weight)}</td><td>{scoreText(item.domain_contribution)}</td>
              </tr>)}</tbody>
            </table></div>
            {domain.components.map((item) => <ComponentDetails key={item.key} component={item} />)}
          </article>;
        })}</div>
      </section>
    </> : null}
    <section className="mci-history" aria-label="MCI history">
      <h2>Monthly history: {mode === "point_in_time" ? "Point-in-time" : "Current-vintage"}</h2>
      <div className="charts-range" role="group" aria-label="Index time range">{ranges.map((item) => <button key={item} aria-pressed={range === item} className={range === item ? "is-active" : ""} onClick={() => setRange(item)}>{item}</button>)}</div>
      <fieldset className="mci-series-controls"><legend>Optional domain lines (MCI always shown)</legend>{mciDomains.map((item) => <label key={item.key}>
        <input type="checkbox" checked={visible.includes(item.key)} onChange={() => setVisible((values) => values.includes(item.key) ? values.filter((key) => key !== item.key) : [...values, item.key])} />
        <span style={{ color: item.color }}>{item.label}</span>
      </label>)}</fieldset>
      {history.status === "loading" ? <p className="chart-state">Loading index history...</p> : null}
      {history.status === "error" ? <div role="alert" className="error-panel"><p>Unable to load index history.</p><button onClick={() => setRetry((value) => value + 1)}>Retry history</button></div> : null}
      {history.status === "ready" ? history.data.observations.length ? <>
        <MciHistoryChart rows={history.data.observations} visible={visible} historyType={mode} />
        {!history.data.observations.some((row) => row.mci !== null) ? <p>No complete MCI values for this range. Domain lines may have partial coverage.</p> : null}
        <p className="mci-history-note">Gaps represent unavailable scores. The horizontal reference is 50; the vertical scale is fixed at 0-100.</p>
      </> : <p className="chart-state">No index history available for this range.</p> : null}
    </section>
    {methodology ? <Methodology data={methodology} /> : null}
  </main>;
}
