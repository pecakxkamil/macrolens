import { tText, tLabel } from "../i18n/language";
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
    <summary>{tText(component.label)}{tText(": calculation and freshness")}</summary>
    <p>{tText(component.rationale)}</p>
    <p>{tText("Orientation: ")}{tText(component.orientation === "target_distance" ? "Proximity to 2%" : component.orientation === "higher" ? "Higher values raise the score" : "Lower values raise the score")}{tText(".")}</p>
    <ul>{component.inputs.map((input) => <li key={input.feature_name}>{tText(component.series_id)} {tText(" / ")}{tText(input.feature_name)}{tText(": ")}{tText(formatNumber(input.value))}</li>)}</ul>
    {component.features.length === 2 ? <p>{tText("Raw component = ")}{tText(component.features[0])} {tText(" minus ")}{tText(component.features[1])}{tText(".")}</p> : null}
    <p>{tText("Source observation: ")}{tText(component.source_observation_date ?? "Unavailable")}{tText(". Feature freshness: ")}{tText(component.feature_as_of_date ?? "Unavailable")}{tText(".")}</p>
    <p>{tText("Effective month: ")}{tText(component.effective_month?.slice(0, 7) ?? "Unavailable")}{tText(component.carried_forward ? " (carried forward)" : "")}{tText(".")}</p>
    {component.orientation !== "target_distance" ? <p>{tText("Expanding reference: ")}{tText(component.reference_sample_size)} {tText(" observations, ")}{tText(component.reference_start_date ?? "-")} {tText(" to ")}{tText(component.reference_end_date ?? "-")}{tText(".")}</p> : null}
    {component.vintage_dates_used ? <p>{tText("Vintage dates used: ")}{tText(component.vintage_dates_used.join(", ") || "Unavailable")}{tText(".")}</p> : null}
    <p>{tText("Overall component weight: ")}{tText(weightText(component.overall_weight))}{tText(". Contribution to MCI: ")}{tText(scoreText(component.mci_contribution))} {tText(" points.")}</p>
  </details>;
}

function Methodology({ data }: { data: MciMethodology }) {
  return <section className="mci-methodology" aria-label={tLabel("Index methodology")}>
    <h2>{tText("Methodology v1")}</h2>
    <p>{tText("50 is the historically typical reference. Above 50 describes broader relatively favorable or strong conditions; below 50 describes broader relatively weak conditions. Inflation uses proximity to a fixed analytical reference instead of a historical percentile.")}</p>
    <p>{tText("Activity normalization: ")}<code>{data.normalization.formula}</code>{tText(". Lower-oriented components use ")}<code>{data.normalization.lower_orientation}</code>{tText(". The reference includes only component observations through the scored month, including that observation.")}</p>
    <p>{tText("Warm-up: ")}{tText(data.normalization.minimum_monthly_samples)} {tText(" monthly observations or ")}{tText(data.normalization.minimum_quarterly_samples)} {tText(" quarterly GDP observations. Constant reference samples score 50.")}</p>
    <p>{tText("Inflation stability: ")}<code>{data.normalization.inflation_formula}</code>{tText(". The ")}{tText(data.normalization.inflation_reference_percent)}{tText("% reference scores 100, a 2 percentage-point deviation scores 50, and a deviation of ")}{tText(data.normalization.inflation_zero_distance_pp)} {tText(" percentage points or more scores 0. Above- and below-reference deviations are penalized equally. This is an analytical reference for all three inflation measures.")}</p>
    <p>{tText("Components are equally weighted within each domain. The six domains each have a weight of 1/6. MCI is their weighted mean.")}</p>
    <p>{tText(data.missing_data)}</p>
    <p>{tText(data.alignment.monthly_weekly)} {tText(data.alignment.gdp)} {tText(data.alignment.calendar)}</p>
    <p>{tText(data.current_selection)}</p>
    <p>{tText("This is a descriptive analytical index. It provides no market prediction or recession probability.")}</p>
  </section>;
}

