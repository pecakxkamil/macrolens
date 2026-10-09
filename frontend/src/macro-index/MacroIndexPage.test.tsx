import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";
import App from "../App";
import type { MciCurrentResponse, MciHistoryObservation } from "../api/macrolens";
import { rangeStartDate } from "../charts/chartData";
import fixture from "./testData.json";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  LineChart: ({ children, data }: { children: ReactNode; data: MciHistoryObservation[] }) => <div data-testid="index-chart" data-rows={JSON.stringify(data)}>{children}</div>,
  Line: ({ dataKey, connectNulls }: { dataKey: string; connectNulls: boolean }) => <span data-testid="index-line" data-key={dataKey} data-connect-nulls={String(connectNulls)} />,
  YAxis: ({ domain }: { domain: number[] }) => <span data-testid="index-axis" data-domain={JSON.stringify(domain)} />,
  CartesianGrid: () => null, XAxis: () => null, ReferenceLine: () => null, Tooltip: () => null,
}));

const current = fixture as MciCurrentResponse;
const observations: MciHistoryObservation[] = ["2006-10-31", "2006-11-30", "2006-12-31"].map((observation_date, index) => ({
  observation_date, mci: index === 1 ? null : 50,
  labor: 50, inflation: 50, growth: 50, consumer: 50, housing: 50, financial_conditions: 50,
}));

