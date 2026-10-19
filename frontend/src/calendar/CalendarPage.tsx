import { tText, tLabel } from "../i18n/language";
import { useEffect, useState } from "react";
import {
  fetchCalendar,
  fetchReleaseDetail,
  fetchSeriesHistory,
  type CalendarEvent,
  type CalendarResponse,
  type HistoryResponse,
  type ReleaseDetailResponse,
  type SeriesMetadata,
} from "../api/macrolens";
import { rangeStartDate } from "../charts/chartData";
import { formatObservationDate } from "../format";
import { categoryLabel, formatIndicatorValue, indicatorCategories } from "../indicators/indicatorMetadata";
import { dateStatus, formatAgendaDate, formatCalendarDate, formatPolandTime, groupCalendarEvents, shiftDate, todayIso, weekRange } from "./calendarDates";

type LoadState<T> = { status: "loading" } | { status: "error" } | { status: "ready"; data: T };

function sourceUrl(value: string | null): string | null {
  return value && /^https?:\/\//i.test(value) ? value : null;
}

function ImportanceIndicator({ importance }: { importance: CalendarEvent["importance"] }) {
  const label = `${importance[0].toUpperCase()}${importance.slice(1)} importance`;
  return <span className={`calendar-importance calendar-importance--${importance}`}>
    <span className="calendar-importance__dot" aria-hidden="true" />{tText(label)}
  </span>;
}

function readingContext(history?: HistoryResponse | null): { latest?: { date: string; value: number }; previous?: { date: string; value: number } } {
  const readings = (history?.observations ?? [])
    .filter((item): item is typeof item & { value: number } => typeof item.value === "number" && Number.isFinite(item.value))
    .sort((a, b) => a.observation_date.localeCompare(b.observation_date));
  const latest = readings[readings.length - 1];
  const previous = readings[readings.length - 2];
  return {
    latest: latest ? { date: latest.observation_date, value: latest.value } : undefined,
    previous: previous ? { date: previous.observation_date, value: previous.value } : undefined,
  };
}

function ContextReading({ series, history }: { series: SeriesMetadata; history?: HistoryResponse | null }) {
  const { latest, previous } = readingContext(history);
  return (
    <div className="calendar-context-reading">
      <div><strong>{tText(series.short_name || series.name)}</strong><span>{tText(series.series_id)}</span></div>
      {history === undefined ? <p role="status">{tText("Loading readings...")}</p> : history === null ? <p>{tText("Readings unavailable.")}</p> : (
        <dl>
          <div><dt>{tText("Latest stored reading")}</dt><dd>{tText(latest ? formatIndicatorValue(latest.value, series, null) : "—")}</dd></div>
          <div><dt>{tText("Previous observation")}</dt><dd>{tText(previous ? formatIndicatorValue(previous.value, series, null) : "—")}</dd></div>
          <div><dt>{tText("Latest observation date")}</dt><dd>{tText(latest ? formatObservationDate(latest.date, series.frequency) : "—")}</dd></div>
        </dl>
      )}
      <a href={`#/explore/indicators/${encodeURIComponent(series.series_id)}`}>{tText("View indicator")}</a>
    </div>
  );
}

