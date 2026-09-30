import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import App from "../App";
import type { CalendarEvent, SeriesMetadata } from "../api/macrolens";
import { dateStatus, formatPolandTime, groupCalendarEvents, shiftDate, todayIso, weekRange } from "./calendarDates";

const cpi: SeriesMetadata = { series_id: "CPIAUCSL", name: "Consumer Price Index", short_name: "CPI", category: "inflation", frequency: "monthly", unit: "index" };
const core: SeriesMetadata = { series_id: "CPILFESL", name: "Core Consumer Price Index", short_name: "Core CPI", category: "inflation", frequency: "monthly", unit: "index" };
const unemployment: SeriesMetadata = { series_id: "UNRATE", name: "Unemployment Rate", short_name: "Unemployment Rate", category: "labor", frequency: "monthly", unit: "percent" };

function events(): CalendarEvent[] {
  const today = todayIso();
  return [
    { release_id: 10, release_name: "Consumer Price Index", release_date: shiftDate(today, -1), release_time: "08:30:00", source_timezone: "America/New_York", release_datetime_utc: "2026-09-29T12:30:00Z", importance: "high", source_link: "https://www.bls.gov/cpi/", date_precision: "date", series: [cpi, core] },
    { release_id: 30, release_name: "Another Labor Release", release_date: today, release_time: null, source_timezone: null, release_datetime_utc: null, importance: "medium", source_link: null, date_precision: "date", series: [unemployment] },
    { release_id: 50, release_name: "H.15 Selected Interest Rates", release_date: today, release_time: null, source_timezone: null, release_datetime_utc: null, importance: "low", source_link: null, date_precision: "date", series: [unemployment] },
    { release_id: 20, release_name: "Employment Situation", release_date: today, release_time: "08:30:00", source_timezone: "America/New_York", release_datetime_utc: "2026-09-30T12:30:00Z", importance: "high", source_link: null, date_precision: "date", series: [unemployment] },
    { release_id: 40, release_name: "Upcoming Activity Release", release_date: shiftDate(today, 1), release_time: null, source_timezone: null, release_datetime_utc: null, importance: "medium", source_link: null, date_precision: "date", series: [unemployment] },
  ];
}

