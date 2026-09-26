import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import App from "../App";
import { historyRows } from "./IndicatorsPage";
import { rangeStartDate } from "../charts/chartData";
import { formatIndicatorValue } from "./indicatorMetadata";
import type { SeriesMetadata } from "../api/macrolens";

const series: SeriesMetadata[] = [
  { series_id: "UNRATE", name: "Unemployment Rate", short_name: "Unemployment Rate", category: "labor", frequency: "monthly", unit: "percent" },
  { series_id: "UNEMPLOY", name: "Unemployment Level", short_name: "Unemployed Persons", category: "labor", frequency: "monthly", unit: "thousands of persons" },
  { series_id: "CPIAUCSL", name: "Consumer Price Index for All Urban Consumers", short_name: "CPI", category: "inflation", frequency: "monthly", unit: "index" },
  { series_id: "DGS10", name: "10-Year Treasury Yield", short_name: "10Y Treasury Yield", category: "financial_conditions", frequency: "daily", unit: "percent" },
];

type MockOptions = { history?: "ready" | "loading" | "error" | "empty"; catalog?: "ready" | "loading" | "error" };

function mockApi(options: MockOptions = {}) {
  const fetchMock = vi.fn().mockImplementation((input: string | URL) => {
    const url = String(input);
    if (url.endsWith("/api/v1/series")) {
      if (options.catalog === "loading") return new Promise(() => undefined);
      if (options.catalog === "error") return Promise.resolve({ ok: false });
      return Promise.resolve({ ok: true, json: async () => ({ series }) });
    }
    if (url.endsWith("/features")) {
      const parts = url.split("/");
      const id = parts[parts.length - 2];
      const features = id === "UNRATE" ? ["level", "change_3m"] : id === "CPIAUCSL" ? ["yoy"] : ["level"];
      return Promise.resolve({ ok: true, json: async () => ({ series_id: id, methodology_version: "v1", features }) });
    }
    if (url.includes("/history")) {
      if (options.history === "loading") return new Promise(() => undefined);
      if (options.history === "error") return Promise.resolve({ ok: false });
      const observations = options.history === "empty" ? [] : url.includes("change_3m")
        ? [{ observation_date: "2026-07-01", value: 0.1 }, { observation_date: "2026-08-01", value: 0.2 }]
        : url.includes("UNEMPLOY")
          ? [{ observation_date: "2026-07-01", value: 7000 }, { observation_date: "2026-08-01", value: 7200 }]
          : [{ observation_date: "2026-07-01", value: 4.0 }, { observation_date: "2026-08-01", value: 4.1 }];
      return Promise.resolve({ ok: true, json: async () => ({ history_type: "current_vintage", observations }) });
    }
    return new Promise(() => undefined);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function openIndicators(hash = "#/indicators/UNRATE") {
  window.location.hash = hash;
  render(<App />);
}

afterEach(() => {
  cleanup();
  window.location.hash = "";
  vi.unstubAllGlobals();
});

describe("Indicator Explorer", () => {
  test("top navigation opens Indicators and the catalog loads", async () => {
    mockApi();
    window.location.hash = "#/";
    render(<App />);
    fireEvent.click(screen.getByRole("link", { name: "Indicators" }));
    expect(await screen.findByRole("heading", { name: "Indicators" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Indicators" })).toHaveAttribute("aria-current", "page");
    expect(await screen.findByRole("link", { name: /UNRATE Unemployment Rate/ })).toBeInTheDocument();
    await waitFor(() => expect(window.location.hash).toBe("#/indicators/UNRATE"));
  });

  test("search matches ID, full name, and short name; category filters instantly", async () => {
    mockApi();
    openIndicators();
    const browser = await screen.findByRole("complementary", { name: "Indicator browser" });
    expect(await within(browser).findByText("4 indicators")).toBeInTheDocument();
    const search = within(browser).getByRole("searchbox", { name: "Search indicators" });
    fireEvent.change(search, { target: { value: "DGS10" } });
    expect(within(browser).getByText("1 indicator")).toBeInTheDocument();
    expect(within(browser).queryByText("UNRATE")).not.toBeInTheDocument();
    fireEvent.change(search, { target: { value: "Consumer Price Index for All" } });
    expect(within(browser).getByText("CPIAUCSL")).toBeInTheDocument();
    fireEvent.change(search, { target: { value: "Unemployed Persons" } });
    expect(within(browser).getByText("UNEMPLOY")).toBeInTheDocument();
    fireEvent.change(search, { target: { value: "" } });
    fireEvent.click(within(browser).getByRole("button", { name: "Inflation" }));
    expect(within(browser).getByText("CPIAUCSL")).toBeInTheDocument();
    expect(within(browser).queryByText("UNRATE")).not.toBeInTheDocument();
  });

  test("selection updates detail and URL; direct valid and invalid URLs are handled", async () => {
    mockApi();
    openIndicators();
    const browser = await screen.findByRole("complementary", { name: "Indicator browser" });
    fireEvent.click(await within(browser).findByRole("link", { name: /UNEMPLOY Unemployed Persons/ }));
    expect(await screen.findByRole("heading", { name: "Unemployment Level" })).toBeInTheDocument();
    expect(window.location.hash).toBe("#/indicators/UNEMPLOY");
    expect(within(browser).getByRole("link", { name: /UNEMPLOY Unemployed Persons/ })).toHaveAttribute("aria-current", "true");
    window.location.hash = "#/indicators/UNRATE";
    expect(await screen.findByRole("heading", { name: "Unemployment Rate" })).toBeInTheDocument();
    cleanup();
    openIndicators("#/indicators/DGS10");
    expect(await screen.findByRole("heading", { name: "10-Year Treasury Yield" })).toBeInTheDocument();
    cleanup();
    openIndicators("#/indicators/NOT_A_SERIES");
    expect(await screen.findByRole("heading", { name: "Indicator not found" })).toBeInTheDocument();
  });

  test("current and previous observations render with dates and correct units", async () => {
    mockApi();
    openIndicators();
    expect(await screen.findByText("4.10%")).toBeInTheDocument();
    expect(screen.getByText("4.00%")).toBeInTheDocument();
    expect(screen.getByText("Current observation date: Aug 2026")).toBeInTheDocument();
    expect(screen.getByText("Previous observation date: Jul 2026")).toBeInTheDocument();
    expect(screen.getByText("Previous value")).toBeInTheDocument();
    expect(formatIndicatorValue(7000, series[1], null)).toBe("7.0M");
    expect(formatIndicatorValue(159100, series[1], null)).toBe("159.1M");
    expect(formatIndicatorValue(206000, { ...series[1], unit: "number" }, null)).toBe("206K");
    expect(formatIndicatorValue(1240, { ...series[1], unit: "thousands of units, seasonally adjusted annual rate" }, null)).toBe("1.24M SAAR");
    expect(formatIndicatorValue(0.12, series[0], "change_3m")).toBe("0.12 pp");
    expect(formatIndicatorValue(6.76, series[3], null)).toBe("6.76%");
    expect(formatIndicatorValue(-0.56, series[2], null)).toBe("-0.56");
  });

  test("range and transformation changes request the correct existing history", async () => {
    const fetchMock = mockApi();
    openIndicators();
    await screen.findByText("4.10%");
    const ranges = screen.getByRole("group", { name: "Indicator time range" });
    expect(within(ranges).getByRole("button", { name: "3Y" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(within(ranges).getByRole("button", { name: "1Y" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes(`UNRATE/history?start_date=${rangeStartDate(1)}`))).toBe(true));
    const transformations = screen.getByRole("group", { name: "Transformation" });
    const change = await within(transformations).findByRole("button", { name: "3M change" });
    expect(within(transformations).queryByRole("button", { name: "YoY" })).not.toBeInTheDocument();
    fireEvent.click(change);
    expect(await screen.findByText("0.20 pp")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes(`/UNRATE/features/change_3m/history?start_date=${rangeStartDate(1)}`))).toBe(true);
  });

  test("catalog and history loading, error, and empty states are explicit", async () => {
    mockApi({ catalog: "loading" });
    openIndicators();
    expect(await screen.findByText("Loading indicators...")).toBeInTheDocument();
    cleanup();
    mockApi({ catalog: "error" });
    openIndicators();
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load indicators.");
    cleanup();
    mockApi({ history: "loading" });
    openIndicators();
    expect(await screen.findByText("Loading indicator history...")).toBeInTheDocument();
    cleanup();
    mockApi({ history: "error" });
    openIndicators();
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load indicator history.");
    cleanup();
    mockApi({ history: "empty" });
    openIndicators();
    expect(await screen.findByText("No history available for this range.")).toBeInTheDocument();
  });

  test("current-vintage limitation is visible without scores or signals", async () => {
    mockApi();
    openIndicators();
    expect((await screen.findByText(/Current-vintage history/)).parentElement).toHaveTextContent("Revised series may differ from originally published values.");
    expect(screen.getByText(/No trading signals/)).toBeInTheDocument();
    expect(screen.queryByText(/macro score/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/trading signal:/i)).not.toBeInTheDocument();
  });

  test("missing historical observations remain missing", () => {
    expect(historyRows({ series_id: "UNRATE", history_type: "current_vintage", observations: [
      { observation_date: "2026-03-01", value: 4.1 },
      { observation_date: "2026-01-01", value: 4.0 },
      { observation_date: "2026-02-01", value: null },
    ] })).toEqual([
      { observation_date: "2026-01-01", value: 4.0 },
      { observation_date: "2026-02-01", value: null },
      { observation_date: "2026-03-01", value: 4.1 },
    ]);
  });
});