function ReleaseDetailPanel({ event }: { event: CalendarEvent }) {
  const [requestId, setRequestId] = useState(0);
  const [detail, setDetail] = useState<LoadState<ReleaseDetailResponse>>({ status: "loading" });
  const [histories, setHistories] = useState<Record<string, HistoryResponse | null>>({});

  useEffect(() => {
    const controller = new AbortController();
    setDetail({ status: "loading" });
    setHistories({});
    if (event.release_id === null) return () => controller.abort();
    fetchReleaseDetail(event.release_id, controller.signal)
      .then(async (data) => {
        if (controller.signal.aborted) return;
        setDetail({ status: "ready", data });
        const results = await Promise.allSettled(data.series.map((series) => fetchSeriesHistory(
          series.series_id,
          { startDate: rangeStartDate(3), signal: controller.signal },
        )));
        if (!controller.signal.aborted) {
          setHistories(Object.fromEntries(data.series.map((series, index) => [
            series.series_id,
            results[index].status === "fulfilled" ? results[index].value : null,
          ])));
        }
      })
      .catch(() => { if (!controller.signal.aborted) setDetail({ status: "error" }); });
    return () => controller.abort();
  }, [event.release_id, requestId]);

  return (
    <div className="calendar-release-detail" aria-label={tLabel(`${event.release_name} details`)}>
      {detail.status === "loading" ? <p role="status">{tText("Loading release details...")}</p> : null}
      {detail.status === "error" ? <div role="alert"><p>{tText("Unable to load release details.")}</p><button type="button" onClick={() => setRequestId((value) => value + 1)}>{tText("Retry details")}</button></div> : null}
      {detail.status === "ready" ? (
        <>
          <h4>{tText(detail.data.release_name)}</h4>
          <p>{tText("Release date: ")}{tText(formatCalendarDate(event.release_date))}</p>
          {sourceUrl(detail.data.source_link) ? <a href={sourceUrl(detail.data.source_link)!} target="_blank" rel="noopener noreferrer">{tText("Source link")}</a> : null}
          <p className="calendar-context-note">{tText("Readings below are latest stored current-vintage context. They are not historical release-vintage values.")}</p>
          <h5>{tText("Affected MacroLens indicators")}</h5>
          <div className="calendar-context-grid">{detail.data.series.map((series) => <ContextReading key={series.series_id} series={series} history={histories[series.series_id]} />)}</div>
        </>
      ) : null}
    </div>
  );
}

function ReleaseCard({ event, expanded, onToggle, today }: { event: CalendarEvent; expanded: boolean; onToggle: () => void; today: string }) {
  const status = dateStatus(event.release_date, today);
  const categories = event.event_type === "fomc_decision" ? ["financial_conditions"] : [...new Set(event.series.map((series) => series.category))];
  return (
    <article className={`calendar-release-card calendar-release-card--${status.toLowerCase()}`}>
      <div className="calendar-release-card__top">
        <div><h3>{tText(event.release_name)}</h3><span>{tText(formatCalendarDate(event.release_date))} {tText(" · ")}{tText(formatPolandTime(event.release_datetime_utc))}</span></div>
        <span className="calendar-status">{tText(status)}</span>
      </div>
      <ImportanceIndicator importance={event.importance} />
      <div className="calendar-category-badges">{categories.map((category) => <span key={category}>{tText(categoryLabel(category))}</span>)}</div>
      <ul className="calendar-series-list">{event.series.map((series) => <li key={series.series_id}><strong>{tText(series.series_id)}</strong><span>{tText(series.short_name || series.name)}</span></li>)}</ul>
      <div className="calendar-release-card__actions">
        <button type="button" aria-expanded={expanded} onClick={onToggle}>{tText(expanded ? "Hide details" : "View details")}</button>
        {sourceUrl(event.source_link) ? <a href={sourceUrl(event.source_link)!} target="_blank" rel="noopener noreferrer">{tText("Source")}</a> : null}
      </div>
      {expanded ? event.event_type === "fomc_decision" ? <div className="calendar-release-detail">
        <p>{tText("Official Federal Reserve policy decision; final day of the scheduled meeting.")}</p>
        <p>{tText("Meeting dates: ")}{event.meeting_start_date} {tText(" through ")}{event.meeting_end_date}</p>
        <p>{tText("Schedule retrieved: ")}{event.retrieved_at}</p>
        <p>{tText("Source timezone: ")}{event.source_timezone ?? tText("Time unavailable")}</p>
        {sourceUrl(event.time_source_url ?? null) ? <a href={event.time_source_url!} target="_blank" rel="noopener noreferrer">{tText("Official time source")}</a> : null}
        <p>{tText("Stored schedules may change. Refresh is separate from page loading.")}</p>
      </div> : <ReleaseDetailPanel key={`${event.release_id}-${event.release_date}`} event={event} /> : null}
    </article>
  );
}

