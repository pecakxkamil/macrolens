import { InfoTooltip } from "../components/InfoTooltip";
import { tText, tLabel } from "../i18n/language";
import { useEffect, useState } from "react";
import { fetchEconomyBrief, type EconomyBriefResponse } from "../api/macrolens";
import { briefMarkdown, briefModel, calendarNote } from "./briefModel";
import type { PreparedFedTarget } from "./fedTarget";
import type { PreparedReading } from "./readingComparisons";

export function downloadReport(markdown: string, generatedAt: string) {
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `macrolens-economy-brief-${generatedAt.slice(0, 10)}.md`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
function ReadingRow({ reading }: { reading: PreparedReading }) {
  const point = (value: PreparedReading["current"], latest = false) => <td className={latest ? "overview-value--latest" : "overview-value--earlier"}>
    <div className="overview-value"><strong><span className="overview-number">{value.value}</span>{value.suffix ? <small className="overview-inline-unit">{value.suffix}</small> : null}</strong>{latest ? <span className={`overview-change overview-change--${reading.tone}`} >{reading.hasChange ? <InfoTooltip label={`${reading.label}: ${reading.labels.change}`} description={reading.tooltip} trigger={reading.compactChange} /> : reading.compactChange}</span> : null}</div>
    {value.yoy !== undefined ? <small className="overview-yoy">{tText(value.yoy)}{value.yoy === "\u2014" ? "" : "%"} {tText("YoY")}</small> : null}
    <time dateTime={value.date}>{tText(value.period)}</time>
  </td>;
  return <section className="overview-reading" aria-label={tLabel(reading.label)}>
    <div className="overview-reading__heading"><h3><a href={reading.indicatorHref}>{tText(reading.label)}</a></h3><span className="overview-unit">{tText(reading.unit)}</span>
      {reading.sources.map((source, index) => <a className="overview-source" key={source.url} href={source.url} target="_blank" rel="noreferrer" aria-label={tLabel(`${reading.label} - source and definition${reading.sources.length > 1 ? ` (${index === 0 ? "2Y" : "10Y"})` : ""}`)}>{tText(reading.sources.length > 1 ? `${index === 0 ? "2Y" : "10Y"} source` : "Source")}</a>)}
    </div>
    <table className="overview-values" aria-label={tLabel(`${reading.label} comparisons`)}><colgroup><col className="overview-latest-column" /><col /><col /></colgroup>
      <thead><tr><th scope="col">{tText("Latest")}</th><th scope="col">{tText(reading.labels.previous)}</th><th scope="col">{tText(reading.labels.earlier)}</th></tr></thead>
      <tbody><tr>{point(reading.current, true)}{point(reading.previous)}{point(reading.earlier)}</tr></tbody>
    </table>
  </section>;
}

function FedTargetBlock({ target }: { target: PreparedFedTarget }) {
  return <section className="overview-fed-target" aria-label={tLabel("Fed target range")}>
    <h3>{tText("Fed target range")}</h3><strong className="overview-target-value">{tText(target.range)}</strong>
    <dl><div><dt>{tText("Effective since")}</dt><dd>{tText(target.effective)}</dd></div>
      <div><dt>{tText("Last rate change")}</dt><dd>{tText(target.lastChange)}</dd></div></dl>
    <p className="overview-target-dates">{tText("Observed through")}: {tText(target.observed)} {tText(" \u00b7 ")}{tText("Retrieved")}: {tText(target.retrieved)}</p>
    <div className="overview-target-sources">{target.sources.map((source, index) => <a key={source.series_id} href={source.url} target="_blank" rel="noreferrer">{tText(index === 0 ? "Lower bound source" : "Upper bound source")}</a>)}</div>
  </section>;
}

export function EconomyBrief() {
  const [data, setData] = useState<EconomyBriefResponse>();
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setData(undefined); setError(false);
    fetchEconomyBrief(controller.signal).then((value) => { if (!controller.signal.aborted) setData(value); })
      .catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [retry]);
  const model = data ? briefModel(data) : undefined;
  return <>
    <header className="page-header overview-header"><h1>{tText("USA Economy Now")}</h1>
      <button type="button" disabled={!model} onClick={() => { if (model && data) { const generatedAt = new Date().toISOString(); downloadReport(briefMarkdown(model, data, generatedAt), generatedAt); } }}>{tText("Download report")}</button>
    </header>
    {!data && !error ? <p className="loading-panel">{tText("Loading Economy Brief...")}</p> : null}
    {error ? <div className="error-panel" role="alert"><p>{tText("Economy Brief is unavailable. Check the API and try again.")}</p><button onClick={() => setRetry((value) => value + 1)}>{tText("Retry brief")}</button></div> : null}
    {data && model ? <main className="economy-brief">
      <div className="overview-data-note"><p>{tText("Current-vintage readings; earlier values may include revisions. Observation periods are shown with each value.")}</p>
        {data.reading_comparisons?.status !== "ready" ? <p role="status">{tText("Reading comparisons unavailable.")}</p> : model.domains.some((domain) => domain.compact.some((reading) => !reading.raw?.current)) ? <p role="status">{tText("Some readings unavailable.")}</p> : null}
      </div>
      <section aria-label={tLabel("Economy across six domains")}><div className="brief-grid">{model.domains.map((domain) => <article key={domain.key} className="domain-card overview-domain" aria-label={tLabel(`${domain.name} brief`)}>
        <h2>{tText(domain.name)}</h2>{domain.freshnessIssues.map(reading => <p role="status" className="market-note" key={reading.key}>{tText(`${reading.label}: Newer stored period ${reading.raw!.latest_stored_observation_date} has no available reading.`)}</p>)}{domain.key === "financial_conditions" ? <FedTargetBlock target={model.fedTarget} /> : null}{domain.compact.map((reading) => <ReadingRow key={reading.key} reading={reading} />)}
      </article>)}</div></section>
      <section className="market-chart-panel overview-events" aria-labelledby="brief-events">
        <h2 id="brief-events">{tText("Upcoming events")}</h2>
        <div className="overview-policy" aria-labelledby="brief-policy"><h3 id="brief-policy">{tText("Next FOMC decision")}</h3>
          <p><strong>{tText(model.policy.headline)}</strong></p>
          <a href={model.policy.fedwatchUrl} target="_blank" rel="noreferrer">{tText("View market probabilities on CME FedWatch")}</a>
        </div>
        <div className="overview-calendar" aria-labelledby="brief-calendar"><h3 id="brief-calendar">{tText("Upcoming releases - next 7 days")}</h3>
          <p className="market-note">{tText(data.calendar_start_date)} {tText(" through ")}{tText(data.calendar_end_date)} {tText(" (including today). Times in Poland.")}</p>
          {model.calendarItems.length || model.calendarGroups.length ? <>
            {model.calendarItems.length ? <ul>{model.calendarItems.map((event) => <li key={event}>{tText(event)}</li>)}</ul> : null}
            {model.calendarGroups.map((group) => <details key={group.name}><summary>{tText(group.summary)}</summary><ul>{group.events.map((event) => <li key={event}>{tText(event)}</li>)}</ul></details>)}
          </> : <p>{tText(model.calendar[0])}</p>}
          <a href="#/overview/calendar">{tText("View full calendar")}</a>
        </div>
        <details className="overview-event-details"><summary>{tText("Event sources and schedule details")}</summary>
          <p>{tText(model.policy.note)}</p><p>{tText(model.policy.metadata)}</p>
          <a href={model.policy.sourceUrl} target="_blank" rel="noreferrer">{tText("Official Federal Reserve FOMC calendar")}</a>
          {model.policy.timeSourceUrl ? <p><a href={model.policy.timeSourceUrl} target="_blank" rel="noreferrer">{tText("Official time source")}</a></p> : null}
          <p>{tText("Stored schedules may change. Refresh is separate from page loading.")}</p>
          <p>{tText(calendarNote)}</p><ul>{model.calendar.map((event) => <li key={event}>{tText(event)}</li>)}</ul>
        </details>
      </section>
    </main> : null}
  </>;
}
