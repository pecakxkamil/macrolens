import { useOverviewRefresh } from "./useOverviewRefresh";
import { SourceCheckStatus } from "./SourceCheckStatus";
import { economicInterpretation, fedDecisionMarkers } from "./economicInterpretation";
import { InterpretationMarker } from "./InterpretationMarker";
import { ReadingChartDialog, readingPreview, fedPreview, type PreviewChart } from "./ReadingChartDialog";
import { EconomicExplanationTooltip } from "./EconomicExplanationTooltip";
import { economicExplanation, fedExplanation } from "./economicExplanations";
import { readingHoverLines, readingHoverText } from "./readingHoverText";
import { InfoTooltip } from "../components/InfoTooltip";
import { tText, tLabel } from "../i18n/language";
import { useEffect, useState } from "react";
import { fetchEconomyBrief, type EconomyBriefResponse } from "../api/macrolens";
import { briefMarkdown, briefModel } from "./briefModel";
import type { PreparedFedTarget } from "./fedTarget";
import { eventShortDateLabel, eventDay, eventIdentity, eventImportanceStars } from "./upcomingEvents";
import { formatPolandTime } from "../calendar/calendarDates";
import type { CalendarEvent } from "../api/macrolens";
import type { PreparedReading } from "./readingComparisons";
import { formatObservationDate } from "../format";

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
function OverviewLegend() {
  const directions = [["\u2191", "Higher than previous", "positive"], ["\u2193", "Lower than previous", "negative"], ["\u2014", "No visible change", "neutral"]];
  const interpretations = [["+", "Usually favorable", "favorable"], ["\u2212", "Usually unfavorable", "unfavorable"], ["\u00b1", "Mixed / context-dependent", "mixed"]];
  return <aside className="overview-symbol-legend" aria-label={tLabel("Change legend")}>
    <div role="group" aria-label={tLabel("Reading change")}><span className="overview-legend-heading">{tText("Reading change")}</span>
      <ul>{directions.map(([symbol,label,tone])=><li key={symbol}><span aria-hidden="true" className={`overview-legend-symbol overview-change--${tone}`}>{symbol}</span><span>{tText(label)}</span></li>)}</ul>
    </div>
    <div role="group" aria-label={tLabel("For the economic area")}><span className="overview-legend-heading">{tText("For the economic area")}</span>
      <ul>{interpretations.map(([symbol,label,tone])=><li key={symbol}><span aria-hidden="true" className={`overview-legend-symbol overview-interpretation--${tone}`}>{symbol}</span><span>{tText(label)}</span></li>)}</ul>
    </div>
  </aside>;
}
function ChartButton({ title, onClick }: {title:string;onClick:()=>void}) {
  return <button type="button" className="overview-chart-button" aria-label={tLabel(`View chart: ${title}`)} title={tLabel(`View chart: ${title}`)} onClick={onClick}>
    <svg aria-hidden="true" width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v14h14M5 12l4-4 3 2 4-6" /></svg>
  </button>;
}
function ReadingRow({ reading, onChart, explanations }: { reading: PreparedReading;onChart:()=>void;explanations:boolean }) {
  const interpretation = economicInterpretation(reading);
  const directionLabel = ({higher:"Higher reading",lower:"Lower reading",unchanged:"No change in reading",unavailable:"Comparison unavailable"})[reading.comparison];
  const value = (point: PreparedReading["current"]) => {
    // Compact screen units only; the model retains full tooltip/report units.
    const suffix = reading.key === "initial_claims" || reading.raw?.unit === "index" || point.value === "\u2014" ? ""
      : reading.raw?.unit === "percentage points" ? " pp" : point.screenSuffix || ` ${reading.unit}`;
    return <strong><span className="overview-number">{point.screenValue}</span>{suffix ? <small className="overview-inline-unit">{reading.raw?.unit === "percentage points" ? suffix : tText(suffix)}</small> : null}</strong>;
  };
  return <tr className={`overview-reading-row${reading.raw?.unit === "index" ? " overview-reading-row--index" : ""}`} aria-label={tLabel(reading.label)}>
    <th scope="row"><div className="overview-reading-heading"><a href={reading.indicatorHref}>{tText(reading.label)}</a><span className="overview-reading-actions"><ChartButton title={reading.label} onClick={onChart} />{explanations ? <span className="overview-explanation"><EconomicExplanationTooltip label={`${reading.label}: Economic meaning`} explanation={economicExplanation(reading)} /></span> : null}</span></div><div className="overview-period"><time dateTime={reading.current.date}>{tText(reading.current.period)}</time></div></th>
    <td className="overview-value--latest"><div className="overview-value"><div className="overview-reading-number">{value(reading.current)}{reading.current.yoy !== undefined ? <small className="overview-yoy">{tText(reading.current.yoy)}{reading.current.yoy === "\u2014" ? "" : "%"} {tText("YoY")}</small> : null}</div><span className={`overview-change overview-change--${reading.tone}`}>
      <InfoTooltip label={`${reading.label}: ${reading.labels.change} - ${directionLabel}`} description={readingHoverText(reading)} trigger={reading.arrow} closable
        content={<span className="reading-change-details">{readingHoverLines(reading).map((line, index) => <span key={index}>{index > 0 ? " " : ""}{tText(line)}</span>)}</span>} />
    </span><InterpretationMarker label={reading.label} interpretation={interpretation} /></div></td>
    <td className="overview-value--earlier">{value(reading.previous)}<time dateTime={reading.previous.date}>{tText(reading.previous.period)}</time></td>
  </tr>;
}

