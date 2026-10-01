import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import App from "../App";
import type { RelationshipResponse } from "../api/macrolens";
import { rangeStartDate } from "../charts/chartData";
import { relationshipChartRows } from "./relationshipData";

function comparison(url: URL, correlation: number | null = 1): RelationshipResponse {
  const thirdSeries = url.searchParams.get("third_series");
  const indicators: RelationshipResponse["indicators"] = [
    { key: "left", series_id: url.searchParams.get("left_series")!, feature_name: url.searchParams.get("left_feature"), name: "Left", short_name: "Left", frequency: "monthly", unit: "percent" },
    { key: "right", series_id: url.searchParams.get("right_series")!, feature_name: url.searchParams.get("right_feature"), name: "Right", short_name: "Right", frequency: "daily", unit: "percent" },
  ];
  if (thirdSeries) indicators.push({ key: "third", series_id: thirdSeries, feature_name: url.searchParams.get("third_feature"), name: "Third", short_name: "Third", frequency: "weekly", unit: "percent" });
  const observations: RelationshipResponse["observations"] = [1, 2, 3].map((month) => ({
    period: `2026-0${month}`,
    left: { observation_date: `2026-0${month}-01`, value: month, normalized_value: month * 100 },
    right: { observation_date: `2026-0${month}-28`, value: month * 2, normalized_value: month * 100 },
    ...(thirdSeries ? { third: { observation_date: `2026-0${month}-26`, value: month * 3, normalized_value: month * 100 } } : {}),
  }));
  const comparisons: RelationshipResponse["comparisons"] = [
    { left_key: "left", right_key: "right", overlapping_observation_count: correlation === null ? 2 : 3, correlation },
  ];
  if (thirdSeries) comparisons.push(
    { left_key: "left", right_key: "third", overlapping_observation_count: 3, correlation: 1 },
    { left_key: "right", right_key: "third", overlapping_observation_count: 3, correlation: 1 },
  );
  return {
    history_type: "current_vintage",
    start_date: url.searchParams.get("start_date"), end_date: url.searchParams.get("end_date"),
    comparison_frequency: "monthly", alignment_methodology: "Latest dated observation per calendar month.",
    normalization_base_period: "2026-01", indicators, observations,
    overlapping_observation_count: comparisons[0].overlapping_observation_count,
    correlation, comparisons,
  };
}