function mockApi(mode: "ready" | "loading" | "error" | "empty" = "ready") {
  const fetchMock = vi.fn().mockImplementation((input: string | URL) => {
    const url = new URL(String(input));
    if (url.pathname === "/api/v1/calendar") {
      if (mode === "loading") return new Promise(() => undefined);
      if (mode === "error") return Promise.resolve({ ok: false });
      const category = url.searchParams.get("category");
      const selected = mode === "empty" ? [] : events().filter((event) => !category || event.series.some((series) => series.category === category));
      return Promise.resolve({ ok: true, json: async () => ({
        start_date: url.searchParams.get("start_date"), end_date: url.searchParams.get("end_date"), category,
        events: selected,
      }) });
    }
    if (url.pathname.startsWith("/api/v1/releases/")) {
      const releaseId = Number(url.pathname.split("/").pop());
      const event = events().find((item) => item.release_id === releaseId)!;
      return Promise.resolve({ ok: true, json: async () => ({
        release_id: releaseId, release_name: event.release_name, source_link: event.source_link,
        press_release: true, date_precision: "date", series: event.series, recent_dates: [event.release_date],
      }) });
    }
    if (url.pathname.endsWith("/history")) {
      return Promise.resolve({ ok: true, json: async () => ({
        history_type: "current_vintage", observations: [
          { observation_date: "2026-07-01", value: 4.0 },
          { observation_date: "2026-08-01", value: 4.1 },
        ],
      }) });
    }
    return new Promise(() => undefined);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function openCalendar() {
  window.location.hash = "#/calendar";
  render(<App />);
}

afterEach(() => {
  cleanup();
  window.location.hash = "";
  vi.unstubAllGlobals();
});

describe("Macro Calendar v1", () => {
  test("navigation and page title render with time-source explanation", async () => {
    mockApi();
    window.location.hash = "#/";
    render(<App />);
    fireEvent.click(screen.getByRole("link", { name: "Calendar" }));
    expect(await screen.findByRole("heading", { name: "Macro Calendar" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Calendar" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText(/Release dates are sourced from FRED/)).toHaveTextContent("FRED does not guarantee publication times");
    expect(screen.getByText("Times shown in Poland local time (Europe/Warsaw).")).toBeInTheDocument();
  });

  test("Poland time conversion handles US and Polish DST transitions", () => {
    expect(formatPolandTime("2026-09-30T12:30:00Z")).toBe("14:30 PL");
    expect(formatPolandTime("2026-03-13T12:30:00Z")).toBe("13:30 PL");
    expect(formatPolandTime("2026-10-29T12:30:00Z")).toBe("13:30 PL");
    expect(formatPolandTime("2026-01-15T13:30:00Z")).toBe("14:30 PL");
    expect(formatPolandTime(null)).toBe("Time unavailable");
  });

  test("known time appears beside date and unknown time stays unavailable", async () => {
    mockApi();
    openCalendar();
    const known = (await screen.findByRole("heading", { name: "Employment Situation" })).closest(".calendar-release-card") as HTMLElement;
    const unknown = screen.getByRole("heading", { name: "Another Labor Release" }).closest(".calendar-release-card") as HTMLElement;
    expect(within(known).getByText(/14:30 PL/)).toBeInTheDocument();
    expect(within(unknown).getByText(/Time unavailable/)).toBeInTheDocument();
    expect(within(known).getByText("High importance")).toBeInTheDocument();
  });

  test("events are grouped by date and a shared release appears once with both indicators", async () => {
    mockApi();
    openCalendar();
    await screen.findByRole("heading", { name: "Macro Calendar" });
    expect(await screen.findByRole("heading", { name: "Consumer Price Index" })).toBeInTheDocument();
    const card = screen.getByRole("heading", { name: "Consumer Price Index" }).closest(".calendar-release-card") as HTMLElement;
    expect(within(card).getByText("CPIAUCSL")).toBeInTheDocument();
    expect(within(card).getByText("CPILFESL")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "Consumer Price Index" })).toHaveLength(1);
    const todayGroup = screen.getByRole("region", { name: new RegExp(new Date(`${todayIso()}T00:00:00Z`).toLocaleDateString("en-US", { weekday: "long", timeZone: "UTC" })) });
    expect(within(todayGroup).getByRole("heading", { name: "Employment Situation" })).toBeInTheDocument();
    expect(within(todayGroup).getByRole("heading", { name: "Another Labor Release" })).toBeInTheDocument();
    expect(within(card).getByRole("link", { name: "Source" })).toHaveAttribute("href", "https://www.bls.gov/cpi/");
  });

  test("importance labels and colored dots appear in cards and the legend", async () => {
    mockApi();
    openCalendar();
    const cases = [
      ["Employment Situation", "high", "High importance"],
      ["Another Labor Release", "medium", "Medium importance"],
      ["H.15 Selected Interest Rates", "low", "Low importance"],
    ] as const;
    for (const [name, importance, label] of cases) {
      const card = (await screen.findByRole("heading", { name })).closest(".calendar-release-card") as HTMLElement;
      const marker = within(card).getByText(label);
      expect(marker).toHaveClass(`calendar-importance--${importance}`);
      expect(marker.querySelector(".calendar-importance__dot")).toHaveAttribute("aria-hidden", "true");
    }
    const legend = screen.getByLabelText("Release importance legend");
    for (const [, , label] of cases) expect(within(legend).getByText(label)).toBeInTheDocument();
    expect(within(legend).getByText(/not market direction/)).toBeInTheDocument();
  });

  test("events within a day render high, medium, then low importance", async () => {
    const grouped = groupCalendarEvents(events());
    const todayEvents = grouped.find((group) => group.date === todayIso())!.events;
    expect(todayEvents.map((event) => event.importance)).toEqual(["high", "medium", "low"]);
    mockApi();
    openCalendar();
    await screen.findByRole("heading", { name: "Employment Situation" });
    const todayGroup = screen.getByRole("region", { name: new RegExp(new Date(`${todayIso()}T00:00:00Z`).toLocaleDateString("en-US", { weekday: "long", timeZone: "UTC" })) });
    expect(within(todayGroup).getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent)).toEqual([
      "Employment Situation", "Another Labor Release", "H.15 Selected Interest Rates",
    ]);
  });

  test("category and week controls request the matching date window", async () => {
    const fetchMock = mockApi();
    openCalendar();
    await screen.findByRole("heading", { name: "Consumer Price Index" });
    const category = screen.getByRole("group", { name: "Calendar category" });
    fireEvent.click(within(category).getByRole("button", { name: "Inflation" }));
    expect(await screen.findByRole("heading", { name: "Consumer Price Index" })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Employment Situation" })).not.toBeInTheDocument());
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("category=inflation"))).toBe(true);
    const { startDate } = weekRange(todayIso());
    fireEvent.click(screen.getByRole("button", { name: "Next week" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes(`start_date=${shiftDate(startDate, 7)}`))).toBe(true));
    fireEvent.click(screen.getByRole("button", { name: "Previous week" }));
    await waitFor(() => expect(fetchMock.mock.calls.filter(([url]) => String(url).includes(`start_date=${startDate}`)).length).toBeGreaterThan(1));
  });

  test("past, today, and upcoming statuses derive only from dates", async () => {
    const today = todayIso();
    expect(dateStatus(shiftDate(today, -1), today)).toBe("Past");
    expect(dateStatus(today, today)).toBe("Today");
    expect(dateStatus(shiftDate(today, 1), today)).toBe("Upcoming");
    mockApi();
    openCalendar();
    const past = (await screen.findByRole("heading", { name: "Consumer Price Index" })).closest(".calendar-release-card") as HTMLElement;
    const current = screen.getByRole("heading", { name: "Employment Situation" }).closest(".calendar-release-card") as HTMLElement;
    const future = screen.getByRole("heading", { name: "Upcoming Activity Release" }).closest(".calendar-release-card") as HTMLElement;
    expect(within(past).getByText("Past")).toBeInTheDocument();
    expect(within(current).getByText("Today")).toBeInTheDocument();
    expect(within(future).getByText("Upcoming")).toBeInTheDocument();
  });

  test("release details show current-vintage context and Indicator links", async () => {
    const fetchMock = mockApi();
    openCalendar();
    const card = (await screen.findByRole("heading", { name: "Employment Situation" })).closest(".calendar-release-card") as HTMLElement;
    fireEvent.click(within(card).getByRole("button", { name: "View details" }));
    const detail = await within(card).findByLabelText("Employment Situation details");
    expect(within(detail).getByText(/Release date:/)).toBeInTheDocument();
    expect(within(detail).getByText(/not historical release-vintage values/)).toBeInTheDocument();
    expect(await within(detail).findByText("4.10%")).toBeInTheDocument();
    expect(within(detail).getByText("Latest stored reading")).toBeInTheDocument();
    expect(within(detail).getByText("Previous observation")).toBeInTheDocument();
    expect(within(detail).getByText("Latest observation date")).toBeInTheDocument();
    const indicatorLink = within(detail).getByRole("link", { name: "View indicator" });
    expect(indicatorLink).toHaveAttribute("href", "#/indicators/UNRATE");
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/api/v1/releases/20"))).toBe(true);
    fireEvent.click(indicatorLink);
    await waitFor(() => expect(window.location.hash).toBe("#/indicators/UNRATE"));
  });

  test("loading, error with retry, and empty range states are clear", async () => {
    mockApi("loading");
    openCalendar();
    expect(await screen.findByText("Loading calendar...")).toBeInTheDocument();
    cleanup();
    mockApi("error");
    openCalendar();
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load calendar.");
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    cleanup();
    mockApi("empty");
    openCalendar();
    expect(await screen.findByText("No tracked MacroLens releases in this period.")).toBeInTheDocument();
  });

  test("no unsupported time, consensus values, surprises, signals, or scores are invented", async () => {
    mockApi();
    openCalendar();
    await screen.findByRole("heading", { name: "Consumer Price Index" });
    const unsupported = screen.getByRole("heading", { name: "H.15 Selected Interest Rates" }).closest(".calendar-release-card") as HTMLElement;
    expect(within(unsupported).getByText(/Time unavailable/)).toBeInTheDocument();
    expect(screen.queryByText(/Consensus:/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Surprise:/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Trading signal:/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Macro score/i)).not.toBeInTheDocument();
  });
});