function EventRow({ event }: { event: CalendarEvent }) {
  const stars = eventImportanceStars(event);
  return <li className="overview-event">
    <time dateTime={event.release_datetime_utc ?? eventDay(event)}>{tText(eventShortDateLabel(event))} · {tText(formatPolandTime(event.release_datetime_utc))}</time>
    <strong>{tText(event.release_name)}{(event.event_type?.startsWith('michigan_')||event.event_type==='adp_monthly')?<> ({event.reference_period?formatObservationDate(event.reference_period,'monthly'):tText('Reference period unconfirmed')})<br/><a href={event.document_url??event.publisher_reports_url} target="_blank" rel="noreferrer">{tText(event.document_status==='available'&&event.document_url?'Data at publisher':'Publisher reports')}</a></>:null}{(event.event_type==='empire_state'||event.event_type==='ft900')&&event.usage_rights?<small>{event.reference_period?formatObservationDate(event.reference_period,'monthly'):''} · {event.usage_rights.copyright} <a href={event.usage_rights.original_url} target="_blank" rel="noreferrer">{tText(event.event_type==='ft900'?'Official Exhibit 1 XLSX':'Original NY Fed CSV')}</a>{' · '}<a href={event.usage_rights.terms_url} target="_blank" rel="noreferrer">{tText(event.event_type==='ft900'?'BEA data use policy':'NY Fed Terms of Use')}</a> · {tText(event.usage_rights.modifications)}</small>:null}</strong>

    <span className="overview-event-stars" role="img" aria-label={tLabel(stars === null ? "Importance unavailable" : `Importance ${stars} of 3`)}><span aria-hidden="true">{stars === null ? "\u2014" : "\u2605".repeat(stars)}</span></span>
  </li>;
}

function FedTargetBlock({ target, onChart, explanations }: { target: PreparedFedTarget;onChart:()=>void;explanations:boolean }) {
  const decision = fedDecisionMarkers(target);
  return <section className="overview-fed-target" aria-label={tLabel("Fed target range")}>
    <h3 className="overview-reading-heading"><a href="#/explore/indicators/DFEDTARL">{tText("Fed target range")}</a><span className="overview-reading-actions"><ChartButton title="Fed target range" onClick={onChart} />{explanations ? <span className="overview-explanation"><EconomicExplanationTooltip label="Fed target range: Economic meaning" explanation={fedExplanation(target)} /></span> : null}</span></h3><strong className="overview-target-value">{tText(target.range)}</strong>
    <dl><div><dt>{tText("Effective since")}</dt><dd>{tText(target.effective)}</dd></div>
      <div><dt>{tText("Last rate change")}</dt><dd className="overview-fed-last-change">{tText(target.lastChange)}{decision ? <><span className={`overview-change overview-change--${decision.tone}`} role="img" aria-label={tLabel(`Last recorded rate change: ${decision.tone === "positive" ? "higher" : "lower"} target range`)}>{decision.arrow}</span><InterpretationMarker label="Last recorded rate change" interpretation={decision.interpretation} /></> : null}</dd></div></dl>
  </section>;
}

