import { afterEach, expect, test } from "vitest";
import type { CalendarEvent, EconomyBriefResponse } from "../api/macrolens";
import { eventImportanceStars, eventDay, eventPriority, eventRelativeDay, overviewEventPriorities, overviewUpcomingEvents, upcomingEventReport } from "./upcomingEvents";
import { setLanguage } from "../i18n/language";

const now = new Date("2026-10-18T12:00:00Z");
function event(name: string, date = "2026-10-20", extra: Partial<CalendarEvent> = {}): CalendarEvent {
  return { release_id: 1, release_name: name, release_date: date, release_datetime_utc: null, release_time: null, source_timezone: null, source_link: null, importance: "medium", date_precision: "date", series: [], ...extra };
}
function data(events: CalendarEvent[], next: CalendarEvent | null = null): EconomyBriefResponse {
  return { calendar_start_date: "2026-10-18", calendar_end_date: "2026-10-24", calendar: {status: "ready", data: {events}}, policy: {status: "ready", data: {next_decision: next}} } as EconomyBriefResponse;
}
afterEach(() => setLanguage("en"));

test.each(overviewEventPriorities)("explicit alias for $key has its configured priority", rule => {
  expect(eventPriority(event(rule.aliases[0]))).toBe(rule);
});
test("unknown, PMI, FOMC minutes and partial source names are not promoted", () => {
  for (const name of ["ISM PMI", "CPI", "Consumer Price Index details", "FOMC minutes", "H.15 Selected Interest Rates"]) expect(eventPriority(event(name))).toBeUndefined();
  expect(eventPriority(event("Official policy meeting", "2026-10-20", {event_type: "fomc_decision"}))?.key).toBe("fomc");
});
test("select at most four by editorial priority, then display in date order", () => {
  const events = [event("Unemployment Insurance Weekly Claims Report", "2026-10-18"), event("Advance Monthly Sales for Retail and Food Services", "2026-10-19"), event("Employment Situation", "2026-10-23"), event("Consumer Price Index", "2026-10-20"), event("Personal Income and Outlays", "2026-10-22"), event("Gross Domestic Product", "2026-10-21")];
  const result = overviewUpcomingEvents(data(events), now);
  expect(result.selected.map(e => e.release_name)).toEqual(["Consumer Price Index", "Gross Domestic Product", "Personal Income and Outlays", "Employment Situation"]);
  expect(result.remaining).toHaveLength(2); expect(events[0].importance).toBe("medium");
});
test("FOMC in the seven-day window appears once even in calendar and policy payloads", () => {
  const fomc = event("FOMC policy decision", "2026-10-21", {event_type: "fomc_decision", event_id: "fomc:2026-10-21", release_id: null});
  const result = overviewUpcomingEvents(data([fomc, {...fomc}], fomc), now);
  expect(result.selected).toHaveLength(1); expect(result.nextFomc).toBeNull(); expect(result.remaining).toEqual([]);
});
test("out-of-window macro releases are excluded, next FOMC is separate", () => {
  const fomc = event("FOMC policy decision", "2026-10-28", {event_type: "fomc_decision"});
  const result = overviewUpcomingEvents(data([event("Employment Situation", "2026-10-25"), event("Consumer Price Index", "2026-10-17")], fomc), now);
  expect(result.selected).toEqual([]); expect(result.remaining).toEqual([]); expect(result.nextFomc).toEqual(fomc);
});
test("one employment release covering payrolls and unemployment stays one event", () => {
  const employment = event("Employment Situation", "2026-10-20", {series: [{series_id: "PAYEMS"}, {series_id: "UNRATE"}] as CalendarEvent["series"]});
  expect(overviewUpcomingEvents(data([employment, employment]), now).selected).toHaveLength(1);
});
test("routine and unrecognized high-importance releases never fill the featured slots", () => {
  const result = overviewUpcomingEvents(data([event("H.15 Selected Interest Rates"), event("Unknown release", "2026-10-22", {importance: "high"})]), now);
  expect(result.selected).toEqual([]); expect(result.remaining).toHaveLength(2);
});
test("known elapsed times including FOMC disappear; unknown times stay on their source day", () => {
  const due = event("Consumer Price Index", "2026-10-18", {release_datetime_utc: now.toISOString()});
  const pastFomc = {...due, release_name: "FOMC policy decision", event_type: "fomc_decision" as const};
  const unknown = event("Gross Domestic Product", "2026-10-18");
  const result = overviewUpcomingEvents(data([due, event("Personal Income and Outlays", "2026-10-18", {release_datetime_utc: "2026-10-18T12:00:01Z"}), unknown], pastFomc), now);
  expect(result.selected.map(e => e.release_name)).toEqual(["Personal Income and Outlays", "Gross Domestic Product"]); expect(result.nextFomc).toBeNull();
  expect(upcomingEventReport(unknown)).toContain("Time unavailable");
});
test("null timing on a duplicate never overrides a confirmed source time", () => {
  const known = event("FOMC policy decision", "2026-10-21", {event_type: "fomc_decision", release_datetime_utc: "2026-10-21T18:00:00Z"});
  const result = overviewUpcomingEvents(data([known], {...known, release_datetime_utc: null}), now);
  expect(result.selected[0].release_datetime_utc).toBe("2026-10-21T18:00:00Z");
});
test("empty calendar and unavailable calendar remain distinct, independent of FOMC", () => {
  expect(overviewUpcomingEvents(data([]), now).available).toBe(true);
  const payload = data([], event("FOMC policy decision", "2026-10-28", {event_type: "fomc_decision"}));
  payload.calendar = {status: "unavailable", data: null, error: "offline"};
  const result = overviewUpcomingEvents(payload, now); expect(result.available).toBe(false); expect(result.nextFomc).not.toBeNull();
});
test("Warsaw dates, weekday, Today/Tomorrow and DST use timezone APIs", () => {
  const e = event("Consumer Price Index", "2026-03-16", {release_datetime_utc: "2026-03-16T12:30:00Z"});
  expect(upcomingEventReport(e)).toContain("Mon, Mar 16, 2026"); expect(upcomingEventReport(e)).toContain("13:30 PL");
  expect(upcomingEventReport({...e, release_date: "2026-10-20", release_datetime_utc: "2026-10-20T12:30:00Z"})).toContain("14:30 PL");
  const midnight = new Date("2026-10-18T22:30:00Z");
  expect(eventRelativeDay(event("Consumer Price Index", "2026-10-19"), midnight)).toBe("Today");
  expect(eventRelativeDay(event("Consumer Price Index", "2026-10-20"), midnight)).toBe("Tomorrow");
  expect(eventDay({...e, release_datetime_utc: "2026-10-18T23:30:00Z"})).toBe("2026-10-19");
  setLanguage("pl"); expect(upcomingEventReport(e)).toContain("13:30 PL");
});

test.each(overviewEventPriorities)("$key star presentation follows the editorial tier without mutating its source class", rule => {
  const e = event(rule.aliases[0], "2026-10-20", {importance: "high"});
  expect(eventImportanceStars(e)).toBe(rule.priority === "Key event" ? 3 : 2);
  expect(e.importance).toBe("high");
});
test.each([["high",3], ["medium",2], ["low",1], ["unknown",null], [undefined,null]] as const)("source class %s maps explicitly to %s for unconfigured events", (importance, stars) => {
  const e = event("Unconfigured release"); Object.assign(e, {importance});
  expect(eventImportanceStars(e)).toBe(stars);
});
