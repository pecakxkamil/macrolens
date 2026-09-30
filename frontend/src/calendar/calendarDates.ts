import type { CalendarEvent } from "../api/macrolens";

export function todayIso(today = new Date()): string {
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseIso(date: string): Date {
  return new Date(`${date}T00:00:00Z`);
}

function iso(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function shiftDate(date: string, days: number): string {
  const shifted = parseIso(date);
  shifted.setUTCDate(shifted.getUTCDate() + days);
  return iso(shifted);
}

export function weekRange(anchor: string): { startDate: string; endDate: string } {
  const day = parseIso(anchor).getUTCDay();
  const startDate = shiftDate(anchor, -(day === 0 ? 6 : day - 1));
  return { startDate, endDate: shiftDate(startDate, 6) };
}

export function dateStatus(releaseDate: string, today: string): "Past" | "Today" | "Upcoming" {
  if (releaseDate < today) return "Past";
  if (releaseDate > today) return "Upcoming";
  return "Today";
}

export function formatAgendaDate(date: string): string {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "long", month: "short", day: "numeric", timeZone: "UTC",
  }).format(parseIso(date));
}

export function formatCalendarDate(date: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short", day: "numeric", year: "numeric", timeZone: "UTC",
  }).format(parseIso(date));
}

export function formatPolandTime(utcDateTime: string | null): string {
  if (!utcDateTime) return "Time unavailable";
  const instant = new Date(utcDateTime);
  if (Number.isNaN(instant.getTime())) return "Time unavailable";
  const time = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "Europe/Warsaw",
  }).format(instant);
  return `${time} PL`;
}

export function groupCalendarEvents(events: CalendarEvent[]): Array<{ date: string; events: CalendarEvent[] }> {
  const groups = new Map<string, CalendarEvent[]>();
  const importanceOrder = { high: 0, medium: 1, low: 2 };
  for (const event of [...events].sort((a, b) =>
    a.release_date.localeCompare(b.release_date)
    || importanceOrder[a.importance] - importanceOrder[b.importance]
    || a.release_name.localeCompare(b.release_name)
    || a.release_id - b.release_id
  )) {
    const group = groups.get(event.release_date) ?? [];
    group.push(event);
    groups.set(event.release_date, group);
  }
  return [...groups].map(([date, items]) => ({ date, events: items }));
}
