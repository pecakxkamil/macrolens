import { tText, tLabel } from "../i18n/language";
import { useEffect, useState } from "react";
import { ChartCard } from "./ChartCard";
import { chartDefinitions, chartDomains, type ChartDomain, type ChartSeries } from "./chartDefinitions";
import { fetchChartHistory, rangeStartDate, requestKey, type HistoryResult } from "./chartData";

const ranges = [1, 3, 5, 10] as const;
type Range = typeof ranges[number];

export function ChartsPage({ embedded = false }: { embedded?: boolean } = {}) {
  const Page = embedded ? "section" : "main";
  const [domain, setDomain] = useState<ChartDomain>("labor");
  const [range, setRange] = useState<Range>(3);
  const [results, setResults] = useState<Record<string, HistoryResult>>({});
  const definitions = chartDefinitions.filter((definition) => definition.domain === domain);

  useEffect(() => {
    const controller = new AbortController();
    const sources = new Map<string, ChartSeries>();
    for (const definition of chartDefinitions.filter((item) => item.domain === domain)) {
      for (const series of definition.series) sources.set(requestKey(series), series);
    }
    const loading: Record<string, HistoryResult> = Object.fromEntries([...sources.keys()].map((key) => [key, { status: "loading" }]));
    setResults(loading);
    const options = { startDate: rangeStartDate(range), signal: controller.signal };
    for (const [key, series] of sources) {
      fetchChartHistory(series, options)
        .then((data) => {
          if (!controller.signal.aborted) setResults((current) => ({ ...current, [key]: { status: "ready", data } }));
        })
        .catch(() => {
          if (!controller.signal.aborted) setResults((current) => ({ ...current, [key]: { status: "error" } }));
        });
    }
    return () => controller.abort();
  }, [domain, range]);

  return (
    <Page className="charts-page" aria-label={tLabel("Curated charts")}>
      {!embedded?<header className="charts-header"><h1>{tText("Historical Charts")}</h1></header>:null}
      <div className="charts-controls">
        <div className="charts-domain-tabs" role="group" aria-label={tLabel("Chart domain")}>
          {chartDomains.map((item) => <button key={item.id} type="button" aria-pressed={domain === item.id} className={domain === item.id ? "is-active" : ""} onClick={() => setDomain(item.id)}>{tText(item.label)}</button>)}
        </div>
        <div className="charts-range" role="group" aria-label={tLabel("Time range")}>
          {ranges.map((years) => <button key={years} type="button" aria-pressed={range === years} className={range === years ? "is-active" : ""} onClick={() => setRange(years)}>{tText(`${years}Y`)}</button>)}
        </div>
      </div>
      <div className="charts-grid">{definitions.map((definition) => <ChartCard key={definition.id} definition={definition} results={results} />)}</div>
    </Page>
  );
}
