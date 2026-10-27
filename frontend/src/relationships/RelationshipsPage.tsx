import { tText, tLabel, getLocale } from "../i18n/language";
import { useEffect, useState } from "react";
import { fetchRelationshipComparison, fetchRelationshipSources, type RelationshipCatalogSource, type RelationshipSource, type RelationshipKey, type RelationshipResponse } from "../api/macrolens";
import { InfoTooltip } from "../components/InfoTooltip";
import { shortUnit } from "./relationshipAxes";
import { rangeStartDate } from "../charts/chartData";
import { featureLabel, categoryLabel, selectedUnit } from "../indicators/indicatorMetadata";
import { RelationshipChart, type ComparisonMode } from "./RelationshipChart";
import { availablePresets, measureKey, measureLabel, relationshipSourceName, presetSource } from "./relationshipDefinitions";

const ranges = ["1Y", "3Y", "5Y", "10Y", "Max"] as const;
type Range = typeof ranges[number];
type LoadState<T> = { status: "loading" } | { status: "error" } | { status: "ready"; data: T };

const seriesColors = ["#83a9d5", "#d9af75", "#b6a2d8"];

function SourceSelect({ index, value, catalog, onChange }: {
  index: number; value: RelationshipSource; catalog: RelationshipCatalogSource[];
  onChange: (value: RelationshipSource) => void;
}) {
  const selected = catalog.find(row => row.series_id === value.seriesId);
  const groups = [...new Set(catalog.map(row => row.category))];
  const features = selected?.features.filter(feature => feature !== "level") ?? [];
  const unit = selected ? shortUnit(selectedUnit(selected, value.featureName ?? null)) : "";
  return <fieldset className="relationship-source-control">
    <legend><span className="relationship-series-dot" style={{ background: seriesColors[index - 1] }} />{tText(`Series ${index}`)}</legend>
    <label className="relationship-select"><span>{tText("Data")}</span>
      <select aria-label={tLabel(`Series ${index} data`)} value={value.seriesId} onChange={event => onChange({ seriesId: event.target.value })}>
        {groups.map(group => <optgroup key={group} label={tLabel(group === "market" ? "Market assets" : categoryLabel(group))}>{catalog.filter(row => row.category === group).map(row => <option key={row.series_id} value={row.series_id}>{tText(relationshipSourceName(row))}</option>)}</optgroup>)}
      </select>
    </label>
    {features.length && selected?.source_kind !== "asset" ? <label className="relationship-select"><span>{tText("Measure")}</span>
      <select aria-label={tLabel(`Series ${index} measure`)} value={value.featureName ?? ""} onChange={event => onChange({ ...value, featureName: event.target.value || undefined })}>
        <option value="">{tText("Level")}</option>
        {features.map(feature => <option key={feature} value={feature}>{tText(featureLabel(feature))}</option>)}
      </select>
    </label> : <div className="relationship-static-measure"><span>{tText("Measure")}</span><strong>{tText(selected?.source_kind === "asset" ? "Price" : "Level")} · {tText(unit)}</strong></div>}
    {selected ? <small className="relationship-source-meta">{tText(unit)} · {tText(selected.frequency)}</small> : null}
  </fieldset>;
}

