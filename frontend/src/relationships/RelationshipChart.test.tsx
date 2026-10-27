import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import type { RelationshipIndicator, RelationshipResponse } from "../api/macrolens";
import { relationshipAxisDomain } from "./relationshipAxes";
import { measureLabel, relationshipSourceName } from "./relationshipDefinitions";
import { setLanguage, tText } from "../i18n/language";
import { RelationshipChart } from "./RelationshipChart";

type TooltipProps = { active: boolean; label: string; payload: Array<{ dataKey: string; value: number; payload: Record<string, string> }> };
let tooltipContent: (props: TooltipProps) => React.ReactNode;

vi.mock("recharts", () => ({
  CartesianGrid: () => null,
  Line: ({ yAxisId, dataKey }: { yAxisId: string; dataKey: string }) =>
    <span data-testid="chart-line" data-axis-id={yAxisId} data-key={dataKey} />,
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Tooltip: ({ content }: { content: typeof tooltipContent }) => { tooltipContent = content; return null; },
  ReferenceLine: ({ y, yAxisId }: { y: number; yAxisId: string }) => <span data-testid="reference-line" data-y={y} data-axis-id={yAxisId} />,
  XAxis: () => null,
  YAxis: ({ yAxisId, orientation, domain, label }: { yAxisId: string; orientation: string; domain: [number, number]; label: {value: string} }) =>
    <span data-testid="y-axis" data-unit={label.value} data-axis-id={yAxisId} data-orientation={orientation} data-domain={JSON.stringify(domain)} />,
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

afterEach(() => { cleanup(); setLanguage("en"); });

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

test("axis bounds cover all finite displayed members with padding, including formerly hidden extremes", () => {
  const rows = [{ left: 4.2, right: -1, third: 120000, left_index: 100 }, { left: 4.6, right: 5.33, third: null, left_index: 160 }, { left: NaN, right: Infinity }];
  const shared = relationshipAxisDomain(rows, ["left", "right"], "actual");
  expect(shared[0]).toBeLessThan(-1); expect(shared[1]).toBeGreaterThan(5.33);
  const unemployment = relationshipAxisDomain(rows, ["left"], "actual");
  expect(unemployment[0]).toBeLessThan(4.2); expect(unemployment[1]).toBeGreaterThan(4.6);
  const indexed = relationshipAxisDomain(rows, ["left"], "indexed");
  expect(indexed[0]).toBeLessThan(100); expect(indexed[1]).toBeGreaterThan(160);
  expect(relationshipAxisDomain([{left: null}], ["left"], "actual")).toEqual([0, 1]);
  for (const value of [0, -5, 4.5]) {
    const domain = relationshipAxisDomain([{left: value}], ["left"], "actual");
    expect(domain[0]).toBeLessThan(value); expect(domain[1]).toBeGreaterThan(value);
  }
});

test("rendered axes receive bounds from their own displayed series", () => {
  const data = response([indicator("left", "UNRATE", "percent"), indicator("right", "BTC", "USD")]);
  data.observations[0].left!.value = 4.5;
  data.observations[0].right = { observation_date: "2026-01-02", value: 120000, normalized_value: 100 };
  const { rerender } = render(<RelationshipChart response={data} labels={labels} mode="actual" />);
  const bounds = screen.getAllByTestId("y-axis").map(axis => JSON.parse(axis.getAttribute("data-domain")!));
  expect(bounds[0][0]).toBeLessThan(4.5); expect(bounds[0][1]).toBeGreaterThan(4.5);
  expect(bounds[1][0]).toBeLessThan(120000); expect(bounds[1][1]).toBeGreaterThan(120000);
  rerender(<RelationshipChart response={data} labels={labels} mode="indexed" />);
  expect(JSON.parse(screen.getByTestId("y-axis").getAttribute("data-domain")!)).toEqual([95, 105]);
});


function pmiResponse() {
  const data = response([indicator("left", "ISM_MANUFACTURING_PMI", "index"), indicator("right", "ISM_SERVICES_PMI", "index")]);
  data.observations = [{period:"2024-01",left:{observation_date:"2024-01-01",value:54.5,normalized_value:null},right:{observation_date:"2024-01-01",value:54.9,normalized_value:null}},
    {period:"2024-02",left:{observation_date:"2024-02-01",value:47,normalized_value:null},right:{observation_date:"2024-02-01",value:57,normalized_value:null}}];
  return data;
}

test("ISM PMI levels share one axis covering both histories with the existing five percent padding", () => {
  render(<RelationshipChart response={pmiResponse()} labels={labels} mode="actual" />);
  const axis = screen.getByTestId("y-axis");
  expect(axis).toHaveAttribute("data-unit","points");
  expect(JSON.parse(axis.getAttribute("data-domain")!)).toEqual([46.5,57.5]);
  for (const line of screen.getAllByTestId("chart-line")) expect(line.getAttribute("data-axis-id")).toBe(axis.getAttribute("data-axis-id"));
  expect(screen.getByTestId("reference-line")).toHaveAttribute("data-y","50");
  expect(screen.getByTestId("reference-line").getAttribute("data-axis-id")).toBe(axis.getAttribute("data-axis-id"));
});

test("reference 50 stays visible when both PMI histories are entirely above it", () => {
  const data=pmiResponse(); data.observations=data.observations.slice(0,1);
  render(<RelationshipChart response={data} labels={labels} mode="actual" />);
  const [min,max]=JSON.parse(screen.getByTestId("y-axis").getAttribute("data-domain")!);
  expect(min).toBeLessThan(50); expect(max).toBeGreaterThan(54.9);
});

test.each(["NFCI", "CPIAUCSL", "NASDAQCOM"])("third index %s retains its own scale and removes the PMI-only reference", third => {
  const data=pmiResponse();data.indicators.push(indicator("third",third,"index"));
  render(<RelationshipChart response={data} labels={labels} mode="actual" />);
  expect(screen.getAllByTestId("y-axis")).toHaveLength(2);
  const lines=screen.getAllByTestId("chart-line");
  expect(lines[0].getAttribute("data-axis-id")).toBe(lines[1].getAttribute("data-axis-id"));
  expect(lines[2].getAttribute("data-axis-id")).not.toBe(lines[0].getAttribute("data-axis-id"));
  expect(screen.queryByTestId("reference-line")).not.toBeInTheDocument();
});

test("PMI with an unrelated index is separate and indexed behavior has no reference 50", () => {
  const data=pmiResponse();data.indicators[1]=indicator("right","NFCI","index");
  const {rerender}=render(<RelationshipChart response={data} labels={labels} mode="actual" />);
  expect(screen.getAllByTestId("y-axis")).toHaveLength(2);
  expect(screen.queryByTestId("reference-line")).not.toBeInTheDocument();
  rerender(<RelationshipChart response={pmiResponse()} labels={labels} mode="indexed" />);
  expect(screen.getAllByTestId("y-axis")).toHaveLength(1);
  expect(screen.queryByTestId("reference-line")).not.toBeInTheDocument();
});

test("ISM names identify the provider in EN/PL and tooltips preserve values and source dates", () => {
  const data=pmiResponse();
  const pmiLabels={...labels,left:measureLabel(data.indicators[0]),right:measureLabel(data.indicators[1])};
  expect(relationshipSourceName(data.indicators[0])).toBe("ISM Manufacturing PMI");
  setLanguage("pl");expect(tText(relationshipSourceName(data.indicators[1]))).toBe("ISM PMI us\u0142ug");setLanguage("en");
  render(<RelationshipChart response={data} labels={pmiLabels} mode="actual" />);
  render(<>{tooltipContent({active:true,label:"2024-01",payload:[{dataKey:"left",value:54.5,payload:{left_date:"2024-01-01"}},{dataKey:"right",value:54.9,payload:{right_date:"2024-01-01"}}]})}</>);
  expect(screen.getByText("54.5")).toBeInTheDocument();expect(screen.getByText("54.9")).toBeInTheDocument();
  expect(screen.getAllByText("Source observation: 2024-01-01")).toHaveLength(2);
  expect(screen.getByText("54.9").textContent).not.toContain("%");
});
