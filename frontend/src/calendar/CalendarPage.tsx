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
    <span className="calendar-importance__dot" aria-hidden="true" />{label}
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
      <div><strong>{series.short_name || series.name}</strong><span>{series.series_id}</span></div>
      {history === undefined ? <p role="status">Loading readings...</p> : history === null ? <p>Readings unavailable.</p> : (
        <dl>
          <div><dt>Latest stored reading</dt><dd>{latest ? formatIndicatorValue(latest.value, series, null) : "—"}</dd></div>
          <div><dt>Previous observation</dt><dd>{previous ? formatIndicatorValue(previous.value, series, null) : "—"}</dd></div>
          <div><dt>Latest observation date</dt><dd>{latest ? formatObservationDate(latest.date, series.frequency) : "—"}</dd></div>
        </dl>
      )}
      <a href={`#/indicators/${encodeURIComponent(series.series_id)}`}>View indicator</a>
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
    <div className="calendar-release-detail" aria-label={`${event.release_name} details`}>
      {detail.status === "loading" ? <p role="status">Loading release details...</p> : null}
      {detail.status === "error" ? <div role="alert"><p>Unable to load release details.</p><button type="button" onClick={() => setRequestId((value) => value + 1)}>Retry details</button></div> : null}
      {detail.status === "ready" ? (
        <>
          <h4>{detail.data.release_name}</h4>
          <p>Release date: {formatCalendarDate(event.release_date)}</p>
          {sourceUrl(detail.data.source_link) ? <a href={sourceUrl(detail.data.source_link)!} target="_blank" rel="noopener noreferrer">Source link</a> : null}
          <p className="calendar-context-note">Readings below are latest stored current-vintage context. They are not historical release-vintage values.</p>
          <h5>Affected MacroLens indicators</h5>
          <div className="calendar-context-grid">{detail.data.series.map((series) => <ContextReading key={series.series_id} series={series} history={histories[series.series_id]} />)}</div>
        </>
      ) : null}
    </div>
  );
}

function ReleaseCard({ event, expanded, onToggle, today }: { event: CalendarEvent; expanded: boolean; onToggle: () => void; today: string }) {
  const status = dateStatus(event.release_date, today);
  const categories = [...new Set(event.series.map((series) => series.category))];
  return (
    <article className={`calendar-release-card calendar-release-card--${status.toLowerCase()}`}>
      <div className="calendar-release-card__top">
        <div><h3>{event.release_name}</h3><span>{formatCalendarDate(event.release_date)} · {formatPolandTime(event.release_datetime_utc)}</span></div>
        <span className="calendar-status">{status}</span>
      </div>
      <ImportanceIndicator importance={event.importance} />
      <div className="calendar-category-badges">{categories.map((category) => <span key={category}>{categoryLabel(category)}</span>)}</div>
      <ul className="calendar-series-list">{event.series.map((series) => <li key={series.series_id}><strong>{series.series_id}</strong><span>{series.short_name || series.name}</span></li>)}</ul>
      <div className="calendar-release-card__actions">
        <button type="button" aria-expanded={expanded} onClick={onToggle}>{expanded ? "Hide details" : "View details"}</button>
        {sourceUrl(event.source_link) ? <a href={sourceUrl(event.source_link)!} target="_blank" rel="noopener noreferrer">Source</a> : null}
      </div>
      {expanded ? <ReleaseDetailPanel key={`${event.release_id}-${event.release_date}`} event={event} /> : null}
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
        <p className="eyebrow">MacroLens</p>
        <h1>Macro Calendar</h1>
        <p className="subtitle">Scheduled US economic releases relevant to MacroLens indicators.</p>
      </header>
      <p className="calendar-notice">Release dates are sourced from FRED and underlying data providers. Scheduled times for supported releases come from official publisher schedules and may change; FRED does not guarantee publication times. Consensus estimates are not included. No trading signals.</p>
      <p className="calendar-time-note">Times shown in Poland local time (Europe/Warsaw).</p>
      <div className="calendar-importance-legend" aria-label="Release importance legend">
        <ImportanceIndicator importance="high" />
        <ImportanceIndicator importance="medium" />
        <ImportanceIndicator importance="low" />
        <span className="calendar-importance-legend__note">Colors indicate release importance, not market direction.</span>
      </div>
      <div className="calendar-controls">
        <div className="calendar-week-controls" role="group" aria-label="Calendar week">
          <button type="button" onClick={() => { setAnchor(shiftDate(anchor, -7)); setSelected(null); }}>Previous week</button>
          <button type="button" onClick={() => { setAnchor(todayIso()); setSelected(null); }}>This week</button>
          <button type="button" onClick={() => { setAnchor(shiftDate(anchor, 7)); setSelected(null); }}>Next week</button>
        </div>
        <span className="calendar-week-label">{formatCalendarDate(startDate)} – {formatCalendarDate(endDate)}</span>
      </div>
      <div className="calendar-category-filters" role="group" aria-label="Calendar category">
        {indicatorCategories.map((item) => <button key={item.id} type="button" aria-pressed={category === item.id} onClick={() => { setCategory(item.id); setSelected(null); }}>{item.label}</button>)}
      </div>
      {state.status === "loading" ? <div className="calendar-state" role="status">Loading calendar...</div> : null}
      {state.status === "error" ? <div className="calendar-state" role="alert"><p>Unable to load calendar.</p><button type="button" onClick={() => setRequestId((value) => value + 1)}>Retry</button></div> : null}
      {state.status === "ready" && !groups.length ? <div className="calendar-state">No tracked MacroLens releases in this period.</div> : null}
      {groups.map((group) => <section key={group.date} className="calendar-day" aria-label={formatAgendaDate(group.date)}>
        <h2>{formatAgendaDate(group.date)}</h2>
        <div className="calendar-day__events">{group.events.map((event) => {
          const key = `${event.release_id}:${event.release_date}`;
          return <ReleaseCard key={key} event={event} today={today} expanded={selected === key} onToggle={() => setSelected((current) => current === key ? null : key)} />;
        })}</div>
      </section>)}
    </main>
  );
}
