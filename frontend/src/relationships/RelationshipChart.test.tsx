import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import type { RelationshipIndicator, RelationshipResponse } from "../api/macrolens";
import { RelationshipChart } from "./RelationshipChart";

vi.mock("recharts", () => ({
  CartesianGrid: () => null,
  Line: ({ yAxisId, dataKey }: { yAxisId: string; dataKey: string }) =>
    <span data-testid="chart-line" data-axis-id={yAxisId} data-key={dataKey} />,
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: ({ yAxisId, orientation }: { yAxisId: string; orientation: string }) =>
    <span data-testid="y-axis" data-axis-id={yAxisId} data-orientation={orientation} />,
}));

const labels = { left: "First", right: "Second", third: "Third" };

function indicator(key: RelationshipIndicator["key"], seriesId: string, unit: string): RelationshipIndicator {
  return {
    key, series_id: seriesId, feature_name: null, name: seriesId, short_name: seriesId,
    frequency: "monthly", unit,
  };
}

function response(indicators: RelationshipIndicator[]): RelationshipResponse {
  const reading = { observation_date: "2026-01-01", value: 2, normalized_value: 100 };
  return {
    history_type: "current_vintage", start_date: null, end_date: null,
    comparison_frequency: "monthly", alignment_methodology: "Monthly alignment.",
    normalization_base_period: "2026-01", indicators,
    observations: [{ period: "2026-01", left: reading, right: reading, third: reading }],
    overlapping_observation_count: 1, correlation: null,
    comparisons: [{ left_key: "left", right_key: "right", overlapping_observation_count: 1, correlation: null }],
  };
}

afterEach(cleanup);

describe("Relationship chart axis compatibility", () => {
  test.each([
    ["CPI YoY, Fed Funds, and 2Y Treasury", [
      indicator("left", "CPIAUCSL", "percent"),
      indicator("right", "DFF", "percent"),
      indicator("third", "DGS2", "percent"),
    ]],
    ["2Y Treasury, 10Y Treasury, and Fed Funds", [
      indicator("left", "DGS2", "percent"),
      indicator("right", "DGS10", "percent"),
      indicator("third", "DFF", "percent"),
    ]],
  ] as const)("%s share one percentage axis in Actual values mode", (_, indicators) => {
    render(<RelationshipChart response={response([...indicators])} labels={labels} mode="actual" />);
    const axes = screen.getAllByTestId("y-axis");
    expect(axes).toHaveLength(1);
    expect(axes[0]).toHaveAttribute("data-orientation", "left");
    expect(screen.getAllByTestId("chart-line")).toHaveLength(3);
    for (const line of screen.getAllByTestId("chart-line")) {
      expect(line).toHaveAttribute("data-axis-id", axes[0].getAttribute("data-axis-id"));
    }
  });

  test.each([
    ["Housing Starts and Mortgage Rate", "HOUST", "thousands of units, seasonally adjusted annual rate", "MORTGAGE30US", "percent"],
    ["GDP level and Unemployment Rate", "GDPC1", "billions of chained 2017 dollars", "UNRATE", "percent"],
    ["NFCI and Treasury yield", "NFCI", "index", "DGS10", "percent"],
  ])("%s retain separate axes", (_, leftSeries, leftUnit, rightSeries, rightUnit) => {
    render(<RelationshipChart response={response([
      indicator("left", leftSeries, leftUnit), indicator("right", rightSeries, rightUnit),
    ])} labels={labels} mode="actual" />);
    const axes = screen.getAllByTestId("y-axis");
    expect(axes).toHaveLength(2);
    expect(axes[0]).toHaveAttribute("data-orientation", "left");
    expect(axes[1]).toHaveAttribute("data-orientation", "right");
    const lines = screen.getAllByTestId("chart-line");
    expect(lines[0].getAttribute("data-axis-id")).not.toBe(lines[1].getAttribute("data-axis-id"));
  });

  test("matching housing count units share an axis", () => {
    const unit = "thousands of units, seasonally adjusted annual rate";
    render(<RelationshipChart response={response([
      indicator("left", "HOUST", unit),
      indicator("right", "PERMIT", unit),
    ])} labels={labels} mode="actual" />);
    expect(screen.getAllByTestId("y-axis")).toHaveLength(1);
    expect(screen.getAllByTestId("chart-line")[0].getAttribute("data-axis-id"))
      .toBe(screen.getAllByTestId("chart-line")[1].getAttribute("data-axis-id"));
  });

  test("Indexed comparison keeps one index axis for mixed units", () => {
    render(<RelationshipChart response={response([
      indicator("left", "HOUST", "thousands of units, seasonally adjusted annual rate"),
      indicator("right", "MORTGAGE30US", "percent"),
      indicator("third", "NFCI", "index"),
    ])} labels={labels} mode="indexed" />);
    expect(screen.getAllByTestId("y-axis")).toHaveLength(1);
    expect(screen.getByTestId("y-axis")).toHaveAttribute("data-axis-id", "index");
    for (const line of screen.getAllByTestId("chart-line")) {
      expect(line).toHaveAttribute("data-axis-id", "index");
      expect(line.getAttribute("data-key")).toMatch(/_index$/);
    }
  });
});