export function CalendarPage() {
  const [anchor, setAnchor] = useState(todayIso);
  const [category, setCategory] = useState("all");
  const [requestId, setRequestId] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [response, setResponse] = useState<{ key: string; state: LoadState<CalendarResponse> }>({ key: "", state: { status: "loading" } });
  const { startDate, endDate } = weekRange(anchor);
  const requestKey = `${startDate}:${endDate}:${category}:${requestId}`;

  useEffect(() => {
    const controller = new AbortController();
    setResponse({ key: requestKey, state: { status: "loading" } });
    fetchCalendar(startDate, endDate, category === "all" ? undefined : category, controller.signal)
      .then((data) => { if (!controller.signal.aborted) setResponse({ key: requestKey, state: { status: "ready", data } }); })
      .catch(() => { if (!controller.signal.aborted) setResponse({ key: requestKey, state: { status: "error" } }); });
    return () => controller.abort();
  }, [requestKey]);

  const state = response.key === requestKey ? response.state : { status: "loading" } as const;
  const groups = state.status === "ready" ? groupCalendarEvents(state.data.events) : [];
  const today = todayIso();

  return (
    <main className="calendar-page">
      <header className="calendar-header">
        <p className="eyebrow">{tText("MacroLens")}</p>
        <h1>{tText("Macro Calendar")}</h1>
        <p className="subtitle">{tText("Scheduled US economic releases relevant to MacroLens indicators.")}</p>
      </header>
      <p className="calendar-notice">{tText("Release dates are sourced from FRED and underlying data providers. Scheduled times for supported releases come from official publisher schedules and may change; FRED does not guarantee publication times. Consensus estimates are not included. No trading signals.")}</p>
      <p className="calendar-notice">{tText("FOMC decisions use the separately stored official Federal Reserve schedule. Only explicitly confirmed times are shown.")}</p>
      {state.status === "ready" && state.data.policy_calendar && state.data.policy_calendar.status !== "available" ? <p className="calendar-notice">{tText("FOMC schedule unavailable; macro release coverage is shown separately.")}</p> : null}
      <p className="calendar-time-note">{tText("Times shown in Poland local time (Europe/Warsaw).")}</p>
      <div className="calendar-importance-legend" aria-label={tLabel("Release importance legend")}>
        <ImportanceIndicator importance="high" />
        <ImportanceIndicator importance="medium" />
        <ImportanceIndicator importance="low" />
        <span className="calendar-importance-legend__note">{tText("Colors indicate release importance, not market direction.")}</span>
      </div>
      <div className="calendar-controls">
        <div className="calendar-week-controls" role="group" aria-label={tLabel("Calendar week")}>
          <button type="button" onClick={() => { setAnchor(shiftDate(anchor, -7)); setSelected(null); }}>{tText("Previous week")}</button>
          <button type="button" onClick={() => { setAnchor(todayIso()); setSelected(null); }}>{tText("This week")}</button>
          <button type="button" onClick={() => { setAnchor(shiftDate(anchor, 7)); setSelected(null); }}>{tText("Next week")}</button>
        </div>
        <span className="calendar-week-label">{tText(formatCalendarDate(startDate))} {tText(" – ")}{tText(formatCalendarDate(endDate))}</span>
      </div>
      <div className="calendar-category-filters" role="group" aria-label={tLabel("Calendar category")}>
        {indicatorCategories.map((item) => <button key={item.id} type="button" aria-pressed={category === item.id} onClick={() => { setCategory(item.id); setSelected(null); }}>{tText(item.label)}</button>)}
      </div>
      {state.status === "loading" ? <div className="calendar-state" role="status">{tText("Loading calendar...")}</div> : null}
      {state.status === "error" ? <div className="calendar-state" role="alert"><p>{tText("Unable to load calendar.")}</p><button type="button" onClick={() => setRequestId((value) => value + 1)}>{tText("Retry")}</button></div> : null}
      {state.status === "ready" && !groups.length ? <div className="calendar-state">{tText("No tracked MacroLens releases in this period.")}</div> : null}
      {groups.map((group) => <section key={group.date} className="calendar-day" aria-label={tLabel(formatAgendaDate(group.date))}>
        <h2>{tText(formatAgendaDate(group.date))}</h2>
        <div className="calendar-day__events">{group.events.map((event) => {
          const key = event.event_id ?? `${event.release_id}:${event.release_date}`;
          return <ReleaseCard key={key} event={event} today={today} expanded={selected === key} onToggle={() => setSelected((current) => current === key ? null : key)} />;
        })}</div>
      </section>)}
    </main>
  );
}
