import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";
import App from "../App";
import { MarketComparisonPage } from "./MarketComparisonPage";
import { MarketComparisonChart, MarketTooltip } from "./MarketComparisonChart";
import type { MarketComparisonResponse, MarketComparisonRow } from "../api/macrolens";
import { rangeStartDate } from "../charts/chartData";

// Comparison tests isolate the independent analysis requests; its behavior is covered separately.
vi.mock("./LeadLagAnalysis", () => ({
  LeadLagAnalysis: ({ macro, startDate }: { macro: string; startDate?: string }) => <section data-testid="lead-lag-section" data-macro={macro} data-start={startDate}>Lead / Lag Analysis</section>,
}));

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  LineChart: ({ children, data }: { children: ReactNode; data: MarketComparisonRow[] }) => <div data-testid="market-chart" data-rows={JSON.stringify(data)}>{children}</div>,
  Line: ({ dataKey, yAxisId, connectNulls }: { dataKey: string; yAxisId: string; connectNulls: boolean }) => <span data-testid="market-line" data-key={dataKey} data-axis={yAxisId} data-connect={String(connectNulls)} />,
  YAxis: ({ domain, yAxisId, label }: { domain: unknown; yAxisId: string; label: { value: string } }) => <span data-testid="market-axis" data-domain={JSON.stringify(domain)} data-axis={yAxisId}>{label.value}</span>,
  CartesianGrid: () => null, XAxis: () => null, Tooltip: () => null,
}));

