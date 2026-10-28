import type { CalendarEvent, EconomyBriefResponse } from "../api/macrolens";
import { getLocale } from "../i18n/language";
import { warsawDate } from "../datePeriods";
import { formatPolandTime, shiftDate } from "../calendar/calendarDates";

// Editorial selection order only; the calendar's importance metadata is unchanged.
export const overviewEventPriorities = [
  { key: "fomc", aliases: ["FOMC policy decision"], priority: "Key event" },
  { key: "fomc_press_conference", aliases: ["FOMC Press Conference"], priority: "Key event" },
  { key: "fomc_sep", aliases: ["Fed Economic Projections (SEP)"], priority: "Key event" },
  { key: "employment", aliases: ["Employment Situation"], priority: "Key event" },
  { key: "cpi", aliases: ["Consumer Price Index"], priority: "Key event" },
  { key: "pce", aliases: ["Personal Income and Outlays"], priority: "Key event" },
  { key: "gdp", aliases: ["Gross Domestic Product"], priority: "Key event" },
  { key: "ism_manufacturing", aliases: ["ISM Manufacturing PMI"], priority: "Key event" },
  { key: "ism_services", aliases: ["ISM Services PMI"], priority: "Key event" },
  { key: "michigan_preliminary", aliases: ["Michigan Consumer Sentiment — Preliminary"], priority: "Key event" },
  { key: "michigan_final", aliases: ["Michigan Consumer Sentiment — Final"], priority: "Tracked event" },
  { key: "retail", aliases: ["Advance Monthly Sales for Retail and Food Services"], priority: "Tracked event" },
  { key: "claims", aliases: ["Unemployment Insurance Weekly Claims Report"], priority: "Tracked event" },
  { key: "fomc_minutes", aliases: ["FOMC Meeting Minutes"], priority: "Tracked event" },
] as const;
export function eventPriority(event: CalendarEvent) {
  return event.event_type === "fomc_decision" ? overviewEventPriorities[0] : overviewEventPriorities.find(rule => rule.key===event.event_type || (rule.aliases as readonly string[]).includes(event.release_name));
}
export function eventInstant(event: CalendarEvent): number | null {
  const instant = event.release_datetime_utc ? Date.parse(event.release_datetime_utc) : NaN;
  return Number.isFinite(instant) ? instant : null;
}
export function eventDay(event: CalendarEvent): string {
  const instant = eventInstant(event);
  return instant === null ? event.release_date : warsawDate(new Date(instant));
}
export function eventIdentity(event: CalendarEvent): string {
  if(event.event_type?.startsWith('michigan_')&&event.event_id)return event.event_id;
  if(event.event_type?.startsWith('fomc_')&&event.event_type!=='fomc_decision'&&event.event_id)return event.event_id;
  return `${eventPriority(event)?.key ?? event.release_id ?? event.event_id ?? event.release_name}|${eventDay(event)}`;
}
export function eventDateLabel(event: CalendarEvent): string {
  return new Intl.DateTimeFormat(getLocale(), { weekday: "short", day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${eventDay(event)}T00:00:00Z`));
}
export function eventRelativeDay(event: CalendarEvent, now: Date): string | null {
  const today = warsawDate(now), day = eventDay(event);
  return day === today ? "Today" : day === shiftDate(today, 1) ? "Tomorrow" : null;
}
export function overviewUpcomingEvents(data: EconomyBriefResponse, now: Date = new Date()) {
  const available = data.calendar.status === "ready" && data.calendar.data !== null;
  const next = data.policy?.status === "ready" ? data.policy.data?.next_decision : null;
  const all = [...(available ? data.calendar.data!.events : []), ...(next ? [next] : [])];
  const unique = new Map<string, CalendarEvent>();
  for (const event of all) {
    const key = eventIdentity(event), prior = unique.get(key);
    // Keep confirmed timing when a duplicate representation has no time.
    if (!prior || eventInstant(event) !== null || eventInstant(prior) === null) unique.set(key, event);
  }
  const future = [...unique.values()].filter(event => {
    const instant = eventInstant(event);
    return instant === null ? eventDay(event) >= warsawDate(now) : instant > now.getTime();
  });
  const chronological = (a: CalendarEvent, b: CalendarEvent) => eventDay(a).localeCompare(eventDay(b))
    || (eventInstant(a) ?? Infinity) - (eventInstant(b) ?? Infinity) || a.release_name.localeCompare(b.release_name);
  const inWindow = future.filter(event => eventDay(event) >= data.calendar_start_date && eventDay(event) <= data.calendar_end_date);
  const selected = inWindow.filter(event => eventPriority(event)).sort((a, b) =>
    overviewEventPriorities.findIndex(rule => rule === eventPriority(a)) - overviewEventPriorities.findIndex(rule => rule === eventPriority(b))
    || chronological(a, b)).slice(0, 4).sort(chronological);
  const selectedIds = new Set(selected.map(eventIdentity));
  const nextFomc = future.filter(event => eventPriority(event)?.key === "fomc").sort(chronological)[0];
  return { available, selected, remaining: inWindow.filter(event => !selectedIds.has(eventIdentity(event))).sort(chronological),
    nextFomc: nextFomc && !selectedIds.has(eventIdentity(nextFomc)) ? nextFomc : null };
}
export function upcomingEventReport(event: CalendarEvent): string {
  if(event.event_type?.startsWith('michigan_'))return `${event.release_name} (${event.reference_period}) - ${eventDateLabel(event)} [${eventDay(event)}] - ${formatPolandTime(event.release_datetime_utc)}. ${eventPriority(event)?.priority}. Numerical results are not integrated. Official reports: ${event.publisher_reports_url}.`;
  return `${event.release_name} - ${eventDateLabel(event)} [${eventDay(event)}] - ${formatPolandTime(event.release_datetime_utc)}. ${eventPriority(event)?.priority ?? "Other event"}.`;
}

// Overview editorial tiers take precedence; source importance is never mutated.
const overviewStars = { "Key event": 3, "Tracked event": 2 } as const;
const sourceStars: Record<string, number> = { high: 3, medium: 2, low: 1 };
export function eventImportanceStars(event: CalendarEvent): number | null {
  const priority = eventPriority(event);
  return priority ? overviewStars[priority.priority] : sourceStars[event.importance] ?? null;
}
export const eventImportanceNote = "MacroLens Overview stars: key editorial events, including both ISM PMI reports and Michigan Preliminary, = 3; tracked editorial events (including Retail Sales, weekly Claims and Michigan Final) = 2. Otherwise source importance maps high = 3, medium = 2, low = 1; unknown importance is unavailable. Editorial tiers take precedence without changing source classes. This is not an Investing.com rating or a forecast of market impact.";
export function eventShortDateLabel(event: CalendarEvent): string {
  return new Intl.DateTimeFormat(getLocale(), { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(`${eventDay(event)}T00:00:00Z`));
}
