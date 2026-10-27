import { tText, tLabel, t } from "../i18n/language";
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

export function IndicatorsPage({ seriesId, embedded = false }: { seriesId?: string; embedded?: boolean }) {
  const Heading = embedded ? "h2" : "h1";
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
      window.location.hash = `#/explore/indicators/${encodeURIComponent(initial.series_id)}`;
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
      && (!query || [item.series_id, item.name, item.short_name].some((value) => value && [value, t(value)].some((name) => name.toLocaleLowerCase().includes(query))));
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
        <p className="eyebrow">{tText("MacroLens")}</p>
        <Heading>{tText("Indicators")}</Heading>
        <p className="subtitle">{tText("Browse the MacroLens US indicator library and inspect individual series.")}</p>
      </header>
      <div className="indicators-notice"><strong>{tText("Current-vintage history.")}</strong> {tText(" Historical observations use the latest stored values. Revised series may differ from originally published values. No trading signals.")}</div>
      <div className="indicators-layout">
        <aside className="indicator-browser" aria-label={tLabel("Indicator browser")}>
          <label htmlFor="indicator-search">{tText("Search indicators")}</label>
          <input id="indicator-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder={tLabel("Name or series ID")} />
          <div className="indicator-filters" role="group" aria-label={tLabel("Indicator category")}>
            {indicatorCategories.map((item) => <button key={item.id} type="button" aria-pressed={category === item.id} onClick={() => setCategory(item.id)}>{tText(item.label)}</button>)}
          </div>
          {catalog.status === "loading" ? <p role="status">{tText("Loading indicators...")}</p> : null}
          {catalog.status === "error" ? <div role="alert"><p>{tText("Unable to load indicators.")}</p><button type="button" onClick={() => setCatalogRequest((value) => value + 1)}>{tText("Retry")}</button></div> : null}
          {catalog.status === "ready" ? (
            <>
              <p className="indicator-browser__count">{tText(filtered.length)} {tText(filtered.length === 1 ? "indicator" : "indicators")}</p>
              <div className="indicator-list">
                {filtered.map((item) => <a key={item.series_id} href={`#/explore/indicators/${encodeURIComponent(item.series_id)}`} className={item.series_id === seriesId ? "is-selected" : ""} aria-current={item.series_id === seriesId ? "true" : undefined}>
                  <strong>{tText(item.series_id)}</strong><span>{tText(item.short_name || item.name)}</span><small>{tText(categoryLabel(item.category))} {tText(" · ")}{tText(item.frequency)}</small>
                </a>)}
                {!filtered.length ? <p>{tText("No indicators match your filters.")}</p> : null}
              </div>
            </>
          ) : null}
        </aside>

        <section className="indicator-detail" aria-label={tLabel("Indicator detail")}>
          {catalog.status === "ready" && !selected && seriesId ? <div className="indicator-empty" role="alert"><h2>{tText("Indicator not found")}</h2><p>{tText("No active configured series matches ")}{tText(seriesId)}{tText(".")}</p></div> : null}
          {catalog.status === "ready" && !selected && !seriesId && !catalog.data.length ? <p>{tText("No active indicators are available.")}</p> : null}
          {selected ? (
            <>
              <header className="indicator-detail__header">
                <p className="eyebrow">{tText(selected.series_id)}</p>
                <h2>{tText(selected.name)}</h2>
                <p>{tText(categoryLabel(selected.category))} {tText(" · ")}{tText(selected.frequency)} {tText(" · ")}{tText(selected.unit)}</p>
              </header>
              <div className="indicator-readings">
                <div><span>{tText("Current value")}</span><strong>{tText(current ? formatIndicatorValue(current.value as number, selected, feature) : "—")}</strong><small>{tText("Current observation date: ")}{tText(current ? formatObservationDate(current.observation_date, selected.frequency) : "No observation")}</small></div>
                <div><span>{tText("Previous value")}</span><strong>{tText(previous ? formatIndicatorValue(previous.value as number, selected, feature) : "—")}</strong><small>{tText("Previous observation date: ")}{tText(previous ? formatObservationDate(previous.observation_date, selected.frequency) : "No earlier observation")}</small></div>
              </div>
              <div className="indicator-chart-controls">
                <div role="group" aria-label={tLabel("Transformation")} className="indicator-transformations">
                  <span>{tText("Measure")}</span>
                  <button type="button" aria-pressed={feature === null} onClick={() => setFeatureChoice({ seriesId: selected.series_id, feature: null })}>{tText("Level")}</button>
                  {availableFeatures.map((name) => <button key={name} type="button" aria-pressed={feature === name} onClick={() => setFeatureChoice({ seriesId: selected.series_id, feature: name })}>{tText(featureLabel(name))}</button>)}
                  {featuresState.status === "loading" ? <span role="status">{tText("Loading transformations...")}</span> : null}
                  {featuresState.status === "error" ? <span role="alert">{tText("Transformations unavailable.")}</span> : null}
                </div>
                <div role="group" aria-label={tLabel("Indicator time range")} className="indicator-ranges">
                  {ranges.map((years) => <button key={years} type="button" aria-pressed={range === years} onClick={() => setRange(years)}>{tText(`${years}Y`)}</button>)}
                </div>
              </div>
              {selected.source === "ism" && historyState.status === "ready" && readings.length ? <p>{tText("Available history")}: {String(readings[0].observation_date)} {tText(" through ")}{String(readings[readings.length - 1].observation_date)} · {readings.length} {tText("observations")}. {tText("Local ISM document history; no imputation or full PIT reconstruction.")}</p> : null}
              <div className="indicator-chart-panel">
                <div className="indicator-chart-panel__heading"><h3>{tText(feature ? featureLabel(feature) : "Observed level")}</h3><span>{tText(selectedUnit(selected, feature))}</span></div>
                {historyState.status === "loading" ? <p className="chart-state" role="status">{tText("Loading indicator history...")}</p> : null}
                {historyState.status === "error" ? <p className="chart-state chart-state--error" role="alert">{tText("Unable to load indicator history.")}</p> : null}
                {historyState.status === "ready" && !readings.length ? <p className="chart-state">{tText("No history available for this range.")}</p> : null}
                {historyState.status === "ready" && readings.length ? <TimeSeriesChart key={historyKey} definition={indicatorChart(selected, feature)} rows={rows} valueFormatter={(value, compact) => formatIndicatorValue(value, selected, feature, compact)} /> : null}
              </div>
              <section className="indicator-about" aria-labelledby="indicator-about-heading">
                <h3 id="indicator-about-heading">{tText("About this indicator")}</h3>
                {selected.description ? <p>{tText(selected.description)}</p> : null}
                {selected.attribution ? <p>{tText(selected.attribution)}</p> : null}
                <dl>
                  <div><dt>{tText("Series ID")}</dt><dd>{tText(selected.series_id)}</dd></div>
                  <div><dt>{tText("Series name")}</dt><dd>{tText(selected.name)}</dd></div>
                  <div><dt>{tText("Category")}</dt><dd>{tText(categoryLabel(selected.category))}</dd></div>
                  <div><dt>{tText("Frequency")}</dt><dd>{tText(selected.frequency)}</dd></div>
                  <div><dt>{tText("Source unit")}</dt><dd>{tText(selected.unit)}</dd></div>
                  <div><dt>{tText("Source")}</dt><dd><a href={selected.source_url ?? `https://fred.stlouisfed.org/series/${encodeURIComponent(selected.series_id)}`} target="_blank" rel="noreferrer">{tText(selected.source === "ism" ? "Institute for Supply Management (ISM)" : "Source and series definition (FRED)")}</a></dd></div>
                  <div><dt>{tText("Available measures")}</dt><dd>{tText("Level")}{tText(availableFeatures.length ? `, ${availableFeatures.map(featureLabel).join(", ")}` : "")}</dd></div>
                </dl>
              </section>
            </>
          ) : null}
        </section>
      </div>
    </main>
  );
}
