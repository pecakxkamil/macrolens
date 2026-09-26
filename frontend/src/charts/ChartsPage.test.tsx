import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import App from "../App";
import { combineChartData, rangeStartDate } from "./chartData";
import { chartDefinitions } from "./chartDefinitions";

function mockHistory(observations: Array<{ observation_date: string; value: number | null }> = [
  { observation_date: "2026-07-01", value: 4.1 },
  { observation_date: "2026-08-01", value: 4.2 },
]) {
  const fetchMock = vi.fn().mockImplementation(() => Promise.resolve({
    ok: true,
    json: async () => ({ history_type: "current_vintage", observations }),
  }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function openCharts() {
  window.location.hash = "#/charts";
  render(<App />);
}

afterEach(() => {
  cleanup();
  window.location.hash = "";
  vi.unstubAllGlobals();
});

describe("Charts v1", () => {
  test("navigation opens Charts and browser history returns to Overview", async () => {
    mockHistory();
    openCharts();
    expect(await screen.findByRole("heading", { name: "Historical Charts" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Charts" })).toHaveAttribute("aria-current", "page");
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    fireEvent.click(screen.getByRole("link", { name: "Overview" }));
    expect(await screen.findByText("Loading USA Economy Now...")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
  });

  test("Labor and 3Y are defaults, with methodology notice and no overview fetch", async () => {
    const fetchMock = mockHistory();
    openCharts();
    expect(await screen.findByRole("heading", { name: "Unemployment Rate" })).toBeInTheDocument();
    expect(within(screen.getByRole("group", { name: "Chart domain" })).getByRole("button", { name: "Labor" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByRole("heading", { name: "CPI Inflation YoY" })).not.toBeInTheDocument();
    expect(within(screen.getByRole("group", { name: "Time range" })).getByRole("button", { name: "3Y" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/Current-vintage history/).parentElement).toHaveTextContent("This is not point-in-time historical reconstruction.");
    expect(screen.getByText("No trading signals.")).toBeInTheDocument();
    expect(screen.queryByText(/macro score/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/trading signal:/i)).not.toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock.mock.calls.every(([url]) => !String(url).includes("/economy/us"))).toBe(true);
    expect(fetchMock.mock.calls.every(([url]) => String(url).includes(`start_date=${rangeStartDate(3)}`))).toBe(true);
  });

  test("financial spread uses the backend synchronized history endpoint", async () => {
    const fetchMock = mockHistory();
    openCharts();
    await screen.findByRole("heading", { name: "Historical Charts" });
    fireEvent.click(within(screen.getByRole("group", { name: "Chart domain" })).getByRole("button", { name: "Financial Conditions" }));
    expect(screen.getByRole("heading", { name: "2s10s Yield Curve Spread" })).toBeInTheDocument();
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/api/v1/analytics/yield-curve/2s10s/history?start_date="))).toBe(true));
  });

  test("changing domain fetches only its series; changing range updates start_date", async () => {
    const fetchMock = mockHistory();
    openCharts();
    await screen.findByRole("heading", { name: "Historical Charts" });
    fireEvent.click(within(screen.getByRole("group", { name: "Chart domain" })).getByRole("button", { name: "Inflation" }));
    expect(screen.getByRole("heading", { name: "CPI Inflation YoY" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Unemployment Rate" })).not.toBeInTheDocument();
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("CPILFESL"))).toBe(true));
    const inflationCalls = fetchMock.mock.calls.filter(([url]) => String(url).includes("CPIAUCSL/features/yoy"));
    expect(inflationCalls).toHaveLength(1);
    fireEvent.click(within(screen.getByRole("group", { name: "Time range" })).getByRole("button", { name: "1Y" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes(`CPIAUCSL/features/yoy/history?start_date=${rangeStartDate(1)}`))).toBe(true));
  });

  test("loading, error, and empty states are explicit", async () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    openCharts();
    expect((await screen.findAllByText("Loading history...")).length).toBeGreaterThan(0);
    cleanup();
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: false })));
    openCharts();
    expect((await screen.findAllByRole("alert"))[0]).toHaveTextContent("Unable to load chart history");
    cleanup();
    mockHistory([]);
    openCharts();
    expect((await screen.findAllByText("No history available for this range.")).length).toBeGreaterThan(0);
  });

  test("legend controls are accessible and show latest readings without hover", async () => {
    mockHistory();
    openCharts();
    const card = (await screen.findByRole("heading", { name: "Unemployment Rate" })).closest(".chart-card") as HTMLElement;
    const hide = await within(card).findByRole("button", { name: "Hide Unemployment rate" });
    expect(within(card).getByRole("region", { name: "Unemployment Rate time series chart" })).toBeInTheDocument();
    expect(hide).toHaveAttribute("aria-pressed", "true");
    expect(card).toHaveTextContent("4.20%");
    fireEvent.click(hide);
    expect(within(card).getByRole("button", { name: "Show Unemployment rate" })).toHaveAttribute("aria-pressed", "false");
    expect(card).toHaveTextContent("Select a series above to display it.");
  });

  test("multi-series dates remain sparse; no missing values are filled", () => {
    const definition = chartDefinitions.find((item) => item.id === "cpi-yoy")!;
    const rows = combineChartData(definition, {
      "CPIAUCSL:yoy": { series_id: "CPIAUCSL", history_type: "current_vintage", observations: [
        { observation_date: "2026-01-01", value: 3.1 },
        { observation_date: "2026-03-01", value: 3.3 },
      ] },
      "CPILFESL:yoy": { series_id: "CPILFESL", history_type: "current_vintage", observations: [
        { observation_date: "2026-02-01", value: 2.8 },
        { observation_date: "2026-03-01", value: null },
      ] },
    });
    expect(rows).toEqual([
      { observation_date: "2026-01-01", headline: 3.1, core: null },
      { observation_date: "2026-02-01", headline: null, core: 2.8 },
      { observation_date: "2026-03-01", headline: 3.3, core: null },
    ]);
  });
});
