import { useEffect, useState } from "react";
import {
  fetchFeatureHistory,
  fetchSeriesCatalog,
  fetchSeriesFeatures,
  fetchSeriesHistory,
  type HistoryResponse,
  type SeriesFeaturesResponse,
  type SeriesMetadata,
} from "../api/macrolens";
import { TimeSeriesChart } from "../charts/TimeSeriesChart";
import { rangeStartDate, type ChartRow } from "../charts/chartData";
import type { ChartDefinition } from "../charts/chartDefinitions";
import { formatObservationDate } from "../format";
import { categoryLabel, featureLabel, formatIndicatorValue, indicatorCategories, selectedUnit } from "./indicatorMetadata";

const ranges = [1, 3, 5, 10] as const;
type Range = typeof ranges[number];
type LoadState<T> = { status: "loading" } | { status: "error" } | { status: "ready"; data: T };

function indicatorChart(metadata: SeriesMetadata, feature: string | null): ChartDefinition {
  const title = `${metadata.short_name || metadata.name} · ${feature ? featureLabel(feature) : "Level"}`;
  return {
    id: `indicator-${metadata.series_id}-${feature ?? "raw"}`,
    domain: metadata.category === "financial_conditions" ? "financial" : metadata.category as ChartDefinition["domain"],
    title,
    description: `${metadata.series_id} · ${feature ? featureLabel(feature) : "Observed level"} · ${metadata.frequency} observations`,
    unit: "index",
    frequency: metadata.frequency as ChartDefinition["frequency"],
    series: [{ id: "value", label: feature ? featureLabel(feature) : "Observed level", color: "#83a9d5" }],
  };
}

export function historyRows(history: HistoryResponse): ChartRow[] {
  return history.observations.map((observation) => ({
    observation_date: observation.observation_date,
    value: typeof observation.value === "number" && Number.isFinite(observation.value) ? observation.value : null,
  })).sort((a, b) => a.observation_date.localeCompare(b.observation_date));
}