export function MacroIndexPage({ embedded = false }: { embedded?: boolean } = {}) {
  const Heading = embedded ? "h2" : "h1";
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
      <p className="eyebrow">{tText("MacroLens")}</p>
      <Heading>{tText("Macro Conditions Index")}</Heading>
      <p className="subtitle">{tText("Experimental descriptive index of monthly US macroeconomic conditions, with six transparent domain subindices.")}</p>
    </header>
    <p className="market-note">{tText("MCI summarizes selected macro indicators on a common descriptive scale. It is not a validated recession or forecasting model; 50 is a reference value, not a validated boundary between recession and a healthy economy.")}</p>
    <div className="charts-range mci-mode-controls" role="group" aria-label={tLabel("Index history mode")}>
      {(["point_in_time", "current_vintage"] as const).map((item) => <button key={item} aria-pressed={mode === item}
        className={mode === item ? "is-active" : ""} onClick={() => {
          if (item !== mode) {
            setCurrent({ status: "loading" }); setHistory({ status: "loading" }); setMode(item);
          }
        }}>{tText(item === "point_in_time" ? "Point-in-time" : "Current-vintage")}</button>)}
    </div>
    <div className="charts-notice">
      {mode === "point_in_time" ? <>
        <strong>{tText("Point-in-time uses only data vintages available by each historical month-end.")}</strong>
        <span>{tText("Availability is date-level. ALFRED vintage dates do not establish precise intraday publication times.")}</span>
      </> : <>
        <strong>{tText("Current-vintage history.")}</strong>
        <span>{tText("Current-vintage history uses today's stored revised values.")}</span>
        <span>{tText("Historical MCI values may differ from what could have been calculated in real time. Publication availability is not reconstructed.")}</span>
      </>}
      <span>{tText("This descriptive index is not an investable or backtest signal.")}</span>
    </div>
    {current.status === "loading" ? <div className="loading-panel">{tText("Loading current index...")}</div> : null}
    {current.status === "error" ? <div className="error-panel" role="alert"><p>{tText("Unable to load the current Macro Conditions Index.")}</p><button onClick={() => setRetry((value) => value + 1)}>{tText("Retry current index")}</button></div> : null}
    {current.status === "ready" ? <>
      <section className="mci-current" aria-label={tLabel("Current Macro Conditions Index")}>
        <div><span>{tText("Macro Conditions Index (")}{tText(mode === "point_in_time" ? "Point-in-time" : "Current-vintage")}{tText(")")}</span><strong>{tText(scoreText(current.data.mci))}{tText(current.data.mci !== null ? " / 100" : "")}</strong></div>
        <div className="mci-scale" role="meter" aria-label={tLabel("Current MCI score")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={current.data.mci ?? undefined} aria-valuetext={tLabel(scoreText(current.data.mci))}>
          {current.data.mci !== null ? <span style={{ left: `${current.data.mci}%` }} /> : null}
        </div>
        <div className="mci-scale-labels"><span>{tText("0")}</span><span>{tText("50 reference")}</span><span>{tText("100")}</span></div>
        <p>{tText(mode === "point_in_time" ? "As-of month" : "Index month")}{tText(": ")}{tText(current.data.observation_date ?? "Unavailable")} {tText(" · Calculated as of: ")}{tText(current.data.as_of_date)}</p>
        {current.data.observation_date !== current.data.latest_evaluated_month ? <p>{tText("Latest evaluated month: ")}{tText(current.data.latest_evaluated_month)}{tText(". Current value uses the latest month with complete coverage.")}</p> : null}
        {current.data.mci === null ? <p>{tText("Complete coverage or sufficient reference history is unavailable. Missing inputs are not filled or reweighted.")}</p> : null}
      </section>
      {mode === "point_in_time" ? <section className="mci-pit-coverage" aria-label={tLabel("Point-in-time coverage")}>
        <h2>{tText("Point-in-time coverage")}</h2>
        <p>{tText("First valid historical MCI: ")}{tText((history.status === "ready" ? history.data.coverage?.first_valid_as_of_date : undefined) ?? current.data.coverage?.first_valid_as_of_date ?? (history.status === "loading" ? "Loading coverage..." : "Unavailable"))}{tText(". Backfilled through: ")}{tText(current.data.coverage?.backfilled_through ?? "Unavailable")}{tText(".")}</p>
        {current.data.coverage?.missing_series.length ? <p>{tText("Vintage history is missing for: ")}{tText(current.data.coverage.missing_series.join(", "))}{tText(". PIT scores remain unavailable until coverage is complete.")}</p> : null}
        <a href={pitMciAuditUrl(current.data.as_of_date)} target="_blank" rel="noreferrer">{tText("Inspect exact PIT inputs for ")}{tText(current.data.as_of_date)}</a>
      </section> : null}
      <section aria-label={tLabel("Domain subindices and component decomposition")}>
        <h2>{tText("Domain subindices")}</h2>
        <div className="mci-domain-grid">{mciDomains.map(({ key }) => {
          const domain = current.data.domains[key];
          return <article className="mci-domain-card" key={key} aria-label={tLabel(domain.name)}>
            <h3>{tText(domain.name)}</h3>
            <strong className="mci-domain-score">{tText(scoreText(domain.score))}{tText(domain.score !== null ? " / 100" : "")}</strong>
            <p>{tText("Domain weight: ")}{tText(weightText(domain.weight))} {tText(" · MCI contribution: ")}{tText(scoreText(domain.contribution))} {tText(" points")}</p>
            <p>{tText("Feature freshness: ")}{tText(domain.as_of_date ?? "Unavailable")}</p>
            <div className="mci-table-wrap"><table>
              <caption>{tText(domain.name)} {tText(" component decomposition")}</caption>
              <thead><tr><th>{tText("Component")}</th><th>{tText("Raw value")}</th><th>{tText("Score / 100")}</th><th>{tText("Weight")}</th><th>{tText("Domain contribution")}</th></tr></thead>
              <tbody>{domain.components.map((item) => <tr key={item.key}>
                <th scope="row">{tText(item.label)}</th><td>{tText(item.raw_value === null ? "Unavailable" : `${formatNumber(item.raw_value)} ${item.unit}`)}</td>
                <td>{tText(scoreText(item.score))}{item.status === "insufficient_history" ? <small>{tText("Insufficient reference history")}</small> : null}</td>
                <td>{tText(weightText(item.weight))}</td><td>{tText(scoreText(item.domain_contribution))}</td>
              </tr>)}</tbody>
            </table></div>
            {domain.components.map((item) => <ComponentDetails key={item.key} component={item} />)}
          </article>;
        })}</div>
      </section>
    </> : null}
    <section className="mci-history" aria-label={tLabel("MCI history")}>
      <h2>{tText("Monthly history: ")}{tText(mode === "point_in_time" ? "Point-in-time" : "Current-vintage")}</h2>
      <div className="charts-range" role="group" aria-label={tLabel("Index time range")}>{ranges.map((item) => <button key={item} aria-pressed={range === item} className={range === item ? "is-active" : ""} onClick={() => setRange(item)}>{tText(item)}</button>)}</div>
      <fieldset className="mci-series-controls"><legend>{tText("Optional domain lines (MCI always shown)")}</legend>{mciDomains.map((item) => <label key={item.key}>
        <input type="checkbox" checked={visible.includes(item.key)} onChange={() => setVisible((values) => values.includes(item.key) ? values.filter((key) => key !== item.key) : [...values, item.key])} />
        <span style={{ color: item.color }}>{tText(item.label)}</span>
      </label>)}</fieldset>
      {history.status === "loading" ? <p className="chart-state">{tText("Loading index history...")}</p> : null}
      {history.status === "error" ? <div role="alert" className="error-panel"><p>{tText("Unable to load index history.")}</p><button onClick={() => setRetry((value) => value + 1)}>{tText("Retry history")}</button></div> : null}
      {history.status === "ready" ? history.data.observations.length ? <>
        <MciHistoryChart rows={history.data.observations} visible={visible} historyType={mode} />
        {!history.data.observations.some((row) => row.mci !== null) ? <p>{tText("No complete MCI values for this range. Domain lines may have partial coverage.")}</p> : null}
        <p className="mci-history-note">{tText("Gaps represent unavailable scores. The horizontal reference is 50; the vertical scale is fixed at 0-100.")}</p>
      </> : <p className="chart-state">{tText("No index history available for this range.")}</p> : null}
    </section>
    {methodology ? <Methodology data={methodology} /> : null}
  </main>;
}
