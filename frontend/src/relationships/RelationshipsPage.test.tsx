import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import App from "../App";
import "../navigation/ResearchPage";
import "./RelationshipsPage";
import { setLanguage } from "../i18n/language";
import type { RelationshipResponse, RelationshipCatalogSource } from "../api/macrolens";
import { rangeStartDate } from "../charts/chartData";
import { relationshipChartRows } from "./relationshipData";

const catalog: RelationshipCatalogSource[] = [
  ["UNRATE","Unemployment Rate","monthly","percent",["level","change_3m"]],
  ["DFF","Fed Funds Rate","daily","percent",["level"]],
  ["CPIAUCSL","Headline CPI","monthly","index",["mom","yoy"]],
  ["INDPRO","Industrial Production","monthly","index",["mom","yoy"]],
  ["GDPC1","Real GDP","quarterly","billions of chained 2017 dollars",["qoq_annualized","yoy"]],
  ["HOUST","Housing Starts","monthly","thousands",["level","mom"]],
  ["MORTGAGE30US","30Y Mortgage Rate","weekly","percent",["level"]],
  ["DGS10","10Y Treasury","daily","percent",["level"]],
  ["NASDAQCOM","Nasdaq Composite","daily","index points",[]],
  ["CBBTCUSD","Bitcoin","daily","USD",[]],
].map(([series_id,name,frequency,unit,features]) => ({series_id,name,short_name:name,frequency,unit,features,category:["NASDAQCOM","CBBTCUSD"].includes(String(series_id))?"market":"labor",source_kind:["NASDAQCOM","CBBTCUSD"].includes(String(series_id))?"asset":"macro"})) as RelationshipCatalogSource[];

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
    { left_key: "left", right_key: "right", overlapping_observation_count: correlation === null ? 2 : 3, correlation, first_pair_period: "2026-01", last_pair_period: "2026-03" },
  ];
  if (thirdSeries) comparisons.push(
    { left_key: "left", right_key: "third", overlapping_observation_count: 3, correlation: 1 },
    { left_key: "right", right_key: "third", overlapping_observation_count: 3, correlation: 1 },
  );
  return {
    history_type: "current_vintage",
    start_date: url.searchParams.get("start_date"), end_date: url.searchParams.get("end_date"),
    comparison_frequency: "monthly", alignment_methodology: "Latest dated observation per calendar month.",
    indexing: { available: true, reason: null }, normalization_base_period: "2026-01", indicators, observations,
    overlapping_observation_count: comparisons[0].overlapping_observation_count,
    correlation, comparisons,
  };
}