export function RelationshipsPage({ embedded = false }: { embedded?: boolean } = {}) {
  const Heading = embedded ? "h2" : "h1";
  const [examplesOpen, setExamplesOpen] = useState(false);
  const [catalog, setCatalog] = useState<LoadState<RelationshipCatalogSource[]>>({ status: "loading" });
  const [catalogRetry, setCatalogRetry] = useState(0);
  const [left, setLeft] = useState<RelationshipSource>({ seriesId: "UNRATE" });
  const [right, setRight] = useState<RelationshipSource>({ seriesId: "DFF" });
  const [third, setThird] = useState<RelationshipSource>();
  const [range, setRange] = useState<Range>("3Y");
  const [mode, setMode] = useState<ComparisonMode>("actual");
  const [retry, setRetry] = useState(0);
  const [response, setResponse] = useState<{ key: string; state: LoadState<RelationshipResponse> }>({ key: "", state: { status: "loading" } });
  const requestKey = `${measureKey(left)}|${measureKey(right)}|${measureKey(third)}|${range}|${retry}`;
  const selectedKeys = [measureKey(left), measureKey(right), ...(third ? [measureKey(third)] : [])];
  const duplicate = new Set(selectedKeys).size !== selectedKeys.length;
  useEffect(() => {
    const controller = new AbortController(); setCatalog({ status: "loading" });
    fetchRelationshipSources(controller.signal).then(data => {
      if (controller.signal.aborted) return;
      setCatalog({ status: "ready", data: data.sources });
      setLeft({ seriesId: data.sources.find(row => row.series_id === "UNRATE")?.series_id ?? data.sources[0]?.series_id ?? "" });
      setRight({ seriesId: data.sources.find(row => row.series_id === "DFF")?.series_id ?? data.sources[1]?.series_id ?? "" });
    }).catch(() => { if (!controller.signal.aborted) setCatalog({ status: "error" }); });
    return () => controller.abort();
  }, [catalogRetry]);
  const ready = catalog.status === "ready" && catalog.data.length >= 2;
  useEffect(() => {
    if (!ready || duplicate) return;
    const controller = new AbortController(); setResponse({ key: requestKey, state: { status: "loading" } });
    fetchRelationshipComparison({ left, right, third, startDate: range === "Max" ? undefined : rangeStartDate(Number(range.slice(0, -1))), signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) { setResponse({ key: requestKey, state: { status: "ready", data } }); if (data.indexing?.available === false) setMode("actual"); } })
      .catch(() => { if (!controller.signal.aborted) setResponse({ key: requestKey, state: { status: "error" } }); });
    return () => controller.abort();
  }, [ready, duplicate, requestKey]);
  const state = response.key === requestKey && !duplicate ? response.state : { status: "loading" } as const;
  const labels: Record<RelationshipKey, string> = { left: "First indicator", right: "Second indicator", third: "Third indicator" };
  if (state.status === "ready") for (const indicator of state.data.indicators) labels[indicator.key] = measureLabel(indicator, indicator.feature_name);
  const canIndex = state.status === "ready" && state.data.indexing?.available !== false && state.data.normalization_base_period !== null;
  const displayMode = mode === "indexed" && canIndex ? "indexed" : "actual";

  return <main className="relationships-page">
    <header className="relationships-header"><Heading>{tText("Compare Data")}</Heading>
      <p>{tText("Current-vintage data. Correlation does not imply causation.")}</p></header>
    {catalog.status === "loading" ? <p role="status">{tText("Loading configured sources...")}</p> : null}
    {catalog.status === "error" ? <div role="alert">{tText("Unable to load configured sources.")} <button onClick={() => setCatalogRetry(value => value + 1)}>{tText("Retry")}</button></div> : null}
    {catalog.status === "ready" && !ready ? <p>{tText("Not enough configured sources are available.")}</p> : null}
    {catalog.status === "ready" && ready ? <>
      <section className="relationship-controls" aria-label={tLabel("Relationship controls")}>
        <div className="relationship-selectors" style={{ gridTemplateColumns: `repeat(${third ? 3 : 2}, minmax(0, 1fr))` }}>
          <SourceSelect index={1} value={left} catalog={catalog.data} onChange={setLeft} />
          <SourceSelect index={2} value={right} catalog={catalog.data} onChange={setRight} />
          {third ? <SourceSelect index={3} value={third} catalog={catalog.data} onChange={setThird} /> : null}
        </div>
        <div className="relationship-actions">
          {third ? <button onClick={() => setThird(undefined)}>{tText("Remove series")}</button> : <button onClick={() => { const source = catalog.data.find(item => item.series_id !== left.seriesId && item.series_id !== right.seriesId); if (source) setThird({ seriesId: source.series_id }); }}>{tText("Add series")}</button>}
          <button aria-expanded={examplesOpen} aria-controls="relationship-examples" onClick={() => setExamplesOpen(value => !value)}>{tText("Example comparisons")}</button>
        </div>
        {examplesOpen ? <div id="relationship-examples" className="relationship-presets" role="group" aria-label={tLabel("Quick comparisons")}>{availablePresets(catalog.data).map(preset => <button key={preset.label} onClick={() => { setLeft(presetSource(preset.left)); setRight(presetSource(preset.right)); setThird(undefined); }}>{tText(preset.label)}</button>)}</div> : null}
        {duplicate ? <p role="alert">{tText("Select distinct measures.")}</p> : null}
        <div className="relationship-options"><div className="charts-range" role="group" aria-label={tLabel("Relationship time range")}>{ranges.map(item => <button key={item} aria-pressed={range === item} className={range === item ? "is-active" : ""} onClick={() => setRange(item)}>{tText(item)}</button>)}</div>
          <div className="charts-range" role="group" aria-label={tLabel("Comparison scale")}><button aria-pressed={displayMode === "actual"} className={displayMode === "actual" ? "is-active" : ""} onClick={() => setMode("actual")}>{tText("Values")}</button><button disabled={!canIndex} aria-pressed={displayMode === "indexed"} className={displayMode === "indexed" ? "is-active" : ""} onClick={() => setMode("indexed")}>{tText("Index 100")}</button>{state.status === "ready" && !canIndex ? <InfoTooltip label="Why Index 100 is unavailable" description={state.data.indexing?.reason ?? "Index 100 needs positive levels with a shared base period; rates and changes cannot be indexed."} /> : null}</div></div>
      </section>
      <section className="relationship-panel" aria-label={tLabel("Relationship results")}>
        {state.status === "loading" && !duplicate ? <p className="relationship-state" role="status">{tText("Loading relationship data...")}</p> : null}
        {state.status === "error" ? <div className="relationship-state" role="alert">{tText("Unable to load relationship data. ")}<button onClick={() => setRetry(value => value + 1)}>{tText("Retry")}</button></div> : null}
        {state.status === "ready" && !state.data.observations.length ? <p>{tText("No aligned history available for this range.")}</p> : null}
        {state.status === "ready" && state.data.observations.length ? <RelationshipChart response={state.data} labels={labels} mode={displayMode} /> : null}
      </section>
      {state.status === "ready" ? <section className="relationship-summary" aria-label={tLabel("Relationship summary")}>
        <p>{tText("Comparison frequency: ")}{tText(state.data.comparison_frequency)}</p>
        <div className="relationship-summary__grid">{state.data.comparisons.map(comparison => <article key={`${comparison.left_key}-${comparison.right_key}`}><h3>{tText(labels[comparison.left_key])} {tText(" / ")}{tText(labels[comparison.right_key])}</h3><dl>
          <div><dt>{tText("N")}</dt><dd>{comparison.overlapping_observation_count}</dd></div><div><dt>{tText("Pearson r")}</dt><dd>{comparison.correlation === null ? tText("Unavailable") : new Intl.NumberFormat(getLocale(), { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(comparison.correlation)}</dd></div>
          <div><dt>{tText("Paired period range")}</dt><dd>{comparison.first_pair_period ?? "\u2014"} {tText(" through ")}{comparison.last_pair_period ?? "\u2014"}</dd></div></dl></article>)}</div>
      </section> : null}
      <details className="relationship-method"><summary>{tText("Method and limitations")}</summary>
        <p>{tText("Historical observations use the latest stored values and may include revisions. This is not point-in-time historical reconstruction.")}</p>
        <p>{tText("Observation periods are not publication dates. This view is not a PIT backtest.")}</p>
        <p>{tText("Correlation describes how two historical series moved together over the selected period. It does not establish causation or predict future market moves.")}</p>
        <p>{tText("Correlations of levels can reflect common trends; they are not return correlations or trading signals.")}</p>
        <p>{tText("Actual values share an axis when display units are compatible; different units use separate axes.")}</p>
        <p>{tText("Indexed comparison: 100 at the first shared nonzero period. Values show relative change, not economic strength.")}</p>
        <p>{tText("Index 100 needs positive levels with a shared base period; rates and changes cannot be indexed.")}</p>
        {state.status === "ready" ? <>
          <p>{tText(state.data.alignment_methodology)}</p>
          {state.data.indexing?.reason ? <p>{tText(state.data.indexing.reason)}</p> : null}
          {state.data.normalization_base_period ? <p>{tText("Shared base period")}: {state.data.normalization_base_period}</p> : null}
          {state.data.indicators.filter(item => item.excluded_observation_count).map(item => <p key={item.key}>{tText(labels[item.key])}: {tText("Stored feature points excluded because calendar dependencies could not be verified")}: {item.excluded_observation_count}.</p>)}
        </> : null}
        <p>{tText("Correlation is unavailable with fewer than three overlapping periods or no variation.")}</p>
        <p>{tText("Stored data only; source freshness is not checked when this page loads.")}</p>
      </details>
      {state.status === "ready" ? <div className="relationship-sources">{state.data.indicators.map(item => <p key={item.key}>{item.source_url ? <a href={item.source_url} target="_blank" rel="noreferrer">{item.series_id}</a> : item.series_id}{item.attribution ? `: ${tText(item.attribution)}` : ""}</p>)}</div> : null}
    </> : null}
  </main>;
}