function mockApi(data = current, historyRows = observations, failFirst = false, pitRows = historyRows) {
  let currentCalls = 0;
  const fetchMock = vi.fn().mockImplementation((input: string | URL) => {
    const url = new URL(String(input));
    if (url.pathname.replace("/point-in-time", "") === "/api/v1/economy/us/mci") {
      currentCalls++;
      return Promise.resolve({ ok: !(failFirst && currentCalls === 1), json: async () => data });
    }
    if (url.pathname.replace("/point-in-time", "") === "/api/v1/economy/us/mci/history") return Promise.resolve({
      ok: true, json: async () => ({ ...data, observations: url.pathname.includes("/point-in-time") ? pitRows : historyRows }),
    });
    return new Promise(() => undefined);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function openIndex() {
  window.location.hash = "#/macro-index";
  render(<App />);
}

afterEach(() => {
  cleanup();
  window.location.hash = "";
  vi.unstubAllGlobals();
});

describe("Macro Conditions Index v1", () => {
  test("navigation opens Macro Index and point-in-time explanation renders", async () => {
    mockApi();
    window.location.hash = "#/";
    render(<App />);
    fireEvent.click(screen.getByRole("link", { name: "Macro Index" }));
    expect(await screen.findByRole("heading", { name: "Macro Conditions Index" })).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Current Macro Conditions Index" })).toHaveTextContent("50.0 / 100");
    expect(screen.getByRole("link", { name: "Macro Index" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Point-in-time uses only data vintages available by each historical month-end.")).toBeInTheDocument();
    expect(screen.getByText(/not an investable or backtest signal/)).toBeInTheDocument();
    expect(screen.queryByText(/Trading signal:|Recession probability:|Bullish|Bearish|Risk-on|Risk-off/i)).not.toBeInTheDocument();
  });

  test("six domains, raw values, scores, weights and calculation details render", async () => {
    mockApi();
    openIndex();
    const section = await screen.findByRole("region", { name: "Domain subindices and component decomposition" });
    expect(within(section).getAllByRole("article")).toHaveLength(6);
    for (const domain of Object.values(current.domains)) {
      const card = within(section).getByRole("article", { name: domain.name });
      expect(within(card).getByRole("heading", { name: domain.name })).toBeInTheDocument();
      expect(card).toHaveTextContent("50.0 / 100");
      expect(card).toHaveTextContent("Domain weight: 16.67%");
      expect(within(card).getByRole("table")).toHaveTextContent("Raw value");
      for (const component of domain.components) expect(within(card).getByRole("rowheader", { name: component.label })).toBeInTheDocument();
    }
    const labor = screen.getByRole("article", { name: "Labor Conditions Index" });
    expect(labor).toHaveTextContent("50.00 thousands of persons");
    expect(labor).toHaveTextContent("33.33%");
    fireEvent.click(within(labor).getByText("Payroll momentum gap: calculation and freshness"));
    expect(labor).toHaveTextContent("Raw component = monthly_change_ma_3m minus monthly_change_ma_6m");
    expect(labor).toHaveTextContent("84 observations");
    expect(labor).toHaveTextContent("Source observation: 2006-12-01");
    expect(screen.getByRole("region", { name: "Index methodology" })).toHaveTextContent("max(0, 100 * (1 - abs(inflation_yoy - 2) / 4))");
  });

  test("history uses fixed 0-100 axis, preserves gaps, and domain lines are optional", async () => {
    mockApi();
    openIndex();
    await screen.findByRole("region", { name: /Macro Conditions Index historical line chart/ });
    expect(screen.getByTestId("index-axis")).toHaveAttribute("data-domain", "[0,100]");
    expect(JSON.parse(screen.getByTestId("index-chart").getAttribute("data-rows")!)[1].mci).toBeNull();
    expect(screen.getAllByTestId("index-line")).toHaveLength(1);
    expect(screen.getByTestId("index-line")).toHaveAttribute("data-key", "mci");
    expect(screen.getByTestId("index-line")).toHaveAttribute("data-connect-nulls", "false");
    fireEvent.click(screen.getByRole("checkbox", { name: "Labor" }));
    expect(screen.getByRole("checkbox", { name: "Labor" })).toBeChecked();
    expect(screen.getAllByTestId("index-line")).toHaveLength(2);
    fireEvent.click(screen.getByRole("checkbox", { name: "Labor" }));
    expect(screen.getAllByTestId("index-line")).toHaveLength(1);
  });

  test("range controls change the history request without recalculating current display", async () => {
    const fetchMock = mockApi();
    openIndex();
    await screen.findByTestId("index-chart");
    const group = screen.getByRole("group", { name: "Index time range" });
    expect(within(group).getByRole("button", { name: "3Y" })).toHaveAttribute("aria-pressed", "true");
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes(`start_date=${rangeStartDate(3)}`))).toBe(true);
    for (const years of [1, 5, 10]) {
      fireEvent.click(within(group).getByRole("button", { name: `${years}Y` }));
      await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes(`start_date=${rangeStartDate(years)}`))).toBe(true));
    }
    fireEvent.click(within(group).getByRole("button", { name: "Max" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/mci/point-in-time/history"))).toBe(true));
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/us/mci/point-in-time"))).toHaveLength(1);
  });

  test("stale complete month and missing scores are identified", async () => {
    const data = structuredClone(current);
    data.latest_evaluated_month = "2007-01-31";
    data.domains.housing.score = null;
    data.domains.housing.contribution = null;
    data.domains.housing.components[0].score = null;
    data.domains.housing.components[0].raw_value = null;
    data.domains.housing.components[0].status = "missing";
    data.mci = null;
    mockApi(data);
    openIndex();
    const hero = await screen.findByRole("region", { name: "Current Macro Conditions Index" });
    expect(hero).toHaveTextContent("Unavailable");
    expect(hero).toHaveTextContent("Latest evaluated month: 2007-01-31");
    expect(hero).toHaveTextContent("Missing inputs are not filled or reweighted");
    expect(screen.getByRole("article", { name: "Housing Conditions Index" })).toHaveTextContent("Unavailable");
  });

  test("PIT is the default and switching modes fetches clearly distinct products", async () => {
    const pitRows = observations.map((row) => ({ ...row, mci: 25 }));
    const fetchMock = mockApi(current, observations, false, pitRows);
    openIndex();
    await screen.findByTestId("index-chart");
    const group = screen.getByRole("group", { name: "Index history mode" });
    expect(within(group).getByRole("button", { name: "Point-in-time" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: "Monthly history: Point-in-time" })).toBeInTheDocument();
    expect(JSON.parse(screen.getByTestId("index-chart").getAttribute("data-rows")!)[0].mci).toBe(25);
    expect(screen.getByRole("region", { name: "Point-in-time coverage" })).toBeInTheDocument();
    fireEvent.click(within(group).getByRole("button", { name: "Current-vintage" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/us/mci"))).toBe(true));
    await screen.findByTestId("index-chart");
    expect(screen.getByText("Current-vintage history uses today's stored revised values.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Monthly history: Current-vintage" })).toBeInTheDocument();
    expect(JSON.parse(screen.getByTestId("index-chart").getAttribute("data-rows")!)[0].mci).toBe(50);
    expect(screen.queryByRole("region", { name: "Point-in-time coverage" })).not.toBeInTheDocument();
    fireEvent.click(within(group).getByRole("button", { name: "Point-in-time" }));
    await screen.findByTestId("index-chart");
    expect(screen.getByText(/Availability is date-level/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Inspect exact PIT inputs/ })).toHaveAttribute("href", "http://127.0.0.1:8000/api/v1/economy/us/mci/point-in-time/2026-10-09");
  });

  test("empty history and retry states are explicit", async () => {
    mockApi(current, [], true);
    openIndex();
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load the current Macro Conditions Index");
    expect(await screen.findByText("No index history available for this range.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry current index" }));
    expect(await screen.findByRole("region", { name: "Current Macro Conditions Index" })).toHaveTextContent("50.0 / 100");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