function comparison(url = new URL("http://localhost/?assets=NASDAQCOM"), count = 60): MarketComparisonResponse {
  const ids = (url.searchParams.get("assets") ?? "NASDAQCOM").split(",");
  const relation = { correlation: 0.18, overlapping_observations: 60, variable_definitions: { macro: "MCI level (0-100)", market: "Monthly price return in percent" } };
  return { methodology_version: "v1", macro_history_type: url.searchParams.get("macro_history_type") === "current_vintage" ? "current_vintage" : "point_in_time",
    market_history_type: "latest_stored_observations", frequency: "monthly", alignment: "last_observation_on_or_before_month_end",
    available_overlap_start: count < 5 ? "2026-01-31" : "2014-12-31", available_overlap_end: "2026-09-30",
    mode: url.searchParams.get("mode") === "actual" ? "actual" : "indexed", status: "ready", base_date: "2020-05-31", base_values: { NASDAQCOM: 9500, CBBTCUSD: 10000 }, message: null,
    rows: Array.from({ length: count }, (_, index) => ({ as_of_date: index === 0 ? "2020-05-31" : "2020-06-30", mci: 62.4, mci_change: 2, NASDAQCOM: 9500, NASDAQCOM_indexed: 143.2, NASDAQCOM_observation_date: "2020-05-29", NASDAQCOM_return_1m: 2, CBBTCUSD: 10000, CBBTCUSD_indexed: 125, CBBTCUSD_observation_date: "2020-05-31", CBBTCUSD_return_1m: 3 })),
    series: [{ series_id: "MCI", name: "MCI", unit: "0-100", source: "MacroLens", first_observation: "2011-05-31", last_observation: "2026-09-30" },
      ...ids.map((id) => ({ series_id: id, name: id === "NASDAQCOM" ? "Nasdaq Composite" : "Bitcoin", unit: id === "NASDAQCOM" ? "index points" : "USD", source: "FRED", source_organization: id === "NASDAQCOM" ? "Nasdaq, Inc." : "Coinbase", source_url: `https://fred.stlouisfed.org/series/${id}`, attribution: "Source terms apply", first_observation: "2014-12-01", last_observation: "2026-09-30" }))],
    statistics: ids.map((id) => ({ asset_id: id as "NASDAQCOM" | "CBBTCUSD", mci: relation, mci_change: { ...relation, correlation: 0.24, overlapping_observations: 59 } })), minimum_correlation_observations: 3,
    limitations: "Market history is latest stored observations, not an ALFRED vintage backfill." };
}
function mockApi(count = 60, error = false, empty = false) {
  const fetchMock = vi.fn().mockImplementation((input: string | URL) => {
    const url = new URL(String(input));
    if (url.pathname !== "/api/v1/market-comparison") return new Promise(() => undefined);
    const body = comparison(url, count);
    if (empty) { body.status = "insufficient_overlap"; body.message = "No common date with MCI and all selected asset prices."; body.base_date = null; }
    return Promise.resolve({ ok: !error, json: async () => body });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
afterEach(() => { cleanup(); window.location.hash = ""; vi.unstubAllGlobals(); });

describe("Market Comparison Lab v1", () => {
  test("route and navigation open the page with PIT, Nasdaq, 5Y and indexed assets defaults", async () => {
    const fetchMock = mockApi();
    window.location.hash = "#/market-comparison";
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Market Comparison Lab" }, { timeout: 3000 })).toBeInTheDocument();
    await screen.findByTestId("market-chart");
    expect(screen.getByRole("link", { name: "Market Comparison" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("checkbox", { name: "Nasdaq Composite" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Bitcoin" })).not.toBeChecked();
    expect(screen.getByRole("button", { name: "Point-in-time" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "5Y" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "MCI level + indexed assets" })).toHaveAttribute("aria-pressed", "true");
    const url = new URL(String(fetchMock.mock.calls[0][0]));
    expect(url.searchParams.get("macro_history_type")).toBe("point_in_time");
    expect(url.searchParams.get("assets")).toBe("NASDAQCOM");
    expect(url.searchParams.get("start_date")).toBe(rangeStartDate(5));
  });
  test("Bitcoin, ranges, actual mode and current-vintage controls update the API and chart", async () => {
    const fetchMock = mockApi(); render(<MarketComparisonPage />);
    await screen.findByTestId("market-chart");
    fireEvent.click(screen.getByRole("checkbox", { name: "Bitcoin" }));
    await screen.findByRole("article", { name: "Bitcoin relationship statistics" });
    for (const range of ["1Y", "3Y", "10Y", "Max"]) {
      fireEvent.click(screen.getByRole("button", { name: range }));
      await waitFor(() => {
        const last = new URL(String(fetchMock.mock.calls[fetchMock.mock.calls.length - 1][0]));
        expect(last.searchParams.get("start_date")).toBe(range === "Max" ? null : rangeStartDate(Number(range.slice(0, -1))));
      });
    }
    fireEvent.click(screen.getByRole("button", { name: "Actual values" }));
    await screen.findByTestId("market-chart");
    expect(screen.getAllByTestId("market-axis")).toHaveLength(3);
    expect(screen.getAllByTestId("market-line").map((line) => line.dataset.key)).toEqual(["mci", "NASDAQCOM", "CBBTCUSD"]);
    fireEvent.click(screen.getByRole("button", { name: "Current-vintage" }));
    await screen.findByText("Current-vintage MCI uses today's stored revised values.");
    await screen.findByTestId("market-chart");
    expect(new URL(String(fetchMock.mock.calls[fetchMock.mock.calls.length - 1][0])).searchParams.get("macro_history_type")).toBe("current_vintage");
  });
  test("indexed assets share an axis while MCI stays 0-100 and gaps are preserved", () => {
    render(<MarketComparisonChart response={comparison()} mode="indexed" />);
    expect(screen.getAllByTestId("market-axis")[0]).toHaveAttribute("data-domain", "[0,100]");
    expect(screen.getAllByTestId("market-line").map((line) => [line.dataset.key, line.dataset.axis])).toEqual([["mci", "mci"], ["NASDAQCOM_indexed", "assets"]]);
    expect(screen.getAllByTestId("market-line").every((line) => line.dataset.connect === "false")).toBe(true);
    expect(screen.getByText("Assets (base = 100)")).toBeInTheDocument();
  });
  test("tooltip preserves actual value/date, PIT date, indexed asset and unavailable values", () => {
    const response = comparison();
    const { rerender } = render(<MarketTooltip response={response} row={response.rows[0]} mode="indexed" />);
    expect(screen.getByText("62.4 / 100")).toBeInTheDocument();
    expect(screen.getByText("PIT as of May 31, 2020")).toBeInTheDocument();
    expect(screen.getByText(/Indexed: 143.2/)).toBeInTheDocument();
    expect(screen.getByText(/Actual: 9,500.00 index points/)).toBeInTheDocument();
    expect(screen.getByText("Market observation: May 29, 2020")).toBeInTheDocument();
    rerender(<MarketTooltip response={response} row={{ ...response.rows[0], NASDAQCOM: null, NASDAQCOM_indexed: null, NASDAQCOM_observation_date: null }} mode="indexed" />);
    expect(screen.getByText("Actual: Unavailable")).toBeInTheDocument();
    expect(screen.getByText("Market observation: Unavailable")).toBeInTheDocument();
  });
  test("neutral statistics, methodology and source attribution render without signals", async () => {
    mockApi(); render(<MarketComparisonPage />);
    const card = await screen.findByRole("article", { name: "Nasdaq Composite relationship statistics" });
    expect(card).toHaveTextContent("+0.18"); expect(card).toHaveTextContent("+0.24");
    expect(card).toHaveTextContent("Observations: 60"); expect(card).toHaveTextContent("Observations: 59");
    expect(screen.getByText(/It does not imply causation or predictive power/)).toBeInTheDocument();
    const methodology = screen.getByRole("region", { name: "Market comparison methodology" });
    expect(methodology).toHaveTextContent("date-level rather than intraday");
    expect(methodology).toHaveTextContent("MCI stays on its native 0-100 scale");
    expect(screen.getByRole("link", { name: "FRED / Nasdaq, Inc." })).toHaveAttribute("href", "https://fred.stlouisfed.org/series/NASDAQCOM");
    expect(screen.queryByText(/Buy signal|Sell signal|Bullish|Bearish|Target price|Expected return/i)).not.toBeInTheDocument();
  });
  test("missing monthly macro scores do not erase five years of calendar coverage", async () => {
    const fetchMock = mockApi(56); render(<MarketComparisonPage />);
    await screen.findByTestId("market-chart");
    expect(screen.getByRole("button", { name: "5Y" })).toHaveAttribute("aria-pressed", "true");
    expect(fetchMock.mock.calls).toHaveLength(1);
  });
  test("short default history falls back to Max and lack of overlap is explicit", async () => {
    const fetchMock = mockApi(3, false, true); render(<MarketComparisonPage />);
    await screen.findByText(/Less than five years of shared valid data/);
    expect(await screen.findByText("No common date with MCI and all selected asset prices.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Max" })).toHaveAttribute("aria-pressed", "true");
    expect(fetchMock.mock.calls).toHaveLength(2);
    expect(screen.queryByTestId("market-chart")).not.toBeInTheDocument();
  });
  test("empty asset selection stops requests and error retry is available", async () => {
    const fetchMock = mockApi(60, true); render(<MarketComparisonPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load market comparison");
    fireEvent.click(screen.getByRole("button", { name: "Retry comparison" }));
    await waitFor(() => expect(fetchMock.mock.calls).toHaveLength(2));
    fireEvent.click(screen.getByRole("checkbox", { name: "Nasdaq Composite" }));
    expect(screen.getByText("Select at least one asset to compare.")).toBeInTheDocument();
    expect(fetchMock.mock.calls).toHaveLength(2);
  });
});


test("lead/lag section inherits the shared macro and range controls", async () => {
  mockApi(); render(<MarketComparisonPage />);
  await screen.findByTestId("market-chart");
  expect(screen.getByTestId("lead-lag-section")).toHaveAttribute("data-macro", "point_in_time");
  expect(screen.getByTestId("lead-lag-section")).toHaveAttribute("data-start", rangeStartDate(5));
  fireEvent.click(screen.getByRole("button", { name: "3Y" }));
  expect(screen.getByTestId("lead-lag-section")).toHaveAttribute("data-start", rangeStartDate(3));
  fireEvent.click(screen.getByRole("button", { name: "Current-vintage" }));
  expect(screen.getByTestId("lead-lag-section")).toHaveAttribute("data-macro", "current_vintage");
});