function mockApi(mode: "ready" | "null" | "error" | "retry" = "ready") {
  let calls = 0;
  const fetchMock = vi.fn().mockImplementation((input: string | URL) => {
    const url = new URL(String(input));
    if (url.pathname === "/api/v1/relationships/sources") return Promise.resolve({ ok: true, json: async () => ({ sources: catalog, history_type: "current_vintage", feature_policy: "Calendar checks" }) });
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
  cleanup(); setLanguage("en");
  window.location.hash = "";
  vi.unstubAllGlobals();
});

describe("Macro Relationships v1", () => {
  test("route, navigation, and explanatory copy render", async () => {
    mockApi();
    window.location.hash = "#/";
    render(<App />);
    fireEvent.click(screen.getByRole("link", { name: "Research" }));
    fireEvent.click(await screen.findByRole("link", { name: "Compare Data" }));
    expect(await screen.findByRole("heading", { name: "Compare Data" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Research" })).toHaveAttribute("aria-current", "page");
    expect(await screen.findByText(/Correlation describes how two historical series moved together/)).toHaveTextContent("does not establish causation or predict future market moves");
    expect(screen.getByText(/Historical observations use the latest stored values/)).toHaveTextContent("not point-in-time historical reconstruction");
    expect(screen.getByText("Method and limitations").closest("details")).not.toHaveAttribute("open");
    expect(screen.queryByRole("group", { name: "Quick comparisons" })).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Series 3 data" })).not.toBeInTheDocument();
  });

  test("selectors, optional third indicator, and ranges update the API request", async () => {
    const fetchMock = mockApi();
    openRelationships();
    await screen.findByRole("combobox", { name: "Series 1 data" });
    fireEvent.change(screen.getByRole("combobox", { name: "Series 1 data" }), { target: { value: "UNRATE" } });
    fireEvent.click(screen.getByRole("button", { name: "Add series" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Series 3 data" }), { target: { value: "DGS10" } });
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
    await screen.findByRole("combobox", { name: "Series 1 data" });
    fireEvent.click(screen.getByRole("button", { name: "Add series" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Series 3 data" }), { target: { value: "DGS10" } });
    fireEvent.click(screen.getByRole("button", { name: "Example comparisons" }));
    fireEvent.click(within(screen.getByRole("group", { name: "Quick comparisons" })).getByRole("button", { name: "Housing Starts vs Mortgage Rate" }));
    expect(screen.getByRole("combobox", { name: "Series 1 data" })).toHaveValue("HOUST");
    expect(screen.getByRole("combobox", { name: "Series 2 data" })).toHaveValue("MORTGAGE30US");
    expect(screen.queryByRole("combobox", { name: "Series 3 data" })).not.toBeInTheDocument();
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
      { period: "2026-01", left_date: "2026-01-01", right_date: "2026-01-28", left: 1, left_index: 100, right: 2, right_index: 100 },
      { period: "2026-02", left_date: "2026-02-01", right_date: "2026-02-28", left: 2, left_index: 200, right: 4, right_index: 200 },
      { period: "2026-03", left_date: "2026-03-01", right_date: "2026-03-28", left: 3, left_index: 300, right: 6, right_index: 300 },
    ]);
    mockApi();
    openRelationships();
    expect(await screen.findByRole("region", { name: "Aligned relationship time series chart" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Index 100" }));
    expect(screen.getByText(/Indexed comparison: 100 at the first shared nonzero period/)).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole("group", { name: "Comparison scale" })).getByRole("button", { name: "Values" }));
    expect(screen.getByText(/Actual values share an axis when display units are compatible/)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Aligned relationship time series chart" })).toBeInTheDocument();
  });

  test("correlation, overlapping count, and null correlation display cleanly", async () => {
    mockApi();
    openRelationships();
    const summary = await screen.findByRole("region", { name: "Relationship summary" });
    expect(within(summary).getByText("Pearson r")).toBeInTheDocument();
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
    expect(fetchMock.mock.calls).toHaveLength(3);
  });
});


test("dynamic catalog supports macro + Bitcoin and separate macro transformations", async () => {
  const fetch = mockApi(); openRelationships(); await screen.findByRole("combobox",{name:"Series 2 data"});
  fireEvent.change(screen.getByRole("combobox",{name:"Series 2 data"}),{target:{value:"INDPRO"}});
  fireEvent.change(screen.getByRole("combobox",{name:"Series 2 measure"}),{target:{value:"mom"}});
  fireEvent.click(screen.getByRole("button",{name:"Add series"}));
  fireEvent.change(screen.getByRole("combobox",{name:"Series 3 data"}),{target:{value:"CBBTCUSD"}});
  expect(screen.queryByRole("combobox",{name:"Series 3 measure"})).not.toBeInTheDocument();
  expect(screen.getByText("Price · USD")).toBeInTheDocument();
  await waitFor(()=>expect(fetch.mock.calls.some(([input])=>{const p=new URL(String(input)).searchParams;return p.get("left_series")==="UNRATE"&&p.get("right_series")==="INDPRO"&&p.get("right_feature")==="mom"&&p.get("third_series")==="CBBTCUSD"&&!p.has("third_feature");})).toBe(true));
  fireEvent.click(screen.getByRole("button",{name:"Remove series"}));
  await waitFor(()=>expect(new URL(String(fetch.mock.calls[fetch.mock.calls.length - 1][0])).searchParams.has("third_series")).toBe(false));
});

test("macro + Nasdaq Composite + Bitcoin are selected without a new provider or Nasdaq-100 label", async () => {
  const fetch=mockApi();openRelationships();await screen.findByRole("combobox",{name:"Series 2 data"});
  fireEvent.change(screen.getByRole("combobox",{name:"Series 2 data"}),{target:{value:"NASDAQCOM"}});
  fireEvent.click(screen.getByRole("button",{name:"Add series"}));
  fireEvent.change(screen.getByRole("combobox",{name:"Series 3 data"}),{target:{value:"CBBTCUSD"}});
  expect(screen.queryByRole("option",{name:"Nasdaq-100"})).not.toBeInTheDocument();
  expect(within(screen.getByRole("combobox",{name:"Series 2 data"})).getByRole("option",{name:"Nasdaq Composite"})).toBeInTheDocument();
  await waitFor(()=>expect(fetch.mock.calls.some(([input])=>{const p=new URL(String(input)).searchParams;return p.get("right_series")==="NASDAQCOM"&&p.get("third_series")==="CBBTCUSD";})).toBe(true));
});

test("API indexing restriction keeps actual values and shows the reason, gaps and actual pair range", async () => {
  const fetch=mockApi();fetch.mockImplementation(async(input:string|URL)=>{const url=new URL(String(input));if(url.pathname.endsWith('/sources'))return {ok:true,json:async()=>({sources:catalog})};
    const result=comparison(url);result.indexing={available:false,reason:"Indexed comparison requires positive levels and a shared period. Growth rates, rates, changes, CFNAI and NFCI are excluded."};result.normalization_base_period=null;result.indicators[0].excluded_observation_count=2;return {ok:true,json:async()=>result};});
  openRelationships();await screen.findByRole("region",{name:"Relationship summary"});
  expect(screen.getByRole("button",{name:"Index 100"})).toBeDisabled();expect(screen.getByRole("button",{name:"Values"})).toHaveAttribute("aria-pressed","true");
  const reason = screen.getByRole("button", { name: "Why Index 100 is unavailable" });
  reason.focus(); expect(reason).toHaveFocus();
  expect(reason).toHaveAccessibleDescription("Indexed comparison requires positive levels and a shared period. Growth rates, rates, changes, CFNAI and NFCI are excluded.");
  fireEvent.keyDown(reason, { key: "Escape" }); expect(reason).not.toHaveFocus();
  expect(screen.getByText(/calendar dependencies could not be verified/)).toHaveTextContent("2");
  expect(screen.getByText("2026-01 through 2026-03")).toBeInTheDocument();
  expect(screen.getByText(/Observation periods are not publication dates/)).toBeInTheDocument();
});

test("scale and EN/PL changes do not reload data or change correlation samples", async () => {
  const fetch=mockApi();openRelationships();await screen.findByRole("region",{name:"Relationship summary"});
  const count=fetch.mock.calls.length;fireEvent.click(screen.getByRole("button",{name:"Index 100"}));
  fireEvent.click(screen.getByRole("button",{name:"Polski"}));
  expect(fetch.mock.calls).toHaveLength(count);expect(screen.getByRole("combobox",{name:"Seria 1: miara"})).toBeInTheDocument();
  expect(screen.getByRole("heading",{name:"Por\u00f3wnaj dane"})).toBeInTheDocument();
});

test("catalog loading and error are explicit and retry uses the same configured catalog endpoint", async () => {
  vi.stubGlobal("fetch",vi.fn(()=>new Promise(()=>undefined)));openRelationships();await screen.findByText("Loading configured sources...");cleanup();
  const fetch=vi.fn().mockResolvedValue({ok:false});vi.stubGlobal("fetch",fetch);openRelationships();await screen.findByRole("alert");
  expect(screen.getByText("Unable to load configured sources.")).toBeInTheDocument();fireEvent.click(screen.getByRole("button",{name:"Retry"}));
  await waitFor(()=>expect(fetch.mock.calls).toHaveLength(2));
});

test("duplicate measures do not issue a comparison until the selection is valid", async () => {
  const fetch=mockApi();openRelationships();await screen.findByRole("region",{name:"Relationship summary"});
  const count=fetch.mock.calls.length;
  fireEvent.change(screen.getByRole("combobox",{name:"Series 2 data"}),{target:{value:"UNRATE"}});
  expect(screen.getByRole("alert")).toHaveTextContent("Select distinct measures.");expect(fetch.mock.calls).toHaveLength(count);
  fireEvent.change(screen.getByRole("combobox",{name:"Series 2 measure"}),{target:{value:"change_3m"}});
  await waitFor(()=>expect(fetch.mock.calls.length).toBeGreaterThan(count));
});

test("opening examples or methodology preserves selections and does not request data", async () => {
  const fetch = mockApi(); openRelationships();
  await screen.findByRole("region", { name: "Relationship summary" });
  const count = fetch.mock.calls.length;
  fireEvent.click(screen.getByRole("button", { name: "Example comparisons" }));
  fireEvent.click(screen.getByRole("button", { name: "Example comparisons" }));
  fireEvent.click(screen.getByText("Method and limitations"));
  expect(screen.getByRole("combobox", { name: "Series 1 data" })).toHaveValue("UNRATE");
  expect(screen.getByRole("combobox", { name: "Series 2 data" })).toHaveValue("DFF");
  expect(screen.queryByRole("combobox", { name: "Series 2 measure" })).not.toBeInTheDocument();
  expect(fetch.mock.calls).toHaveLength(count);
});