export function IndicatorsPage({ seriesId }: { seriesId?: string }) {
  const [catalog, setCatalog] = useState<LoadState<SeriesMetadata[]>>({ status: "loading" });
  const [catalogRequest, setCatalogRequest] = useState(0);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [range, setRange] = useState<Range>(3);
  const [featureChoice, setFeatureChoice] = useState<{ seriesId: string; feature: string | null }>({ seriesId: "", feature: null });
  const [features, setFeatures] = useState<{ seriesId: string; state: LoadState<SeriesFeaturesResponse> }>({ seriesId: "", state: { status: "loading" } });
  const [history, setHistory] = useState<{ key: string; state: LoadState<HistoryResponse> }>({ key: "", state: { status: "loading" } });

  useEffect(() => {
    const controller = new AbortController();
    setCatalog({ status: "loading" });
    fetchSeriesCatalog(controller.signal)
      .then((data) => { if (!controller.signal.aborted) setCatalog({ status: "ready", data: data.series }); })
      .catch(() => { if (!controller.signal.aborted) setCatalog({ status: "error" }); });
    return () => controller.abort();
  }, [catalogRequest]);

  useEffect(() => {
    if (catalog.status === "ready" && !seriesId && catalog.data.length) {
      const initial = catalog.data.find((item) => item.series_id === "UNRATE") ?? catalog.data[0];
      window.location.hash = `#/indicators/${encodeURIComponent(initial.series_id)}`;
    }
  }, [catalog, seriesId]);

  const selected = catalog.status === "ready" ? catalog.data.find((item) => item.series_id === seriesId) : undefined;
  const feature = selected && featureChoice.seriesId === selected.series_id ? featureChoice.feature : null;
  const historyKey = selected ? `${selected.series_id}:${feature ?? "raw"}:${range}` : "";

  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    setFeatures({ seriesId: selected.series_id, state: { status: "loading" } });
    fetchSeriesFeatures(selected.series_id, controller.signal)
      .then((data) => { if (!controller.signal.aborted) setFeatures({ seriesId: selected.series_id, state: { status: "ready", data } }); })
      .catch(() => { if (!controller.signal.aborted) setFeatures({ seriesId: selected.series_id, state: { status: "error" } }); });
    return () => controller.abort();
  }, [selected?.series_id]);

  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    setHistory({ key: historyKey, state: { status: "loading" } });
    const options = { startDate: rangeStartDate(range), signal: controller.signal };
    const request = feature
      ? fetchFeatureHistory(selected.series_id, feature, options)
      : fetchSeriesHistory(selected.series_id, options);
    request
      .then((data) => { if (!controller.signal.aborted) setHistory({ key: historyKey, state: { status: "ready", data } }); })
      .catch(() => { if (!controller.signal.aborted) setHistory({ key: historyKey, state: { status: "error" } }); });
    return () => controller.abort();
  }, [historyKey]);

  const filtered = catalog.status === "ready" ? catalog.data.filter((item) => {
    const query = search.trim().toLocaleLowerCase();
    return (category === "all" || item.category === category)
      && (!query || [item.series_id, item.name, item.short_name].some((value) => value?.toLocaleLowerCase().includes(query)));
  }) : [];
  const featuresState = selected && features.seriesId === selected.series_id ? features.state : { status: "loading" } as const;
  const availableFeatures = featuresState.status === "ready" ? featuresState.data.features.filter((name) => name !== "level") : [];
  const historyState = history.key === historyKey ? history.state : { status: "loading" } as const;
  const rows = historyState.status === "ready" ? historyRows(historyState.data) : [];
  const readings = rows.filter((row) => typeof row.value === "number");
  const current = readings[readings.length - 1];
  const previous = readings[readings.length - 2];

  return (
    <main className="indicators-page">
      <header className="indicators-header">
        <p className="eyebrow">MacroLens</p>
        <h1>Indicators</h1>
        <p className="subtitle">Browse the MacroLens US indicator library and inspect individual series.</p>
      </header>
      <div className="indicators-notice"><strong>Current-vintage history.</strong> Historical observations use the latest stored values. Revised series may differ from originally published values. No trading signals.</div>
      <div className="indicators-layout">
        <aside className="indicator-browser" aria-label="Indicator browser">
          <label htmlFor="indicator-search">Search indicators</label>
          <input id="indicator-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name or series ID" />
          <div className="indicator-filters" role="group" aria-label="Indicator category">
            {indicatorCategories.map((item) => <button key={item.id} type="button" aria-pressed={category === item.id} onClick={() => setCategory(item.id)}>{item.label}</button>)}
          </div>
          {catalog.status === "loading" ? <p role="status">Loading indicators...</p> : null}
          {catalog.status === "error" ? <div role="alert"><p>Unable to load indicators.</p><button type="button" onClick={() => setCatalogRequest((value) => value + 1)}>Retry</button></div> : null}
          {catalog.status === "ready" ? (
            <>
              <p className="indicator-browser__count">{filtered.length} {filtered.length === 1 ? "indicator" : "indicators"}</p>
              <div className="indicator-list">
                {filtered.map((item) => <a key={item.series_id} href={`#/indicators/${encodeURIComponent(item.series_id)}`} className={item.series_id === seriesId ? "is-selected" : ""} aria-current={item.series_id === seriesId ? "true" : undefined}>
                  <strong>{item.series_id}</strong><span>{item.short_name || item.name}</span><small>{categoryLabel(item.category)} · {item.frequency}</small>
                </a>)}
                {!filtered.length ? <p>No indicators match your filters.</p> : null}
              </div>
            </>
          ) : null}
        </aside>

        <section className="indicator-detail" aria-label="Indicator detail">
          {catalog.status === "ready" && !selected && seriesId ? <div className="indicator-empty" role="alert"><h2>Indicator not found</h2><p>No active configured series matches {seriesId}.</p></div> : null}
          {catalog.status === "ready" && !selected && !seriesId && !catalog.data.length ? <p>No active indicators are available.</p> : null}
          {selected ? (
            <>
              <header className="indicator-detail__header">
                <p className="eyebrow">{selected.series_id}</p>
                <h2>{selected.name}</h2>
                <p>{categoryLabel(selected.category)} · {selected.frequency} · {selected.unit}</p>
              </header>
              <div className="indicator-readings">
                <div><span>Current value</span><strong>{current ? formatIndicatorValue(current.value as number, selected, feature) : "—"}</strong><small>Current observation date: {current ? formatObservationDate(current.observation_date, selected.frequency) : "No observation"}</small></div>
                <div><span>Previous value</span><strong>{previous ? formatIndicatorValue(previous.value as number, selected, feature) : "—"}</strong><small>Previous observation date: {previous ? formatObservationDate(previous.observation_date, selected.frequency) : "No earlier observation"}</small></div>
              </div>
              <div className="indicator-chart-controls">
                <div role="group" aria-label="Transformation" className="indicator-transformations">
                  <span>Measure</span>
                  <button type="button" aria-pressed={feature === null} onClick={() => setFeatureChoice({ seriesId: selected.series_id, feature: null })}>Level</button>
                  {availableFeatures.map((name) => <button key={name} type="button" aria-pressed={feature === name} onClick={() => setFeatureChoice({ seriesId: selected.series_id, feature: name })}>{featureLabel(name)}</button>)}
                  {featuresState.status === "loading" ? <span role="status">Loading transformations...</span> : null}
                  {featuresState.status === "error" ? <span role="alert">Transformations unavailable.</span> : null}
                </div>
                <div role="group" aria-label="Indicator time range" className="indicator-ranges">
                  {ranges.map((years) => <button key={years} type="button" aria-pressed={range === years} onClick={() => setRange(years)}>{years}Y</button>)}
                </div>
              </div>
              <div className="indicator-chart-panel">
                <div className="indicator-chart-panel__heading"><h3>{feature ? featureLabel(feature) : "Observed level"}</h3><span>{selectedUnit(selected, feature)}</span></div>
                {historyState.status === "loading" ? <p className="chart-state" role="status">Loading indicator history...</p> : null}
                {historyState.status === "error" ? <p className="chart-state chart-state--error" role="alert">Unable to load indicator history.</p> : null}
                {historyState.status === "ready" && !readings.length ? <p className="chart-state">No history available for this range.</p> : null}
                {historyState.status === "ready" && readings.length ? <TimeSeriesChart key={historyKey} definition={indicatorChart(selected, feature)} rows={rows} valueFormatter={(value, compact) => formatIndicatorValue(value, selected, feature, compact)} /> : null}
              </div>
              <section className="indicator-about" aria-labelledby="indicator-about-heading">
                <h3 id="indicator-about-heading">About this indicator</h3>
                <dl>
                  <div><dt>Series ID</dt><dd>{selected.series_id}</dd></div>
                  <div><dt>Series name</dt><dd>{selected.name}</dd></div>
                  <div><dt>Category</dt><dd>{categoryLabel(selected.category)}</dd></div>
                  <div><dt>Frequency</dt><dd>{selected.frequency}</dd></div>
                  <div><dt>Source unit</dt><dd>{selected.unit}</dd></div>
                  <div><dt>Available measures</dt><dd>Level{availableFeatures.length ? `, ${availableFeatures.map(featureLabel).join(", ")}` : ""}</dd></div>
                </dl>
              </section>
            </>
          ) : null}
        </section>
      </div>
    </main>
  );
}