export function EconomyBrief({explanations=false}: {explanations?:boolean} = {}) {
  const [preview,setPreview] = useState<{chart:PreviewChart|null;title:string}>();
  const [now, setNow] = useState(() => new Date());
  useEffect(() => { const timer = window.setInterval(() => setNow(new Date()), 30_000); return () => window.clearInterval(timer); }, []);
  const [storedData, setData] = useState<EconomyBriefResponse>();
  const refresh = useOverviewRefresh(storedData, setData);
  const data = storedData ? {...storedData, refresh: refresh ?? storedData.refresh} : undefined;
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setData(undefined); setError(false);
    fetchEconomyBrief(controller.signal).then((value) => { if (!controller.signal.aborted) setData(value); })
      .catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [retry]);
  const model = data ? briefModel(data, undefined, now) : undefined;
  return <>
    <header className="page-header overview-header"><div className="overview-title"><h1>{tText("USA Economy Now")}</h1><SourceCheckStatus checks={data?.source_checks} refresh={data?.refresh} unsupported={data?.automatic_refresh_supported===false} /></div>
      <div className="overview-header-actions"><OverviewLegend /><button type="button" disabled={!model} onClick={() => { if (model && data) { const generatedAt = new Date().toISOString(); downloadReport(briefMarkdown(model, data, generatedAt), generatedAt); } }}>{tText("Download report")}</button></div>
    </header>
    {!data && !error ? <p className="loading-panel">{tText("Loading Economy Brief...")}</p> : null}
    {error ? <div className="error-panel" role="alert"><p>{tText("Economy Brief is unavailable. Check the API and try again.")}</p><button onClick={() => setRetry((value) => value + 1)}>{tText("Retry brief")}</button></div> : null}
    {data && model ? <main className="economy-brief">
      <div className="overview-data-note"><p>{tText("Data sources:")} <a href="https://fred.stlouisfed.org/" target="_blank" rel="noreferrer">FRED</a>, <a href="https://www.ismworld.org/" target="_blank" rel="noreferrer">ISM</a>, <a href="https://www.federalreserve.gov/" target="_blank" rel="noreferrer">{tText("Federal Reserve")}</a>.</p>
        {data.reading_comparisons?.status !== "ready" ? <p role="status">{tText("Reading comparisons unavailable.")}</p> : model.domains.some((domain) => domain.compact.some((reading) => !reading.raw?.current)) ? <p role="status">{tText("Some readings unavailable.")}</p> : null}
      </div>
      <section aria-label={tLabel("Economy across six domains")}><div className="brief-grid">{model.domains.map((domain) => <article key={domain.key} className="domain-card overview-domain" aria-label={tLabel(`${domain.name} brief`)}>
        <h2>{tText(domain.name)}</h2>{domain.freshnessIssues.map(reading => <p role="status" className="market-note" key={reading.key}>{tText(`${reading.label}: Newer stored period ${reading.raw!.latest_stored_observation_date} has no available reading.`)}</p>)}
        {domain.key === "financial_conditions" ? <FedTargetBlock explanations={explanations} target={model.fedTarget} onChart={()=>setPreview({chart:fedPreview,title:"Fed target range"})} /> : null}
        <table className="overview-domain-table" aria-label={tLabel(`${domain.name} readings`)}><colgroup><col style={{ width: "41.5%" }} /><col style={{ width: "37%" }} /><col style={{ width: "21.5%" }} /></colgroup>
          <thead><tr><th scope="col">{tText("Indicator")}</th><th scope="col">{tText("Currently")}</th><th scope="col">{tText("Previous")}</th></tr></thead>
          <tbody>{domain.compact.map(reading => <ReadingRow key={reading.key} explanations={explanations} reading={reading} onChart={()=>setPreview({chart:readingPreview(reading),title:reading.label})} />)}</tbody>
        </table>
      </article>)}</div></section>
      <section className="market-chart-panel overview-events" aria-labelledby="brief-events">
        <h2 id="brief-events">{tText("Upcoming events")}</h2>
        <p className="market-note overview-event-window">{tText("Next 7 days")}</p>
        <div className="overview-calendar" aria-labelledby="brief-calendar"><h3 id="brief-calendar" className="visually-hidden">{tText("Upcoming releases - next 7 days")}</h3>
          {!model.upcoming.available ? <p role="status">{tText("Release calendar unavailable; upcoming coverage is unknown.")}</p> : null}
          {model.upcoming.selected.length ? <ul className="overview-event-list">{model.upcoming.selected.map(event => <EventRow key={eventIdentity(event)} event={event} />)}</ul> : model.upcoming.available ? <p>{tText("No key upcoming events in the stored 7-day window.")}</p> : null}
        </div>
        {model.upcoming.nextFomc ? <div className="overview-policy" aria-labelledby="brief-policy"><h3 id="brief-policy">{tText("Next FOMC decision")}</h3><ul className="overview-event-list"><EventRow event={model.upcoming.nextFomc} /></ul></div> : null}

        <a className="overview-full-calendar" href="#/calendar">{tText("View full calendar")}</a>
      </section>
    </main> : null}
    {preview ? <ReadingChartDialog publicationId={data?.data_revision} chart={preview.chart} title={preview.title} onClose={()=>setPreview(undefined)} /> : null}
  </>;
}
