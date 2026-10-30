import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import App from "../App";
// Compile the real first research route during collection. Translation assertions
// must not spend their DOM wait budget on cold nested Vite/Recharts imports.
import "../navigation/ResearchPage";
import "../macro-index/MacroIndexPage";
import { getLanguage, setLanguage, t, tText, tLabel, getLocale } from "./language";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { InfoTooltip } from "../components/InfoTooltip";
import { formatNumber, formatObservationDate } from "../format";
import { formatPolandTime } from "../calendar/calendarDates";
import { briefMarkdown, briefModel } from "../brief/briefModel";
import type { EconomyBriefResponse } from "../api/macrolens";
import dictionary from "./pl.json";
import { resolveRoute } from "../navigation/routes";

function language(value: "en" | "pl") { act(() => setLanguage(value)); }
function offline() {
  const fetch = vi.fn().mockResolvedValue({ ok: false });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}
afterEach(() => {
  cleanup(); language("en"); localStorage.removeItem("macrolens.language");
  window.location.hash = ""; vi.unstubAllGlobals(); vi.restoreAllMocks();
});

test("corner switch translates all navigation labels, sets document language and remembers preference", async () => {
  const fetch = offline(); render(<App />);
  await screen.findByRole("heading", { name: "USA Economy Now" });
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  expect(screen.getByRole("button", { name: "English" })).toHaveAttribute("aria-pressed", "true");
  const count = fetch.mock.calls.length;
  fireEvent.click(screen.getByRole("button", { name: "Polski" }));
  expect(document.documentElement.lang).toBe("pl");
  expect(localStorage.getItem("macrolens.language")).toBe("pl");
  const nav = screen.getByRole("navigation", { name: "Nawigacja główna" });
  for (const name of ["Przegl\u0105d", "Eksploracja danych", "Badania"]) {
    expect(within(nav).getByRole("link", { name })).toBeInTheDocument();
  }
  expect(screen.getByRole("heading", { name: "Gospodarka USA" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Pobierz raport" })).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(count);
  fireEvent.click(screen.getByRole("button", { name: "English" }));
  expect(screen.getByRole("link", { name: "Overview" })).toBeInTheDocument();
  expect(document.documentElement.lang).toBe("en");
});

test.each([
  ["#/state", "Gospodarka USA"],
  ["#/macro-index", "Indeks warunków makroekonomicznych"],
  ["#/market-comparison", "Analiza makro i rynku"],
  ["#/charts", "Wykresy historyczne"],
  ["#/indicators", "Wskaźniki"],
  ["#/calendar", "Kalendarz"],
  ["#/relationships", "Por\u00f3wnaj dane"],
])("route %s opens in Polish, including its error state and controls", async (hash, heading) => {
  language("pl"); offline(); window.location.hash = hash; render(<App />);
  expect(await screen.findByRole("heading", { name: heading }, { timeout: 5000 })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Polski" })).toHaveAttribute("aria-pressed", "true");
  expect(window.location.hash).toBe(resolveRoute(hash).hash);
  await waitFor(() => expect(screen.queryByText(/^Loading /)).not.toBeInTheDocument());
  expect(screen.queryByText(/^Unable to load /)).not.toBeInTheDocument();
});

test("switch preserves the selected range and route without another request", async () => {
  const fetch = offline(); window.location.hash = "#/charts"; render(<App />);
  await screen.findByRole("heading", { name: "Historical Charts" });
  fireEvent.click(screen.getByRole("button", { name: "1Y" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "1Y" })).toHaveAttribute("aria-pressed", "true"));
  const count = fetch.mock.calls.length;
  fireEvent.click(screen.getByRole("button", { name: "Polski" }));
  expect(screen.getByRole("button", { name: "1 rok" })).toHaveAttribute("aria-pressed", "true");
  expect(window.location.hash).toBe("#/explore/charts");
  expect(fetch).toHaveBeenCalledTimes(count);
});

test("Polish numbers, observation dates and Warsaw DST use locale APIs without changing values", () => {
  language("pl");
  expect(getLocale()).toBe("pl-PL");
  expect(formatNumber(3.71)).toBe("3,71");
  expect(formatObservationDate("2026-04-01", "quarterly")).toBe("kw. 2 2026");
  expect(formatObservationDate("2026-08-01", "monthly")).toMatch(/sie/);
  expect(formatPolandTime("2026-03-16T12:30:00Z")).toBe("13:30 PL");
  language("en"); expect(formatNumber(3.71)).toBe("3.71");
});

test("indicator descriptions and accessible tooltips are translated", () => {
  language("pl"); render(<InfoTooltip metricKey="unemploymentRate" />);
  const button = screen.getByRole("button", { name: /Informacje:.*Stopa bezrobocia/ });
  fireEvent.click(button);
  expect(screen.getByRole("tooltip")).toHaveTextContent("Udział osób bezrobotnych");
  expect(screen.getByRole("tooltip")).not.toHaveTextContent("Share of the civilian");
});

test("API evidence and calculation explanations translate with their actual labels", () => {
  language("pl");
  expect(t("Labor overall momentum is mixed.")).toBe("Ogólna dynamika rynku pracy: mieszane sygnały.");
  expect(t("NFCI direction is tightening.")).toBe("Kierunek NFCI: zaostrzanie.");
  const rule = "For the same quarter, QoQ annualized above YoY means accelerating, below means decelerating, equal means stable. This does not compare successive quarterly annualized rates. Uses unrounded feature values.";
  expect(t(rule)).toContain("Dla tego samego kwartału");
  expect(t(rule)).toContain("Nie porównuje to kolejnych");
  expect(t("Headline CPI momentum: Decelerating. Inputs: 0.18 percent [annualized_3m], 3.71 percent [yoy]."))
    .toContain("[annualized_3m]");
});

test("raw identifiers, API tuples, URLs, numeric data and axis binding remain unchanged", () => {
  language("pl");
  const url = "https://fred.stlouisfed.org/series/PAYEMS";
  expect(t(url)).toBe(url);
  const source = "(CPIAUCSL, yoy) (GDPC1, qoq_annualized) [level] [annualized_3m] point_in_time";
  expect(t(source)).toBe(source);
  const data = { mci: 57.46, series_id: "PAYEMS", value: 29, unit: "percent" };
  expect(tText(data)).toBe(data);
  const label = tLabel({ value: "Assets (base = 100)", dataKey: "mci", angle: 90 });
  expect(label).toEqual({ value: "Aktywa (baza = 100)", dataKey: "mci", angle: 90 });
  expect(tText(["Labor", 29, null])).toEqual(["Rynek pracy", 29, null]);
});

test("Markdown export follows the selected language and keeps raw source metadata and links", () => {
  const data: EconomyBriefResponse = {
    assembled_at: "2026-10-18T17:00:00+02:00", timezone: "Europe/Warsaw", history_type: "current_vintage",
    snapshot: { status: "unavailable", data: null, error: "Unavailable" },
    state: { status: "unavailable", data: null, error: "Unavailable" },
    calendar: { status: "ready", data: { start_date: "2026-10-18", end_date: "2026-10-24", category: null, events: [] }, error: null },
    changes: { status: "ready", error: null, data: [{
      series_id: "UNRATE", feature_name: "level", label: "Unemployment rate", frequency: "monthly",
      unit: "percent", change_unit: "percentage points", change_type: "Difference from previous calendar month",
      change: .1, expected_previous_observation_date: "2026-08-01", latest_stored_observation_date: "2026-09-01",
      current: { observation_date: "2026-09-01", feature_as_of_date: "2026-10-02", value: 4.2 },
      previous: { observation_date: "2026-08-01", feature_as_of_date: "2026-10-02", value: 4.1 },
    }] }, calendar_start_date: "2026-10-18", calendar_end_date: "2026-10-24",
  };
  data.reading_comparisons = { status: "ready", error: null, data: [{ ...data.changes.data![0], domain: "labor", component: "unemployment", three_periods_ago: null, expected_three_periods_ago_date: "2026-06-01" }] };
  language("pl");
  const report = briefMarkdown(briefModel(data), data, data.assembled_at);
  expect(report).toContain("# MacroLens - Przegląd gospodarki");
  expect(report).toContain("Poprzedni miesi");
  expect(report).toContain("## Rynek pracy");
  expect(report).toContain("Stopa bezrobocia");
  expect(report).toContain("4,20");
  expect(report).toContain("(UNRATE, level)");
  expect(report).toContain("2026-09-01");
  expect(report).toContain("https://fred.stlouisfed.org/series/UNRATE");
  expect(report).not.toContain("Latest reading comparisons");
  expect(report).not.toContain("No tracked releases");
  language("en");
  expect(briefMarkdown(briefModel(data, { status: "unavailable" }), data, data.assembled_at)).toContain("Previous month");
});

test("storage changes synchronize the language across tabs", () => {
  render(<LanguageSwitcher />);
  act(() => window.dispatchEvent(new StorageEvent("storage", { key: "macrolens.language", newValue: "pl" })));
  expect(getLanguage()).toBe("pl");
  expect(screen.getByRole("button", { name: "Polski" })).toHaveAttribute("aria-pressed", "true");
});

test("catalog entries are complete strings, and repeated rendering does not translate Polish twice", () => {
  for (const [source, translation] of Object.entries(dictionary)) {
    expect(source.trim()).not.toBe("");
    expect(typeof translation).toBe("string"); expect(translation.trim()).not.toBe("");
  }
  language("pl");
  const first = t("This is a descriptive analytical index. It provides no market prediction or recession probability.");
  expect(t(first)).toBe(first);
});

test("Polish indicator search accepts the translated name and preserves raw series IDs", async () => {
  language("pl");
  window.location.hash = "#/indicators";
  vi.stubGlobal("fetch", vi.fn().mockImplementation((input: string) => {
    if (String(input).endsWith("/api/v1/series")) return Promise.resolve({ ok: true, json: async () => ({ series: [
      { series_id: "UNRATE", name: "Unemployment Rate", short_name: "Unemployment Rate", category: "labor", frequency: "monthly", unit: "percent" },
      { series_id: "HOUST", name: "Housing Starts", short_name: "Housing Starts", category: "housing", frequency: "monthly", unit: "thousands" },
    ] }) });
    return new Promise(() => undefined);
  }));
  render(<App />);
  await screen.findByRole("link", { name: /UNRATE.*Stopa bezrobocia/ });
  fireEvent.change(screen.getByLabelText("Szukaj wskaźników"), { target: { value: "bezrobocia" } });
  expect(screen.getByRole("link", { name: /UNRATE.*Stopa bezrobocia/ })).toHaveAttribute("href", "#/explore/indicators/UNRATE");
  expect(screen.queryByRole("link", { name: /HOUST.*Rozpoczęte/ })).not.toBeInTheDocument();
});


test("reorganized view introductions and domain links translate as complete phrases", () => {
  language("pl");
  for (const text of [
    "Inspect US macroeconomic indicators, their history, transformations and sources.",
    "Explore documented historical comparisons. Results depend on the selected data, period and method.",
    "Experimental descriptive index of monthly US macroeconomic conditions, with six transparent domain subindices.",
    "MCI summarizes selected macro indicators on a common descriptive scale. It is not a validated recession or forecasting model; 50 is a reference value, not a validated boundary between recession and a healthy economy.",
    "How do macro conditions and their changes relate to Nasdaq and Bitcoin returns?",
    "Compare monthly MCI levels and changes with market returns, then inspect lead/lag correlations and rolling windows below. Statistics describe only the selected sample; gaps and sample sizes remain visible.",
    "Explore Labor data", "Explore Inflation data", "Explore Growth data", "Explore Consumer data", "Explore Housing data", "Explore Financial Conditions data",
    "Source and series definition (FRED)",
  ]) expect(t(text)).toBe(dictionary[text as keyof typeof dictionary]);
});

test("indicator range labels translate without resetting the selected range", async () => {
  offline(); window.location.hash = "#/explore/indicators/UNRATE"; render(<App />);
  await screen.findByRole("heading", { name: "Indicators" });
  // The catalog is enough to render controls; history remains unavailable.
  vi.stubGlobal("fetch", vi.fn().mockImplementation((input: string) => String(input).endsWith("/api/v1/series") ? Promise.resolve({ ok: true, json: async () => ({series:[{series_id:"UNRATE",name:"Unemployment Rate",short_name:"Unemployment Rate",category:"labor",frequency:"monthly",unit:"percent"}]}) }) : new Promise(() => undefined)));
  fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
  await screen.findByRole("button", { name: "1Y" });
  fireEvent.click(screen.getByRole("button", { name: "1Y" }));
  fireEvent.click(screen.getByRole("button", { name: "Polski" }));
  expect(screen.getByRole("button", { name: "1 rok" })).toHaveAttribute("aria-pressed", "true");
});