function mockApi(mode: "ready" | "null" | "error" | "retry" = "ready") {
  let calls = 0;
  const fetchMock = vi.fn().mockImplementation((input: string | URL) => {
    const url = new URL(String(input));
    if (url.pathname !== "/api/v1/relationships/compare") return new Promise(() => undefined);
    calls += 1;
    if (mode === "error" || (mode === "retry" && calls === 1)) return Promise.resolve({ ok: false });
    return Promise.resolve({ ok: true, json: async () => comparison(url, mode === "null" ? null : 1) });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function openRelationships() {
  window.location.hash = "#/relationships";
  render(<App />);
}

afterEach(() => {
  cleanup();
  window.location.hash = "";
  vi.unstubAllGlobals();
});

describe("Macro Relationships v1", () => {
  test("route, navigation, and explanatory copy render", async () => {
    mockApi();
    window.location.hash = "#/";
    render(<App />);
    fireEvent.click(screen.getByRole("link", { name: "Relationships" }));
    expect(await screen.findByRole("heading", { name: "Macro Relationships" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Relationships" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText(/Correlation describes how two historical series moved together/)).toHaveTextContent("does not establish causation or predict future market moves");
    expect(screen.getByText(/Current-vintage history/).parentElement).toHaveTextContent("not point-in-time historical reconstruction");
  });

  test("selectors, optional third indicator, and ranges update the API request", async () => {
    const fetchMock = mockApi();
    openRelationships();
    await screen.findByRole("heading", { name: "Macro Relationships" });
    fireEvent.change(screen.getByRole("combobox", { name: "First indicator" }), { target: { value: "UNRATE:raw" } });
    fireEvent.change(screen.getByRole("combobox", { name: "Third indicator (optional)" }), { target: { value: "DGS10:raw" } });
    fireEvent.click(within(screen.getByRole("group", { name: "Relationship time range" })).getByRole("button", { name: "5Y" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => {
      const url = new URL(String(input));
      return url.searchParams.get("left_series") === "UNRATE"
        && url.searchParams.get("right_series") === "DFF"
        && url.searchParams.get("third_series") === "DGS10"
        && url.searchParams.get("start_date") === rangeStartDate(5);
    })).toBe(true));
    fireEvent.click(within(screen.getByRole("group", { name: "Relationship time range" })).getByRole("button", { name: "Max" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => {
      const url = new URL(String(input));
      return url.searchParams.get("third_series") === "DGS10" && !url.searchParams.has("start_date");
    })).toBe(true));
  });

  test("quick presets populate both selectors and clear the third", async () => {
    const fetchMock = mockApi();
    openRelationships();
    await screen.findByRole("heading", { name: "Macro Relationships" });
    fireEvent.change(screen.getByRole("combobox", { name: "Third indicator (optional)" }), { target: { value: "DGS10:raw" } });
    fireEvent.click(within(screen.getByRole("group", { name: "Quick comparisons" })).getByRole("button", { name: "Housing Starts vs Mortgage Rate" }));
    expect(screen.getByRole("combobox", { name: "First indicator" })).toHaveValue("HOUST:raw");
    expect(screen.getByRole("combobox", { name: "Second indicator" })).toHaveValue("MORTGAGE30US:raw");
    expect(screen.getByRole("combobox", { name: "Third indicator (optional)" })).toHaveValue("");
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => {
      const url = new URL(String(input));
      return url.searchParams.get("left_series") === "HOUST"
        && url.searchParams.get("right_series") === "MORTGAGE30US"
        && !url.searchParams.has("third_series");
    })).toBe(true));
  });

  test("aligned API values feed the chart in actual and indexed modes", async () => {
    const response = comparison(new URL("http://localhost/api/v1/relationships/compare?left_series=CPIAUCSL&right_series=DFF"));
    expect(relationshipChartRows(response)).toEqual([
      { period: "2026-01", left: 1, left_index: 100, right: 2, right_index: 100 },
      { period: "2026-02", left: 2, left_index: 200, right: 4, right_index: 200 },
      { period: "2026-03", left: 3, left_index: 300, right: 6, right_index: 300 },
    ]);
    mockApi();
    openRelationships();
    expect(await screen.findByRole("region", { name: "Aligned relationship time series chart" })).toBeInTheDocument();
    expect(screen.getByText(/Indexed comparison: 100 at the first shared nonzero period/)).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole("group", { name: "Comparison scale" })).getByRole("button", { name: "Actual values" }));
    expect(screen.getByText(/Actual values share an axis when display units are compatible/)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Aligned relationship time series chart" })).toBeInTheDocument();
  });

  test("correlation, overlapping count, and null correlation display cleanly", async () => {
    mockApi();
    openRelationships();
    const summary = await screen.findByRole("region", { name: "Relationship summary" });
    expect(within(summary).getByText("Pearson correlation")).toBeInTheDocument();
    expect(within(summary).getByText("1.00")).toBeInTheDocument();
    expect(within(summary).getByText("3")).toBeInTheDocument();
    cleanup();
    mockApi("null");
    openRelationships();
    const nullSummary = await screen.findByRole("region", { name: "Relationship summary" });
    expect(within(nullSummary).getByText("Unavailable")).toBeInTheDocument();
    expect(within(nullSummary).getByText("2")).toBeInTheDocument();
  });

  test("API error state can be retried", async () => {
    const fetchMock = mockApi("retry");
    openRelationships();
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load relationship data.");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("region", { name: "Relationship summary" })).toBeInTheDocument();
    expect(fetchMock.mock.calls).toHaveLength(2);
  });
});
