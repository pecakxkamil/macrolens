import { explanationAuditMarkdown } from "./explanationAudit";
import { economicExplanation } from "./economicExplanations";
import { economicInterpretation } from "./economicInterpretation";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "../App";
import { EconomyBrief } from "./EconomyBrief";
// Compile the optional module during collection, outside the DOM wait budget.
// Cold import ordering is exercised by lazyLoading and production-preview tests.
import "./ReadingExplanation";
import { readingHoverLines } from "./readingHoverText";
import { upcomingEventReport } from "./upcomingEvents";
import { briefMarkdown, briefModel, domainSelection, eventText } from "./briefModel";
import { prepareFedTarget, fedTargetReportLine } from "./fedTarget";
import { comparisonTone, prepareReading, readingNumber, readingReportLine, readingLabels } from "./readingComparisons";
import { setLanguage } from "../i18n/language";
import type { EconomyBriefResponse, OverviewReadingComparison, UsaEconomyNow } from "../api/macrolens";
import snapshot from "../../../tests/fixtures/macro_state_snapshot.json";

function fixture(): EconomyBriefResponse {
  const readings = domainSelection.flatMap((domain) => domain.readings.map(([component, series_id]): OverviewReadingComparison => {
    const frequency = component === "real_gdp" ? "quarterly" : ["initial_claims", "mortgage_rate", "nfci"].includes(component) ? "weekly" : ["fed_funds_rate", "yield_curve_2s10s"].includes(component) ? "daily" : "monthly";
    const dates = frequency === "quarterly" ? ["2026-07-01", "2026-04-01", "2025-10-01"] : frequency === "weekly" ? ["2026-10-03", "2026-09-26", "2026-09-12"] : frequency === "daily" ? ["2026-10-07", "2026-10-06", "2026-10-01"] : ["2026-09-01", "2026-08-01", "2026-06-01"];
    const feature_name = component === "payrolls" ? "monthly_change" : ["initial_claims", "manufacturing_pmi", "services_pmi"].includes(component) ? "raw" : component === "real_gdp" ? "qoq_annualized" : component === "yield_curve_2s10s" ? "spread" : ["headline_cpi", "core_cpi", "core_pce", "industrial_production", "real_consumption", "real_disposable_income", "retail_sales", "average_hourly_earnings", "producer_ppi"].includes(component) ? "mom" : "level";
    const unit = component === "payrolls" ? "thousands" : component === "initial_claims" ? "claims" : component === "job_openings" ? "thousands of openings" : ["cfnai", "nfci", "manufacturing_pmi", "services_pmi"].includes(component) ? "index" : ["housing_starts", "building_permits"].includes(component) ? "thousands SAAR" : component === "yield_curve_2s10s" ? "percentage points" : "percent";
    const change_unit = unit === "percent" ? "percentage points" : unit === "index" ? "index points" : unit;
    const current = component === "job_openings" ? 7250 : component === "initial_claims" ? 199000 : component === "unemployment" ? 4.2 : feature_name === "mom" ? .3 : 3.2, previous = component === "job_openings" ? 7100 : component === "initial_claims" ? 198000 : component === "unemployment" ? 4.1 : feature_name === "mom" ? .1 : 3;
    return { domain: domain.key, component, series_id, feature_name, label: readingLabels[component], frequency, unit, change_unit,
      current: { value: current, observation_date: dates[0], feature_as_of_date: "2026-10-08" },
      previous: { value: previous, observation_date: dates[1], feature_as_of_date: "2026-10-08" },
      three_periods_ago: { value: 2.8, observation_date: dates[2], feature_as_of_date: "2026-10-08" },
      context_moving_average_4w: component === "initial_claims" ? {value: 198500, observation_date: dates[0], feature_as_of_date: "2026-10-08"} : null,
      context_yoy: feature_name === "mom" && series_id !== "PPIFIS" ? { current: { value: 3.2, observation_date: dates[0], feature_as_of_date: "2026-10-08" }, previous: { value: 3, observation_date: dates[1], feature_as_of_date: "2026-10-08" }, three_periods_ago: { value: 2.8, observation_date: dates[2], feature_as_of_date: "2026-10-08" } } : null,
      change: current - previous, change_type: "Difference from previous calendar month", latest_stored_observation_date: dates[0], expected_previous_observation_date: dates[1], expected_three_periods_ago_date: dates[2] };
  }));
  return { assembled_at: "2026-10-18T12:30:00+02:00", timezone: "Europe/Warsaw", history_type: "current_vintage",
    snapshot: { status: "ready", data: snapshot as UsaEconomyNow, error: null }, state: { status: "unavailable", data: null, error: "State unavailable" },
    fed_target: { status: "ready", error: null, data: { availability: "available", lower: 3.75, upper: 4, observation_date: "2026-10-18", effective_date: "2026-09-17", retrieved_at: "2026-10-19T11:00:00Z", last_rate_change: { effective_date: "2026-09-17", lower_change_bps: 25, upper_change_bps: 25, change_bps: 25, previous_lower: 3.5, previous_upper: 3.75 }, sources: ["DFEDTARL", "DFEDTARU"].map(series_id => ({ series_id, url: `https://fred.stlouisfed.org/series/${series_id}`, observation_date: "2026-10-18", retrieved_at: "2026-10-19T11:00:00Z" })) } },
    reading_comparisons: { status: "ready", data: readings, error: null }, changes: { status: "ready", data: [], error: null }, calendar_start_date: "2026-10-18", calendar_end_date: "2026-10-24",
    calendar: { status: "ready", error: null, data: { start_date: "2026-10-18", end_date: "2026-10-24", category: null,
      events: [{ release_id: 10, release_name: "Gross Domestic Product", release_date: "2026-10-20", release_time: "08:30:00", source_timezone: "America/New_York", release_datetime_utc: "2026-10-20T12:30:00Z", importance: "high", source_link: "https://www.bea.gov/", date_precision: "date", series: [{ series_id: "GDPC1", name: "Real GDP", short_name: "Real GDP", category: "growth", frequency: "quarterly", unit: "billions" }] }] } },
  };
}
function mockApi(data = fixture()) {
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => data });
  vi.stubGlobal("fetch", fetch); return fetch;
}
beforeEach(() => { vi.useFakeTimers({ toFake: ["Date"] }); vi.setSystemTime(new Date("2026-10-18T10:00:00Z")); });
afterEach(() => { vi.useRealTimers(); cleanup(); setLanguage("en"); vi.unstubAllGlobals(); vi.restoreAllMocks(); window.location.hash = ""; });

test("Overview prioritizes 21 numeric readings and a Fed target range across six domains and preserves four navigation links", async () => {
  const fetch = mockApi(); render(<App />); await screen.findByRole("heading", { name: "Labor" });
  expect(document.querySelectorAll(".overview-domain")).toHaveLength(6);
  expect(document.querySelectorAll(".overview-reading-row")).toHaveLength(21);
  for (const card of document.querySelectorAll(".overview-domain")) {
    expect(card.querySelectorAll(":scope > table")).toHaveLength(1); expect(card.querySelector("details")).toBeNull();
    const visible = card.cloneNode(true) as HTMLElement; visible.querySelectorAll("details").forEach(detail => detail.remove());
    expect(visible.textContent).not.toMatch(/momentum|accelerating|decelerating|Feature as-of|PAYEMS|CPIAUCSL/);
  }
  expect(within(screen.getByRole("navigation")).getAllByRole("link")).toHaveLength(4);
  expect(screen.queryByText("At a glance")).not.toBeInTheDocument();
  expect(screen.queryByText("Latest reading comparisons")).not.toBeInTheDocument();
  expect(screen.queryByText("Supporting MCI")).not.toBeInTheDocument();
  expect(screen.queryByText("Cross-currents")).not.toBeInTheDocument();
  expect(screen.queryByText("How this is assessed")).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(1); expect(String(fetch.mock.calls[0][0])).toMatch(/\/brief$/);
});

test("domain tables keep two values and periods with no replacement disclosures", async () => {
  const data = fixture(), fetch = mockApi(data); render(<EconomyBrief />); await screen.findByRole("heading", { name: "Labor" });
  const model = briefModel(data);
  for (const domain of model.domains) {
    const card = screen.getByRole("article", { name: `${domain.name} brief` });
    for (const reading of domain.compact) {
      const row = within(card).getByRole("row", { name: reading.label }), cells = row.querySelectorAll("td");
      expect(cells).toHaveLength(2);
      expect(cells[0].querySelector("strong")).toHaveTextContent(reading.key === "initial_claims" ? reading.current.screenValue : reading.current.display);
      expect(cells[1].querySelector("strong")).toHaveTextContent(reading.key === "initial_claims" ? reading.previous.screenValue : reading.previous.display);
      expect(row.querySelector("th time")).toHaveTextContent(reading.current.period);
      expect(cells[1].querySelector("time")).toHaveTextContent(reading.previous.period);
      expect(within(row).getByRole("link")).toHaveAttribute("href", reading.indicatorHref);
      expect(within(row).queryByRole("link", { name: /source/i })).not.toBeInTheDocument();
    }
    expect(within(card).queryByText("More comparisons")).not.toBeInTheDocument();
  }
  expect(fetch).toHaveBeenCalledTimes(1);
});

test.each([
  ["CPI MoM", "Previous month", "3 months earlier", "Jun 2026"],
  ["Real GDP QoQ, annualized", "Previous quarter", "3 quarters earlier", "Q4 2025"],
  ["Initial jobless claims", "Previous week", "3 weeks earlier", "Sep 12, 2026"],
  ["10Y–2Y Treasury spread", "Previous observation", "3 observations earlier", "Oct 1, 2026"],
])("%s labels the correct comparison frequency", async (name, previous, earlier, day) => {
  const data = fixture(); mockApi(data); render(<EconomyBrief />); const row = await screen.findByRole("row", { name });
  const reading = briefModel(data).domains.flatMap(d => d.compact).find(r => r.label === name)!;
  expect(reading.labels.previous).toBe(previous); expect(reading.labels.earlier).toBe(earlier);
  expect(briefMarkdown(briefModel(data), data, data.assembled_at)).toContain(day);
  expect(row.querySelectorAll("time")).toHaveLength(2);

});

test.each([
  ["unemployment", 4.2, 4.1, "positive"], ["unemployment", 4.1, 4.2, "negative"],
  ["initial_claims", 210000, 200000, "positive"], ["initial_claims", 190000, 200000, "negative"],
  ["payrolls", 200, 100, "positive"], ["payrolls", 100, 200, "negative"],
  ["real_gdp", 3, 2, "positive"], ["real_consumption", 1, 2, "negative"],
  ["industrial_production", 3, 2, "positive"], ["real_disposable_income", 3, 2, "positive"],
  ["headline_cpi", 2, 3, "negative"], ["core_pce", 3, 2, "positive"],
  ["headline_cpi", -.1, .1, "negative"], ["core_cpi", .1, -.1, "positive"],
  ["core_pce", -.2, -.1, "negative"],
  ["yield_curve_2s10s", 1, .5, "positive"], ["mortgage_rate", 7, 6, "positive"],
  ["retail_sales", 5, 4, "positive"], ["nfci", .2, .1, "positive"],
  ["unemployment", 4, 4, "neutral"],
])("direction for %s (%s vs %s) has explicit presentation color %s", (component, current, previous, tone) => {
  const item = fixture().reading_comparisons!.data!.find(x => x.component === component)!;
  item.current!.value = current as number; item.previous!.value = previous as number; item.change = (current as number) - (previous as number);
  expect(comparisonTone(item)).toBe(tone);
  const reading = prepareReading(item.component, item.series_id, item);
  expect(reading.arrow).toBe(current === previous ? "\u2014" : current > previous ? "\u2191" : "\u2193");
});

test("arrow color expresses numerical direction independently from its economic marker", async () => {
  mockApi(); render(<EconomyBrief />); const region = await screen.findByRole("row", { name: "Unemployment rate" });
  expect(region.querySelector(".overview-change")).toHaveClass("overview-change--positive");
  expect(region.querySelector(".overview-change")).toHaveTextContent("\u2191");
  expect(region.querySelector(".overview-value--latest strong")).toHaveTextContent("4.2");
  expect(region.querySelector(".overview-value--latest strong")?.className).toBe("");
});

test("missing required periods stay blank with their expected dates; zero stays numeric", async () => {
  const data = fixture(), item = data.reading_comparisons!.data![1];
  item.previous = null; item.three_periods_ago!.value = 0; item.change = null;
  mockApi(data); render(<EconomyBrief />); const region = await screen.findByRole("row", { name: "Unemployment rate" });
  const cells = region.querySelectorAll("td"); expect(cells[1]).toHaveTextContent("\u2014"); expect(cells[1]).toHaveTextContent("Aug 2026");
  expect(briefModel(data).domains[0].compact[1].earlier.value).toBe("0.0");
  expect(region.querySelector(".overview-change")).toHaveClass("overview-change--neutral");
  expect(briefMarkdown(briefModel(data), data, data.assembled_at)).toContain("Previous month: \u2014 (Aug 2026)");
});

test("unavailable histories do not fall back to different snapshot measures or fabricate values", async () => {
  const data = fixture(); data.reading_comparisons = { status: "unavailable", data: null, error: "Unavailable" };
  mockApi(data); render(<EconomyBrief />); await screen.findByText("Reading comparisons unavailable.");
  for (const cell of document.querySelectorAll(".overview-values tbody strong")) expect(cell).toHaveTextContent("\u2014");
  expect(screen.getByRole("button", { name: "Download report" })).toBeEnabled();
});

test("all screen comparisons share the same prepared data and text with the Markdown main section", () => {
  const data = fixture(), model = briefModel(data), report = briefMarkdown(model, data, data.assembled_at), main = report.split("## Audit details")[0];
  for (const domain of model.domains) for (const reading of domain.compact) expect(main).toContain(readingReportLine(reading));
  expect(main).not.toMatch(/momentum|accelerating|decelerating|Latest reading comparisons|Feature as-of|qoq_annualized/);
  expect(report).toContain("2026-10-08"); expect(report).toContain("(PAYEMS, monthly_change)");
  expect(report).toContain("feature as-of"); expect(main).toContain("earlier values may include revisions");
});

test("Markdown download uses the loaded aggregate without PIT/history requests or refetching", async () => {
  const data = fixture(), fetch = mockApi(data); render(<EconomyBrief />); await screen.findByRole("heading", { name: "Labor" });
  const create = vi.fn().mockReturnValue("blob:test"), revoke = vi.fn();
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: create }); Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revoke });
  let filename = ""; vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function(this: HTMLAnchorElement) { filename = this.download; });
  fireEvent.click(screen.getByRole("button", { name: "Download report" }));
  expect(fetch).toHaveBeenCalledTimes(1); expect(filename).toMatch(/^macrolens-economy-brief-.*\.md$/);
  const text = await new Promise<string>(resolve => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.readAsText(create.mock.calls[0][0]); });
  expect(text).toContain(readingReportLine(briefModel(data).domains[0].compact[1]));
  expect(text).not.toMatch(/\n{3,}/); expect(text).not.toContain("qoq\\_annualized");
  const urls = [...text.matchAll(/\]\(([^)]+)\)/g)].map(match => match[1]); expect(new Set(urls).size).toBe(urls.length);
  await waitFor(() => expect(revoke).toHaveBeenCalledWith("blob:test"));
});

test("EN/PL translates labels, formats values and exports the same periods without extra requests", async () => {
  const data = fixture(), fetch = mockApi(data); render(<App />); await screen.findByRole("heading", { name: "Labor" });
  fireEvent.click(screen.getByRole("button", { name: "Polski" }));
  const table = document.querySelector(".overview-domain-table");
  expect(table).toHaveTextContent("4,2"); expect(table).toHaveTextContent("Poprzednio"); expect(screen.queryByText("Wi\u0119cej por\u00f3wna\u0144")).not.toBeInTheDocument();
  const report = briefMarkdown(briefModel(data), data, data.assembled_at);
  expect(report).toContain("4,2"); expect(report).toContain("3 miesi"); expect(report).toContain("https://fred.stlouisfed.org/series/UNRATE");
  expect(document.documentElement.lang).toBe("pl"); expect(fetch).toHaveBeenCalledTimes(1);
});

test("repeated low releases remain grouped and all dates are kept in the report", async () => {
  const data = fixture(), original = data.calendar.data!.events[0];
  data.calendar.data!.events.push(...[19,20,21].map(day => ({ ...original, release_id: 15, release_name: "H.15 Selected Interest Rates", importance: "low" as const, release_datetime_utc: null, release_time: null, source_timezone: null, release_date: `2026-10-${day}`, source_link: "https://www.federalreserve.gov/releases/h15/" })));
  mockApi(data); render(<EconomyBrief />); await screen.findByRole("heading", {name: "Upcoming events"});
  expect(document.querySelector(".overview-other-events")).toBeNull();
  const report = briefMarkdown(briefModel(data), data, data.assembled_at); for (const day of [19,20,21]) expect(report).toContain(`2026-10-${day}`);
  expect(document.querySelectorAll(".overview-domain")[5].compareDocumentPosition(document.querySelector('[aria-labelledby="brief-events"]')! ) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

test("empty and unavailable calendar states stay distinct", async () => {
  const data = fixture(); data.calendar.data!.events = []; mockApi(data); const { unmount } = render(<EconomyBrief />);
  await screen.findByText("No key upcoming events in the stored 7-day window."); unmount();
  data.calendar = { status: "unavailable", data: null, error: "Unavailable" }; mockApi(data); render(<EconomyBrief />);
  await screen.findAllByText("Release calendar unavailable; upcoming coverage is unknown.");
});

test("transport error allows retry and disables export until data arrives", async () => {
  const fetch = mockApi(); fetch.mockRejectedValueOnce(new Error("offline")); render(<EconomyBrief />); await screen.findByRole("alert");
  expect(screen.getByRole("button", { name: "Download report" })).toBeDisabled(); fireEvent.click(screen.getByRole("button", { name: "Retry brief" }));
  await screen.findByRole("heading", { name: "Labor" }); expect(screen.getByRole("button", { name: "Download report" })).toBeEnabled();
});

test("small differences remain exact in details while the main display rounds consistently", () => {
  expect(readingNumber(.00001, "percentage points")).toBe("0.00");
  const item = fixture().reading_comparisons!.data!.find(row => row.component === "headline_cpi")!;
  item.change = .00001;
  expect(prepareReading(item.component, item.series_id, item).exactDifference).toBe("+0.00001 pp");
});

test("release times remain timezone-aware across the US/Polish DST mismatch", () => {
  const event = fixture().calendar.data!.events[0]; expect(eventText(event)).toContain("14:30 PL");
  expect(eventText({ ...event, release_date: "2026-03-16", release_datetime_utc: "2026-03-16T12:30:00Z" })).toContain("13:30 PL");
  expect(eventText({ ...event, release_datetime_utc: null })).toContain("Time unavailable");
});

test("next FOMC decision is independent of seven-day preview, with DST-aware time and report provenance", async () => {
  const data = fixture();
  data.policy = { status: "ready", error: null, data: { schedule_status: "available", retrieved_at: "2026-10-19T09:00:00Z", source_url: "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", market_probabilities: { status: "not_integrated", source_url: "https://www.cmegroup.com/fedwatch" },
    next_decision: { release_id: null, event_id: "fomc:2026-10-28", event_type: "fomc_decision", release_name: "FOMC policy decision", release_date: "2026-10-28", meeting_start_date: "2026-10-27", meeting_end_date: "2026-10-28", release_time: "14:00:00", source_timezone: "America/New_York", release_datetime_utc: "2026-10-28T18:00:00Z", retrieved_at: "2026-10-19T09:00:00Z", time_source_url: "https://www.federalreserve.gov/newsevents/2026-october.htm", importance: "high", source_link: "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", date_precision: "date", series: [] } } };
  mockApi(data); render(<EconomyBrief />);
  await screen.findByText(/Oct 28.*19:00 PL/);
  expect(screen.queryByRole("link", { name: "View market probabilities on CME FedWatch" })).not.toBeInTheDocument();
  const model = briefModel(data);
  const report = briefMarkdown(model, data, data.assembled_at);
  const main = report.split("## Audit details")[0];
  expect(main).toContain(upcomingEventReport(data.policy!.data!.next_decision!));
  expect(main).toContain("[View market probabilities on CME FedWatch](https://www.cmegroup.com/fedwatch)");
  expect(main).toContain("CME probabilities are not integrated. ISM PMI uses locally imported release tables");
  expect(main).not.toContain("Feature as-of:"); expect(main).not.toContain("[qoq_annualized]");
  for (const domain of model.domains) for (const reading of domain.compact) expect(main).toContain(readingReportLine(reading));
  expect(report).toContain(model.policy.metadata);
  expect(data.calendar.data!.events).toHaveLength(1);
});


test("level differences share the row unit while rate changes retain explicit percentage points", () => {
  const data = fixture();
  const housing = data.reading_comparisons!.data!.find(item => item.component === "housing_starts")!;
  const prepared = prepareReading(housing.component, housing.series_id, housing);
  expect(prepared.unit).toBe("thousand homes/year (annualized)");
  expect(prepared.compactChange).toBe("0 k");
  expect(prepared.change).toContain("thousand homes/year (annualized)");
  const unemployment = data.reading_comparisons!.data![1];
  expect(prepareReading(unemployment.component, unemployment.series_id, unemployment).compactChange).toContain("pp");
});


test("eight monthly activity/inflation and wage rows compare MoM and show same-month YoY context", async () => {
  const data = fixture(); mockApi(data); render(<EconomyBrief />); await screen.findByRole("heading", { name: "Labor" });
  for (const item of data.reading_comparisons!.data!.filter(row => row.feature_name === "mom" && row.series_id !== "PPIFIS")) {
    const region = screen.getByRole("row", { name: item.label });
    const points = region.querySelectorAll("td");
    expect(points[0].querySelector("strong")).toHaveTextContent("0.3");
    expect(points[1].querySelector("strong")).toHaveTextContent("0.1");
    expect(points[0].querySelector(".overview-yoy")).toHaveTextContent("3.20% YoY");
    expect(region.querySelector(".overview-change")).toHaveTextContent("\u2191");
    expect(points[1].querySelector(".overview-yoy")).toBeNull();
    expect(item.context_yoy!.current!.observation_date).toBe(item.current!.observation_date);
  }
  expect(data.reading_comparisons!.data!.filter(row => row.feature_name === "mom" && row.series_id !== "PPIFIS")).toHaveLength(8);
  expect(data.reading_comparisons!.data!.find(row => row.component === "real_gdp")!.feature_name).toBe("qoq_annualized");
});

test("YoY from another month is never shown next to current MoM", async () => {
  const data = fixture(), cpi = data.reading_comparisons!.data!.find(row => row.component === "headline_cpi")!;
  cpi.context_yoy!.current!.observation_date = "2026-08-01";
  mockApi(data); render(<EconomyBrief />); const region = await screen.findByRole("row", { name: "CPI MoM" });
  expect(region.querySelector(".overview-yoy")).toHaveTextContent("\u2014 YoY");
  expect(region.querySelector(".overview-yoy")).not.toHaveTextContent("3.2");
  expect(readingReportLine(briefModel(data).domains[1].compact[0])).toContain("YoY: \u2014");
});

test("Fed target block shows bounds, effective date, last rate change and explicit data freshness", async () => {
  const data = fixture(); mockApi(data); render(<EconomyBrief />); const block = await screen.findByRole("region", { name: "Fed target range" });
  expect(block).toHaveTextContent("3.75\u20134.00%"); expect(block).toHaveTextContent("Effective sinceSep 17, 2026");
  expect(block).toHaveTextContent("Last rate change+25 bp"); expect(block).not.toHaveTextContent("Observed through");
  expect(block).not.toHaveTextContent("Retrieved"); expect(block).not.toHaveTextContent("Last decision");
  expect(block.querySelector("table")).toBeNull();
  expect(within(block).getByRole("link")).toHaveAttribute("href", "#/explore/indicators/DFEDTARL");
  expect(screen.queryByRole("region", { name: "Effective Fed Funds Rate" })).not.toBeInTheDocument();
  const model = briefModel(data); expect(briefMarkdown(model, data, data.assembled_at)).toContain(fedTargetReportLine(model.fedTarget));
});

test("unavailable official bounds never fall back to snapshot DFF", async () => {
  const data = fixture(); data.fed_target = { status: "unavailable", data: null, error: "Unavailable" };
  mockApi(data); render(<EconomyBrief />); const block = await screen.findByRole("region", { name: "Fed target range" });
  expect(block.querySelector(".overview-target-value")).toHaveTextContent("\u2014");
  expect(block).not.toHaveTextContent(String(snapshot.financial_conditions.fed_funds_rate.level));
  expect(prepareFedTarget(data.fed_target).lastChange).toBe("\u2014");
});


test("Fed retrieval date uses Poland local time while observation date remains the source date", () => {
  const data = fixture(); data.fed_target!.data!.retrieved_at = "2026-10-18T23:30:00Z";
  const prepared = prepareFedTarget(data.fed_target);
  expect(prepared.retrieved).toBe("Oct 19, 2026");
  expect(prepared.observed).toBe("Oct 18, 2026");
});


test.each([ ["en", "0.30", "3.20", "3.75\u20134.00%", "4.2"], ["pl", "0,30", "3,20", "3,75\u20134,00%", "4,2"] ] as const)("fixed rate precision in %s is shared by the report and UI", (language, mom, yoy, fed, unemployment) => {
  setLanguage(language);
  const data = fixture(), model = briefModel(data), cpi = model.domains[1].compact[0];
  expect(cpi.current.value).toBe(mom); expect(cpi.current.yoy).toBe(yoy);
  expect(model.fedTarget.range).toBe(fed); expect(model.domains[0].compact[1].current.value).toBe(unemployment);
  expect(briefMarkdown(model, data, data.assembled_at)).toContain(mom);
  expect(readingNumber(198000, "persons")).toMatch(language === "en" ? /198,000/ : /198\s000/);
});

test.each([.00001, -.00001, .0049, -.0049, 0])("rate delta %s has no directional arrow at two-decimal precision", delta => {
  const item = fixture().reading_comparisons!.data!.find(row => row.component === "industrial_production")!;
  item.current!.value = item.previous!.value + delta; item.change = delta;
  const reading = prepareReading(item.component, item.series_id, item);
  expect(reading.arrow).toBe("\u2014"); expect(reading.compactChange).toBe("\u2014"); expect(reading.tone).toBe("neutral");
  expect(readingReportLine(reading)).toContain(reading.change);
});

test("a visible rate change keeps a keyboard-accessible exact tooltip using the existing component", async () => {
  const data = fixture(), item = data.reading_comparisons!.data!.find(row => row.component === "headline_cpi")!;
  item.current!.value = item.previous!.value + .0051; item.change = .0051; mockApi(data); render(<EconomyBrief />);
  const region = await screen.findByRole("row", { name: "CPI MoM" });
  const button = within(region).getByRole("button", { name: "CPI MoM: Change vs previous month - Higher reading" });
  expect(button).toHaveTextContent("\u2191"); expect(button).not.toHaveTextContent("0.0051");
  button.focus(); expect(button).toHaveFocus();
  const tooltip = document.getElementById(button.getAttribute("aria-describedby")!);
  expect(tooltip).toHaveAttribute("role", "tooltip"); expect(tooltip).toHaveTextContent("+0.01 percentage points");
  fireEvent.click(button); expect(button).toHaveAttribute("aria-expanded", "true");
  fireEvent.keyDown(button, { key: "Escape" }); expect(button).toHaveAttribute("aria-expanded", "false");
  expect(briefMarkdown(briefModel(data), data, data.assembled_at)).toContain("+0.0051 percentage points");
});

test("compact calendar omits coverage and unknown times; five Polish publications have correct wording and no empty list", async () => {
  const data = fixture(), original = data.calendar.data!.events[0];
  data.calendar.data!.events = [19,20,21,22,23].map(day => ({ ...original, release_id: 15, release_name: "H.15 Selected Interest Rates", importance: "low" as const, release_datetime_utc: null, release_time: null, source_timezone: null, release_date: `2026-10-${day}` }));
  setLanguage("pl"); mockApi(data); render(<EconomyBrief />);
  await screen.findByRole("heading", {name: "Nadchodz\u0105ce wydarzenia"});
  expect(document.querySelector(".overview-other-events")).toBeNull();
  const panel = document.querySelector('[aria-labelledby="brief-calendar"]')!;
  expect([...panel.querySelectorAll("ul")].every(list => list.children.length > 0)).toBe(true);
  expect([...panel.querySelectorAll("li")].every(item => item.textContent?.trim())).toBe(true);
  const group = briefModel(data).calendarGroups[0]; expect(group.events.every(event => !event.includes("Covers:") && !event.includes("Time unavailable"))).toBe(true);
  const report = briefMarkdown(briefModel(data), data, data.assembled_at);
  expect(report).not.toMatch(/^[-*]\s*$/m); expect(report).not.toContain("5 daty");
  for (const day of [19,20,21,22,23]) expect(report).toContain(`2026-10-${day}`);
});

test("a newer stored missing period shows a domain-specific notice also preserved in the report", async () => {
  const data = fixture(), item = data.reading_comparisons!.data!.find(row => row.component === "headline_cpi")!;
  item.latest_stored_observation_date = "2026-10-01";
  mockApi(data); render(<EconomyBrief />);
  const notice = await screen.findByRole("status");
  expect(notice).toHaveTextContent("CPI MoM: Newer stored period 2026-10-01 has no available reading.");
  expect(notice.closest("article")).toHaveAttribute("aria-label", "Inflation brief");
  expect(briefMarkdown(briefModel(data), data, data.assembled_at)).toContain(notice.textContent!);
});


test("rounded negative zero is never displayed as a negative rate", () => {
  expect(readingNumber(-.00001, "percent")).toBe("0.00");
  setLanguage("pl"); expect(readingNumber(-.00001, "percent")).toBe("0,00");
});


test.each([
  ["en", "payrolls", 29, "29 k"], ["pl", "payrolls", 29, "29 tys."],
  ["en", "initial_claims", 198500, "198,500 claims"], ["pl", "initial_claims", 198500, "198\u00a0500 wniosk\u00f3w"],
  ["en", "housing_starts", 1275, "1,275 k"], ["pl", "building_permits", 1403, "1\u00a0403 tys."],
  ["en", "headline_cpi", .65, "0.65%"], ["pl", "headline_cpi", .65, "0,65%"],
  ["en", "unemployment", 4.2, "4.2%"], ["pl", "unemployment", 4.2, "4,2%"],
  ["en", "yield_curve_2s10s", .33, "0.33 pp"], ["pl", "yield_curve_2s10s", .33, "0,33 pp"],
  ["en", "nfci", -.5, "-0.50"], ["pl", "manufacturing_pmi", -.5, "-0,50"],
] as const)("%s %s includes the compact unit at every displayed value", (language, component, value, expected) => {
  setLanguage(language);
  const item = fixture().reading_comparisons!.data!.find(row => row.component === component)!;
  for (const point of [item.current!, item.previous!, item.three_periods_ago!]) point.value = value;
  const reading = prepareReading(component, item.series_id, item);
  for (const point of [reading.current, reading.previous, reading.earlier]) expect(point.display).toBe(expected);
});

test.each(["payrolls", "initial_claims", "housing_starts", "mortgage_rate", "yield_curve_2s10s"])("%s compact difference uses magnitude without a repeated direction sign", component => {
  const item = fixture().reading_comparisons!.data!.find(row => row.component === component)!;
  for (const delta of [-104,104]) {
    item.current!.value = item.previous!.value + delta; item.change = delta;
    const reading = prepareReading(component, item.series_id, item);
    expect(reading.compactChange).toMatch(delta < 0 ? /^\u2193 / : /^\u2191 /);
    expect(reading.compactChange).not.toMatch(/[+-]/);
    expect(reading.change).toMatch(delta < 0 ? /^-104 / : /^\+104 /);
    expect(reading.tooltip).toContain(reading.change);
  }
});

test("lower positive retail MoM describes slower growth rather than a fall in sales", () => {
  const item = fixture().reading_comparisons!.data!.find(row => row.component === "retail_sales")!;
  item.current!.value = .77; item.previous!.value = 1.13; item.change = .77-1.13;
  const reading = prepareReading(item.component, item.series_id, item);
  expect(reading.current.display).toBe("0.77%"); expect(reading.arrow).toBe("\u2193");
  expect(reading.tooltip).toContain("Rate lower than in the previous month.");
  expect(reading.tooltip).toContain("Previous rate: 1.13%"); expect(reading.tooltip).toContain("Current rate: 0.77%");
  expect(reading.tooltip).toContain("Difference: -0.36 percentage points."); expect(reading.tone).toBe("negative");
  setLanguage("pl"); const pl = briefMarkdown(briefModel({ ...fixture(), reading_comparisons: { status: "ready", data: [item], error: null } }), fixture(), "2026-10-19T12:00:00Z");
  expect(pl).toContain("-0,36 pkt proc.");
});

test("GDP uses a quarterly rate comparison and claims uses a weekly value comparison", () => {
  const data = fixture();
  const gdp = data.reading_comparisons!.data!.find(row => row.component === "real_gdp")!;
  gdp.current!.value = 2.22; gdp.previous!.value = 2.49; gdp.change = 2.22-2.49;
  const quarterly = prepareReading(gdp.component,gdp.series_id,gdp);
  expect(quarterly.tooltip).toContain("Rate lower than in the previous quarter.");
  expect(quarterly.tooltip).not.toContain("previous month"); expect(quarterly.change).toBe("-0.27 percentage points");
  const claims = data.reading_comparisons!.data!.find(row => row.component === "initial_claims")!;
  claims.current!.value = 198500; claims.previous!.value = 198250; claims.change = 250;
  const level = prepareReading(claims.component,claims.series_id,claims);
  expect(level.compactChange).toBe("\u2191 250 claims"); expect(level.tooltip).toContain("Value higher than in the previous week.");
  expect(level.tooltip).not.toContain("rate:"); expect(level.tooltip).toContain("Current value: 198,500 claims");
});

test("missing values have no appended units or comparison arrows, while index and rate zero stay numeric", () => {
  for (const item of fixture().reading_comparisons!.data!) {
    item.current = item.previous = item.three_periods_ago = null; item.change = null;
    const reading = prepareReading(item.component,item.series_id,item);
    for (const point of [reading.current,reading.previous,reading.earlier]) expect(point.display).toBe("\u2014");
    expect(reading.hasChange).toBe(false); expect(reading.compactChange).toBe("\u2014");
  }
  expect(readingNumber(0,"index")).toBe("0.00"); expect(readingNumber(-.00001,"index")).toBe("0.00");
});

test("screen values retain their intended compact units and full keyboard tooltip units", async () => {
  const data = fixture(); mockApi(data); render(<EconomyBrief />); await screen.findByRole("heading",{name:"Labor"});
  const model = briefModel(data);
  for (const reading of model.domains.flatMap(domain=>domain.compact)) {
    const region = screen.getByRole("row",{name:reading.label});
    for (const [i,point] of [reading.current,reading.previous].entries()) expect(region.querySelectorAll("strong")[i]).toHaveTextContent(reading.key === "initial_claims" ? point.screenValue : point.display);
    const button = within(region).getByRole("button",{name:/Change vs|Zmiana wobec/});
    button.focus(); expect(button).toHaveFocus();
    for (const line of readingHoverLines(reading)) expect(document.getElementById(button.getAttribute("aria-describedby")!)).toHaveTextContent(line);
  }
  const housing = model.domains[4].compact[0];
  expect(readingReportLine(housing)).toContain("thousand homes/year (annualized)");
  expect(readingReportLine(housing)).not.toContain(" k");
});

test("FOMC and seven-day releases share one event block with calendar access and no provenance disclosure", async () => {
  mockApi(); render(<EconomyBrief />); const region = await screen.findByRole("region",{name:"Upcoming events"});
  expect(region.querySelector(".overview-other-events")).toBeNull();
  expect(within(region).getByRole("heading",{name:"Upcoming releases - next 7 days"})).toBeInTheDocument();
  expect(within(region).queryByText(/2026-10-18.*2026-10-24/)).not.toBeInTheDocument();
  expect(within(region).getByRole("link",{name:"View full calendar"})).toHaveAttribute("href","#/calendar");
  expect(within(region).queryByText("Event sources and schedule details")).not.toBeInTheDocument();
  const data = fixture(), report = briefMarkdown(briefModel(data), data, data.assembled_at);
  expect(report).toContain("2026-10-18 through 2026-10-24");
  expect(report).toContain("### Full release details");
  expect(report).toContain("### FOMC schedule provenance");
});

test("an elapsed scheduled release is removed locally without fetching or declaring fresh readings", async () => {
  vi.useRealTimers();
  vi.useFakeTimers({ toFake: ["Date", "setInterval", "clearInterval", "setTimeout", "clearTimeout"] });
  vi.setSystemTime(new Date("2026-10-18T10:00:00Z"));
  const data = fixture(); data.calendar.data!.events[0].release_date = "2026-10-18"; data.calendar.data!.events[0].release_datetime_utc = "2026-10-18T10:00:10Z";
  const fetch = mockApi(data);
  await act(async () => { render(<EconomyBrief />); });
  expect(document.querySelector(".overview-calendar .overview-event")).toHaveTextContent("Gross Domestic Product");
  act(() => { vi.advanceTimersByTime(30_000); });
  expect(document.querySelector(".overview-calendar .overview-event")).toBeNull();
  expect(screen.getByText("No key upcoming events in the stored 7-day window.")).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(data.reading_comparisons!.data![0].current!.observation_date).toBe("2026-09-01");
});

test("all hidden histories, additional readings, sources and exact differences remain in downloaded Markdown", async () => {
  const data = fixture(), fetch = mockApi(data); render(<EconomyBrief />); await screen.findByRole("heading", { name: "Labor" });
  expect(document.querySelectorAll(".overview-comparison-details[open]")).toHaveLength(0);
  const report = briefMarkdown(briefModel(data), data, data.assembled_at);
  for (const domain of briefModel(data).domains) {
    for (const reading of domain.compact) { expect(report).toContain(readingReportLine(reading)); expect(report).toContain(reading.change); for (const source of reading.sources) expect(report).toContain(source.url); }
    for (const reading of domain.readings) expect(report).toContain(reading);
  }
  expect(fetch).toHaveBeenCalledTimes(1);
});

test("housing uses compact units while annualization remains explicit in details and report", async () => {
  mockApi(); render(<EconomyBrief />);
  for (const label of ["Housing starts", "Building permits"]) {
    const row = await screen.findByRole("row", {name: label});
        for (const cell of row.querySelectorAll("td")) { expect(cell.querySelector("strong")).toHaveTextContent(" k"); expect(cell.querySelector("strong")).not.toHaveTextContent("SAAR"); }
    const card = row.closest("article")!;
    expect(card.querySelector(".overview-comparison-details")).toBeNull();
    expect(briefMarkdown(briefModel(fixture()), fixture(), fixture().assembled_at)).toContain("thousand homes/year (annualized)");
  }
});

test("index readings keep number and arrow compact while full units remain in details and Markdown", async () => {
  const data = fixture(); mockApi(data); render(<EconomyBrief />);
  for (const name of ["ISM Manufacturing PMI", "NFCI"]) {
    const row = await screen.findByRole("row", {name});
    expect(row).toHaveClass("overview-reading-row--index");
    expect(row.querySelector("strong")).not.toHaveTextContent("index points");
    expect(row.closest("article")!.querySelector(".overview-comparison-details")).toBeNull();
  }
  expect(briefMarkdown(briefModel(data), data, data.assembled_at)).toContain("index points");
});

test("compact event rows expose stars and retain provenance in the report rather than an Overview disclosure", async () => {
  mockApi(); render(<App />); const panel = await screen.findByRole("region", {name: "Upcoming events"});
  const row = panel.querySelector(".overview-event")!;
  expect(within(row as HTMLElement).getByRole("img", {name: "Importance 3 of 3"})).toHaveTextContent("\u2605\u2605\u2605");
  expect(row.querySelector("time")).toHaveTextContent("Oct 20");
  expect(row.querySelector("a")).toBeNull();
  expect(panel.querySelector(".overview-other-events")).toBeNull();
  expect(panel.querySelector("details")).toBeNull();
  const data = fixture(), report = briefMarkdown(briefModel(data), data, data.assembled_at);
  expect(report).toContain("Editorial tiers take precedence without changing source classes.");
  expect(report).toContain("https://www.cmegroup.com/fedwatch");
  expect(panel.lastElementChild).toHaveAttribute("href", "#/calendar");
  fireEvent.click(screen.getByRole("button", {name: "Polski"}));
  expect(screen.getByRole("img", {name: "Wa\u017cno\u015b\u0107 3 z 3"})).toBeInTheDocument();
});

test("five labor rows keep raw claims compact and preserve the average only in the report", async () => {
  const data = fixture(), fetch = mockApi(data); render(<App />);
  const labor = await screen.findByRole("article", {name: "Labor brief"});
  expect(labor.querySelectorAll("tbody tr")).toHaveLength(5);
  expect(labor.querySelector("details")).toBeNull(); expect(screen.queryByText("More comparisons")).not.toBeInTheDocument();
  const claims = within(labor).getByRole("row", {name: "Initial jobless claims"});
  expect(claims.querySelector("strong")).toHaveTextContent("199,000");
  expect(claims.querySelector("strong")).not.toHaveTextContent("claims");
  expect(within(claims).queryByText(/4W avg/)).not.toBeInTheDocument();
  expect(claims.querySelector(".overview-change")).toHaveClass("overview-change--positive");
  const openings = within(labor).getByRole("row", {name: "JOLTS job openings"});
  expect(openings.querySelector("strong")).toHaveTextContent("7.25 m");
  const wage = within(labor).getByRole("row", {name: "Hourly earnings MoM"});
  expect(wage.querySelector("strong")).toHaveTextContent("0.30%"); expect(wage.querySelector(".overview-yoy")).toHaveTextContent("3.20% YoY");
  for (const row of [openings, wage]) { expect(row.querySelector(".overview-change")).toHaveClass("overview-change--positive"); const button = within(row).getByRole("button", {name: /Change vs|Zmiana wobec/}); button.focus(); expect(button).toHaveFocus(); }
  const report = briefMarkdown(briefModel(data), data, data.assembled_at);
  expect(report).toContain("JOLTS job openings [thousand openings]: Latest: 7,250");
  expect(report).toContain("Same-week 4W average: 198,500 claims");
  expect(report).toContain("CES0500000003, mom"); expect(report).toContain("ICSA, raw");
  fireEvent.click(screen.getByRole("button", {name: "Polski"}));
  expect(screen.getByRole("row", {name: "Wolne miejsca pracy \u2014 JOLTS"}).querySelector("strong")).toHaveTextContent("7,25 mln");
  expect(fetch).toHaveBeenCalledTimes(1);
});

test("claims average from another week is omitted and never replaces missing raw data", async () => {
  const data = fixture(), claims = data.reading_comparisons!.data!.find(r => r.component === "initial_claims")!;
  claims.context_moving_average_4w!.observation_date = "2026-09-26";
  claims.previous = null; claims.change = null; mockApi(data); render(<EconomyBrief />);
  const row = await screen.findByRole("row", {name: "Initial jobless claims"});
  expect(row.querySelector(".overview-claims-context")).toBeNull();
  expect(row.querySelectorAll("td")[1]).toHaveTextContent("\u2014"); expect(row.querySelectorAll("td")[1]).toHaveTextContent("Sep 26, 2026");
});

test.each(["job_openings", "average_hourly_earnings"])("%s uses numerical direction separately from economic interpretation and reports exact periods and units", component => {
  const item = fixture().reading_comparisons!.data!.find(r => r.component === component)!;
  for (const delta of [-20, 20]) {
    item.current!.value = item.previous!.value + delta; item.change = delta; const prepared = prepareReading(component, item.series_id, item);
    expect(prepared.tone).toBe(delta > 0 ? "positive" : "negative"); expect(prepared.arrow).toBe(delta > 0 ? "\u2191" : "\u2193");
    expect(prepared.tooltip).toContain("Sep 2026"); expect(prepared.tooltip).toContain("Aug 2026");
    expect(prepared.tooltip).toContain(component === "average_hourly_earnings" ? "Rate" : "Value");
    expect(prepared.change).toContain(component === "average_hourly_earnings" ? "percentage points" : "thousand openings");
  }
});

test("PPI is a fourth inflation row with numerical direction, exact pp difference and no YoY", async () => {
  const data = fixture(), ppi = data.reading_comparisons!.data!.find(r => r.series_id === "PPIFIS")!;
  ppi.current!.value = .5; ppi.previous!.value = .2; ppi.change = .3;
  mockApi(data); render(<App />);
  const row = await screen.findByRole("row", {name:"Producer inflation PPI MoM"});
  expect(row.closest("tbody")!.children).toHaveLength(4);
  expect(row.querySelector("strong")).toHaveTextContent("0.50%");
  expect(row.querySelectorAll("td")[1]).toHaveTextContent("0.20%");
  expect(row.querySelector(".overview-yoy")).toBeNull();
  expect(row.querySelector(".overview-change")).toHaveClass("overview-change--positive");
  expect(within(row).getByRole("link")).toHaveAttribute("href", "#/explore/indicators/PPIFIS");
  const button = within(row).getByRole("button", {name: /Change vs|Zmiana wobec/}); button.focus(); expect(button).toHaveFocus();
  expect(document.getElementById(button.getAttribute("aria-describedby")!)).toHaveTextContent("Difference: +0.30 percentage points");
  const report = briefMarkdown(briefModel(data), data, data.assembled_at);
  expect(report).toContain("Producer inflation PPI MoM [%]: Latest: 0.50");
  expect(report).toContain("PPIFIS, mom"); expect(report).toContain("https://fred.stlouisfed.org/series/PPIFIS");
  expect(readingReportLine(prepareReading("producer_ppi", "PPIFIS", ppi))).not.toContain("YoY");
  fireEvent.click(screen.getByRole("button",{name:"Polski"}));
  expect(screen.getByRole("row",{name:"Inflacja producencka PPI m/m"})).toBeInTheDocument();
});

test("unclassified PPI does not change the completeness of existing inflation assessments", () => {
  const data = fixture();
  data.state = {status: "ready", error: null, data: {
    as_of_date: "2026-10-01", component_as_of_dates: data.snapshot.data!.component_as_of_dates,
    domains: Object.fromEntries(domainSelection.map(domain => [domain.key, {
      name: domain.name, as_of_date: "2026-10-01", classifications: {},
      readings: domain.readings.filter(([key]) => key !== "producer_ppi").map(([key]) => ({
        key, value: 2, label: key, unit: "percent", observation_date: "2026-09-01", feature_as_of_date: "2026-10-01"
      })), evidence: ["Existing domain assessment."]
    }])) as NonNullable<EconomyBriefResponse["state"]["data"]>["domains"], cross_currents: []
  }};
  const inflation = briefModel(data).domains.find(d => d.key === "inflation")!;
  expect(inflation.missing).toBe(false);
  expect(inflation.compact.some(r => r.raw?.series_id === "PPIFIS")).toBe(true);
  expect(inflation.readings.some(r => r.includes("PPIFIS"))).toBe(false);
});


test("local PMI rows preserve index units, numerical directions and document provenance in Markdown", async () => {
  const data = fixture();
  for (const component of ["manufacturing_pmi", "services_pmi"]) {
    const row = data.reading_comparisons!.data!.find(r => r.component === component)!;
    row.feature_name = "raw"; row.current!.value = 37; row.previous!.value = 35; row.change = 2;
    row.source_url = "https://www.prnewswire.com/news-releases/synthetic-test.html";
    Object.assign(row.current!, {document_published_at:"2026-10-03T10:00:00-04:00",retrieved_at:"2026-10-20T10:00:00Z",raw_hash:"synthetic-hash"});
  }
  mockApi(data); render(<App />);
  for (const label of ["ISM Manufacturing PMI", "ISM Services PMI"]) {
    const row = await screen.findByRole("row",{name:label});
    expect(row.querySelector("strong")).toHaveTextContent("37.00");
    expect(row.querySelector("strong")).not.toHaveTextContent("%");
    expect(row.querySelector(".overview-change")).toHaveClass("overview-change--positive");
  }
  expect(screen.queryByRole("row",{name:"CFNAI, 3M average"})).not.toBeInTheDocument();
  const report = briefMarkdown(briefModel(data),data,data.assembled_at);
  expect(report).toContain("Manufacturing PMI [index points]");
  expect(report).toContain("+2 index points");
  expect(report).toContain("RAW SHA-256 synthetic-hash");
  expect(report).toContain("document published 2026-10-03");
  expect(report).toContain("https://www.prnewswire.com/news-releases/synthetic-test.html");
  expect(report).not.toContain("fred.stlouisfed.org/series/ISM_");
  fireEvent.click(screen.getByRole("button",{name:"Polski"}));
  expect(screen.getByRole("row",{name:"ISM PMI przemys\u0142u"})).toBeInTheDocument();
});


test.each(["en", "pl"] as const)("compact claims and spread retain full keyboard tooltip and report units in %s", async language => {
  setLanguage(language);
  const data=fixture();mockApi(data);render(<EconomyBrief />);
  const claims=await screen.findByRole("row",{name:language === "pl" ? "Nowe wnioski o zasi\u0142ek" : "Initial jobless claims"});
  expect(claims.querySelectorAll("strong")[0]).toHaveTextContent(language === "pl" ? "199 000" : "199,000");
  expect(claims.querySelectorAll("strong")[1]).toHaveTextContent(language === "pl" ? "198 000" : "198,000");
  expect(claims.textContent).not.toMatch(/4W|198[ ,\u00a0]500/);
  const tooltip=within(claims).getByRole("button", {name: /Change vs|Zmiana wobec/});tooltip.focus();expect(tooltip).toHaveFocus();
  expect(document.getElementById(tooltip.getAttribute("aria-describedby")!)!.textContent).toContain(language === "pl" ? "wniosk" : "claims");
  expect(within(claims).getByRole("link")).toHaveAttribute("href","#/explore/indicators/ICSA");
  const spread=document.querySelector('a[href="#/explore/indicators/DGS2"]')!.closest("tr")!;
  expect(spread.querySelector("strong")).toHaveTextContent("pp");
  const report=briefMarkdown(briefModel(data),data,data.assembled_at);
  expect(report).toContain(language === "pl" ? "\u015arednia 4W" : "Same-week 4W average");
  expect(report).toContain(language === "pl" ? "pkt proc." : "percentage points");
});


test("optional economic notes toggle below language controls without refetching and remember preference",async()=>{
 const fetch=mockApi();const {unmount}=render(<App />);await screen.findByRole("heading",{name:"Labor"});
 const toggle=screen.getByRole("button",{name:"Overview explanations"});
 expect(toggle).toHaveAttribute("aria-pressed","false");expect(screen.queryByRole("button",{name:/Economic meaning/})).not.toBeInTheDocument();
 fireEvent.click(toggle);expect(await screen.findAllByRole("button",{name:/Economic meaning/})).toHaveLength(22);
 expect(localStorage.getItem("macrolens.overview.explanations")).toBe("true");expect(fetch).toHaveBeenCalledTimes(1);
 const note=screen.getByRole("button",{name:"CPI MoM: Economic meaning"});
 const heading=note.closest("th")!;
 expect(within(heading).getAllByRole("button").map(button=>button.getAttribute("aria-label"))).toEqual(["View chart: CPI MoM","CPI MoM: Economic meaning"]);
 note.focus();expect(note).toHaveFocus();
 const body=document.getElementById(note.getAttribute("aria-describedby")!)!;
 expect(within(body).getAllByRole("listitem")).toHaveLength(3);
 for(const title of ["Economy:","Fed:","Markets:"])expect(body).toHaveTextContent(title);
 fireEvent.keyDown(note,{key:"Escape"});expect(note).toHaveFocus();expect(note).toHaveAttribute("aria-expanded","false");
 fireEvent.click(screen.getByRole("button",{name:"Polski"}));
 expect(screen.getByRole("button",{name:/Inflacja CPI m\/m: Znaczenie odczytu/})).toBeInTheDocument();
 unmount();render(<App />);await screen.findByRole("heading",{name:"Rynek pracy"});
 const saved=screen.getByRole("button",{name:"Obja\u015bnienia Overview"});expect(saved).toHaveAttribute("aria-pressed","true");fireEvent.click(saved);
 expect(screen.queryByRole("button",{name:/Znaczenie odczytu/})).not.toBeInTheDocument();
 localStorage.removeItem("macrolens.overview.explanations");
});

test.each(["en", "pl"] as const)("numeric arrows and domain markers remain independent of Explain in %s", async language => {
 setLanguage(language);
 const data=fixture(), items=data.reading_comparisons!.data!;
 const unemployment=items.find(r=>r.component==="unemployment")!;
 unemployment.current!.value=4;unemployment.previous!.value=4.1;unemployment.change=-.1;
 const jobs=items.find(r=>r.component==="payrolls")!;jobs.current!.value=29;jobs.previous!.value=133;jobs.change=-104;
 const claims=items.find(r=>r.component==="initial_claims")!;claims.previous=null;claims.change=null;
 const wage=items.find(r=>r.component==="average_hourly_earnings")!;wage.current!.value=wage.previous!.value;wage.change=0;
 mockApi(data);render(<EconomyBrief />);
 const row=await screen.findByRole("row",{name:language==="pl"?"Stopa bezrobocia":"Unemployment rate"});
 expect(row.querySelector(".overview-change")).toHaveClass("overview-change--negative");
 expect(row.querySelector(".overview-change")).toHaveTextContent("\u2193");
 const badge=row.querySelector(".overview-interpretation")!;
 expect(badge).toHaveClass("overview-interpretation--favorable");expect(badge).toHaveTextContent("+");
 const button=within(badge as HTMLElement).getByRole("button");button.focus();expect(button).toHaveFocus();
 const tip=document.getElementById(button.getAttribute("aria-describedby")!)!;
 expect(tip).toHaveTextContent(language==="pl"?"ni\u017csza stopa bezrobocia":"lower unemployment");
 fireEvent.keyDown(button,{key:"Escape"});expect(button).toHaveAttribute("aria-expanded","false");
 expect(document.querySelectorAll(".overview-explanation")).toHaveLength(0);
 expect(document.querySelectorAll(".overview-symbol-legend")).toHaveLength(1);
 const nfp=screen.getByRole("row",{name:language==="pl"?"Zatrudnienie poza rolnictwem \u2014 NFP":"Nonfarm payrolls (NFP)"});
 expect(nfp.querySelector(".overview-interpretation")).toHaveClass("overview-interpretation--mixed");
 const missing=screen.getByRole("row",{name:language==="pl"?"Nowe wnioski o zasi\u0142ek":"Initial jobless claims"});
 expect(missing.querySelector(".overview-change")).toHaveTextContent("?");expect(missing.querySelector(".overview-interpretation")).toBeNull();
 const unchanged=screen.getByRole("row",{name:language==="pl"?"Wynagrodzenie godzinowe m/m":"Hourly earnings MoM"});
 expect(unchanged.querySelector(".overview-change")).toHaveTextContent("\u2014");expect(unchanged.querySelector(".overview-interpretation")).toBeNull();
 const report=briefMarkdown(briefModel(data),data,data.assembled_at);
 expect(report).not.toContain("Usually favorable");expect(report).not.toContain("Zwykle korzystne");
 expect(report).not.toContain("Arrows: direction");expect(report).not.toContain("Strza\u0142ki: kierunek");
});

test.each(["en", "pl"] as const)("header legend explains symbols beside report controls and sources replace the old notes in %s", async language => {
 setLanguage(language);const data=fixture();mockApi(data);render(<EconomyBrief />);
 await screen.findByRole("heading",{name:language==="pl"?"Rynek pracy":"Labor"});
 const legend=screen.getByRole("complementary",{name:language==="pl"?"Legenda zmian":"Change legend"});
 expect(within(legend).getAllByRole("listitem")).toHaveLength(6);
 expect(within(legend).queryByText("?")).not.toBeInTheDocument();
 expect(within(legend).queryByText(language==="pl"?"Brak por\u00f3wnania":"No comparison")).not.toBeInTheDocument();
 for(const symbol of ["\u2191","\u2193","\u2014","+","\u2212","\u00b1"])expect(within(legend).getByText(symbol)).toBeInTheDocument();
 expect(within(legend).getByRole("group",{name:language==="pl"?"Zmiana odczytu":"Reading change"})).toHaveTextContent(language==="pl"?"Wy\u017cszy ni\u017c poprzednio":"Higher than previous");
 expect(within(legend).getByRole("group",{name:language==="pl"?"Dla obszaru gospodarki":"For the economic area"})).toHaveTextContent(language==="pl"?"Zwykle korzystne":"Usually favorable");
 const download=screen.getByRole("button",{name:language==="pl"?"Pobierz raport":"Download report"});
 expect(legend.closest("header")).toBe(download.closest("header"));
 expect(legend.compareDocumentPosition(download)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
 expect(screen.getByRole("link",{name:"FRED"})).toHaveAttribute("href","https://fred.stlouisfed.org/");
 expect(screen.getByRole("link",{name:"ISM"})).toHaveAttribute("href","https://www.ismworld.org/");
 expect(screen.queryByText(/Current-vintage readings; earlier|Bie\u017c\u0105ca wersja danych; wcze\u015bniejsze/)).not.toBeInTheDocument();
 expect(screen.queryByText(/Arrows: direction of the reading change|Strza\u0142ki: kierunek zmiany odczytu/)).not.toBeInTheDocument();
 expect(briefMarkdown(briefModel(data),data,data.assembled_at)).toContain(language==="pl"?"Bie\u017c\u0105ca wersja danych":"Current-vintage readings");
});

test.each(["en", "pl"] as const)("source-check line is hidden without actual check metadata in %s", async language => {
 setLanguage(language);const data=fixture();mockApi(data);render(<EconomyBrief />);
 await screen.findByRole("heading",{name:language==="pl"?"Rynek pracy":"Labor"});
 expect(document.querySelector(".overview-source-check")).toBeNull();
 expect(screen.queryByText(/no recorded timestamp/)).not.toBeInTheDocument();
});

test("Overview reading arrows expose a dismissible comparison popup", async () => {
 mockApi();render(<EconomyBrief />);
 const row=await screen.findByRole("row",{name:"Unemployment rate"});
 const change=row.querySelector(".overview-change") as HTMLElement;
 const arrow=within(change).getByRole("button");
 fireEvent.click(arrow);
 fireEvent.click(within(change).getByRole("button",{name:"Close explanation"}));
 expect(arrow).toHaveAttribute("aria-expanded","false");
 expect(arrow).toHaveFocus();
});

test.each(["en", "pl"] as const)("Overview keeps only one activated reading popup in %s", async language => {
 setLanguage(language);mockApi();render(<EconomyBrief explanations />);
 const row=await screen.findByRole("row",{name:language==="pl"?"Stopa bezrobocia":"Unemployment rate"});
 const arrow=within(row.querySelector(".overview-change") as HTMLElement).getByRole("button");
 const marker=within(row.querySelector(".overview-interpretation") as HTMLElement).getByRole("button");
 const note=within(row.querySelector(".overview-explanation") as HTMLElement).getByRole("button");
 for(const button of [arrow,marker,note]) {
  fireEvent.pointerEnter(button,{pointerType:"mouse"});fireEvent.focus(button);
  expect(button).toHaveAttribute("aria-expanded","false");
 }
 for(const button of [arrow,marker,note,arrow]) {
  fireEvent.click(button);
  expect(button).toHaveAttribute("aria-expanded","true");
  expect(document.querySelectorAll(".info-tooltip--open")).toHaveLength(1);
 }
 fireEvent.click(within(row.querySelector(".overview-change") as HTMLElement).getByRole("button",{name:language==="pl"?"Zamknij obja\u015bnienie":"Close explanation"}));
 expect(document.querySelectorAll(".info-tooltip--open")).toHaveLength(0);
});

test.each(["en", "pl"] as const)("reading popup separates name, periods and rounded difference in %s", async language => {
 setLanguage(language);const data=fixture();
 const jobs=data.reading_comparisons!.data!.find(item=>item.component==="payrolls")!;
 jobs.current!.value=29;jobs.previous!.value=133;jobs.change=-104;
 mockApi(data);render(<EconomyBrief />);
 const row=await screen.findByRole("row",{name:language==="pl"?"Zatrudnienie poza rolnictwem \u2014 NFP":"Nonfarm payrolls (NFP)"});
 const arrow=within(row.querySelector(".overview-change") as HTMLElement).getByRole("button");
 fireEvent.click(arrow);
 const tooltip=document.getElementById(arrow.getAttribute("aria-describedby")!)!;
 const lines=tooltip.querySelector(".reading-change-details")!.children;
 expect(lines).toHaveLength(3);
 expect(lines[0]).toHaveTextContent(language==="pl"?"Zatrudnienie poza rolnictwem \u2014 NFP":"Nonfarm payrolls (NFP)");
 expect(lines[1]).toHaveTextContent(language==="pl"?"Warto\u015b\u0107 ni\u017csza ni\u017c w poprzednim miesi\u0105cu":"Value lower than in the previous month");
 expect(lines[1]).toHaveTextContent(language==="pl"?"wrz 2026 wobec sie 2026":"Sep 2026 vs Aug 2026");
 expect(lines[2]).toHaveTextContent(language==="pl"?"R\u00f3\u017cnica: -104 tys. miejsc pracy.":"Difference: -104 thousand jobs.");
 expect(within(tooltip).getByRole("button",{name:language==="pl"?"Zamknij obja\u015bnienie":"Close explanation"})).toBeInTheDocument();
});

test("missing comparison popup keeps the indicator name without inventing a difference", async () => {
 const data=fixture();const jobs=data.reading_comparisons!.data!.find(item=>item.component==="payrolls")!;
 jobs.previous=null;jobs.change=null;
 mockApi(data);render(<EconomyBrief />);
 const row=await screen.findByRole("row",{name:"Nonfarm payrolls (NFP)"});
 const arrow=within(row.querySelector(".overview-change") as HTMLElement).getByRole("button");fireEvent.click(arrow);
 const tooltip=document.getElementById(arrow.getAttribute("aria-describedby")!)!;
 expect(tooltip.querySelector(".reading-change-details")!.children).toHaveLength(2);
 expect(tooltip).toHaveTextContent("Comparison unavailable.");expect(tooltip).not.toHaveTextContent("Difference:");
});


test("audit export uses the same data and existing interpretation functions as Overview",()=>{
 const data=fixture(),model=briefModel(data),report=explanationAuditMarkdown(data,data.assembled_at);
 for(const domain of model.domains)for(const reading of domain.compact){
  expect(report).toContain(reading.raw!.series_id);
  const note=economicExplanation(reading),interpretation=economicInterpretation(reading);
  for(const text of [note.observation,note.economy,note.fed,note.markets])expect(report).toContain(text);
  if(interpretation)expect(report).toContain(interpretation.reason);
 }
 expect(report).toContain("DFEDTARL / DFEDTARU");
 expect(report).toContain("stored value 199000 claims");
});

test("report during a background check uses its saved dataset and records the running check",()=>{
 const data=fixture();data.data_revision="saved-revision";
 data.refresh={status:"running",job_id:"running-job",attempted_at:"2026-10-26T10:00:00Z",results:[]};
 const report=briefMarkdown(briefModel(data),data,data.assembled_at);
 expect(report).toContain("Checking availability of new data");
 expect(report).toContain("Published data revision: saved-revision");
 expect(report).toContain("2026-10-26T10:00:00Z");
 expect(report).toContain("Latest: 199,000 (Oct 3, 2026)");
});

test.each(['en','pl'] as const)('Overview includes Michigan month and restricted publisher link without a seventh card in %s',async language=>{
 setLanguage(language);const data=fixture();
 data.calendar.data!.events=[{release_id:null,event_id:'michigan:2026-10:final',event_type:'michigan_final',release_name:'Michigan Consumer Sentiment — Final',release_date:'2026-10-23',release_time:null,release_datetime_utc:null,source_timezone:'America/New_York',source_link:'https://data.sca.isr.umich.edu/survey-info.php',importance:'medium',date_precision:'date',series:[],measures:[],reference_period:'2026-10-01',publication_stage:'final',expects_numeric_result:true,result_integration_status:'publisher_permission_required',publisher_reports_url:'https://data.sca.isr.umich.edu/reports.php?year=2026'}];
 mockApi(data);render(<EconomyBrief/>);
 const link=await screen.findByRole('link',{name:language==='en'?'Publisher reports':'Raporty wydawcy'});
 expect(link).toHaveAttribute('href',data.calendar.data!.events[0].publisher_reports_url);
 expect(link.closest('li')).toHaveTextContent(language==='en'?'Oct 2026':'paź 2026');
 expect(document.querySelectorAll('.overview-domain')).toHaveLength(6);
 const report=briefMarkdown(briefModel(data),data,data.assembled_at);
 expect(report).toContain('https://data.sca.isr.umich.edu/reports.php?year=2026');
});

test.each(['en','pl'] as const)('FT900 attribution and source links survive Overview export with six cards in %s',async language=>{
 setLanguage(language);vi.setSystemTime(new Date('2026-11-01T12:00:00Z'));const data=fixture();
 data.calendar_start_date='2026-11-01';data.calendar_end_date='2026-11-07';
 data.calendar.data!.events=[{release_id:null,event_id:'ft900:2026-09:monthly',event_type:'ft900',release_name:'U.S. Trade Balance — Goods and Services',reference_period:'2026-09-01',release_date:'2026-11-04',release_time:'08:30:00',release_datetime_utc:'2026-11-04T13:30:00Z',source_timezone:'America/New_York',source_link:'https://www.census.gov/foreign-trade/schedule.html',importance:'medium',date_precision:'date',series:[],usage_rights:{source:'U.S. Census Bureau / U.S. Bureau of Economic Analysis',copyright:'Source: U.S. Census Bureau and U.S. Bureau of Economic Analysis.',terms_url:'https://www.bea.gov/help/faq/147',original_url:'https://www.census.gov/foreign-trade/Press-Release/current_press_release/exh1.xlsx',modifications:'MacroLens converts millions to billions; current-vintage, no publisher endorsement.',redistribution_conditions:'BEA public-domain policy with exceptions.'}}];
 mockApi(data);render(<EconomyBrief/>);
 const link=await screen.findByRole('link',{name:language==='en'?'BEA data use policy':'Zasady wykorzystania danych BEA'});
 expect(link.closest('li')).toHaveTextContent('14:30');expect(link.closest('li')).toHaveTextContent('U.S. Census Bureau');
 expect(document.querySelectorAll('.overview-domain')).toHaveLength(6);
 expect(document.querySelectorAll('.overview-calendar .overview-event').length).toBeLessThanOrEqual(4);
 const report=briefMarkdown(briefModel(data),data,data.assembled_at);
 expect(report).toContain('https://www.bea.gov/help/faq/147');expect(report).toContain('no publisher endorsement');
});

test.each(['en','pl'] as const)('Empire attribution is present in Overview and exported report without a seventh card in %s',async language=>{
 setLanguage(language);vi.setSystemTime(new Date('2026-11-14T12:00:00Z'));const data=fixture();
 data.calendar_start_date='2026-11-14';data.calendar_end_date='2026-11-20';
 data.calendar.data!.events=[{release_id:null,event_id:'empire-state:2026-11:monthly',event_type:'empire_state',release_name:'Empire State Manufacturing Survey',reference_period:'2026-11-01',release_date:'2026-11-16',release_time:'08:30:00',release_datetime_utc:'2026-11-16T13:30:00Z',source_timezone:'America/New_York',source_link:'https://www.newyorkfed.org/survey/empire/empiresurvey_overview',importance:'medium',date_precision:'date',series:[],usage_rights:{source:'Federal Reserve Bank of New York',copyright:'© 2026 Federal Reserve Bank of New York.',terms_url:'https://www.newyorkfed.org/privacy/termsofuse',original_url:'https://www.newyorkfed.org/medialibrary/media/survey/empire/data/esms_seasonallyadjusted_diffusion.csv',modifications:'MacroLens index-point differences; no New York Fed endorsement.',redistribution_conditions:'https://www.newyorkfed.org/privacy/termsofuse'}}];
 mockApi(data);render(<EconomyBrief/>);
 const link=await screen.findByRole('link',{name:language==='en'?'NY Fed Terms of Use':'Warunki wykorzystania NY Fed'});
 expect(link.closest('li')).toHaveTextContent('14:30');expect(link.closest('li')).toHaveTextContent('Federal Reserve Bank of New York');
 expect(document.querySelectorAll('.overview-domain')).toHaveLength(6);
 expect(document.querySelectorAll('.overview-calendar .overview-event').length).toBeLessThanOrEqual(4);
 const report=briefMarkdown(briefModel(data),data,data.assembled_at);
 expect(report).toContain('https://www.newyorkfed.org/privacy/termsofuse');expect(report).toContain('no New York Fed endorsement');
});

test.each(['en','pl'] as const)('ADP appears in Overview as a monthly report without adding a domain in %s',async language=>{
 setLanguage(language);vi.setSystemTime(new Date('2026-11-01T12:00:00Z'));const data=fixture();
 data.calendar_start_date='2026-11-01';data.calendar_end_date='2026-11-07';
 data.calendar.data!.events=[{release_id:null,event_id:'adp:2026-10:monthly',event_type:'adp_monthly',release_name:'ADP National Employment Report',release_date:'2026-11-04',release_time:'08:15:00',release_datetime_utc:'2026-11-04T13:15:00Z',source_timezone:'America/New_York',source_link:'https://adpemploymentreport.com/',importance:'high',date_precision:'date',series:[],measures:[],reference_period:'2026-10-01',publication_stage:'monthly',expects_numeric_result:true,result_integration_status:'publisher_permission_required',publisher_reports_url:'https://mediacenter.adp.com/press-releases?l=100'}];
 mockApi(data);render(<EconomyBrief/>);
 const link=await screen.findByRole('link',{name:language==='en'?'Publisher reports':'Raporty wydawcy'});
 expect(link.closest('li')).toHaveTextContent('14:15');expect(document.querySelectorAll('.overview-domain')).toHaveLength(6);
 expect(document.querySelectorAll('.overview-calendar .overview-event').length).toBeLessThanOrEqual(4);
 const report=briefMarkdown(briefModel(data),data,data.assembled_at);
 expect(report).toContain('2026-10-01');expect(report).toContain('https://mediacenter.adp.com/press-releases?l=100');
});

test("report identifies GDP and claims window comparisons without reinterpreting consecutive readings",()=>{
 const data=fixture();
 data.classification_basis={growth:[{component:"real_gdp",field:"momentum",label:"Real GDP momentum",classification:"accelerating",short:"Quarterly annualized versus annual growth.",observation_date:"2026-04-01",feature_as_of_date:"2026-09-30",inputs:[{label:"Quarterly annualized growth",feature_name:"qoq_annualized",value:2.22,unit:"percent"},{label:"Year-over-year growth",feature_name:"yoy",value:2.19,unit:"percent"}],rule:"This compares different windows, not consecutive quarters."}],labor:[{component:"initial_claims",field:"momentum",label:"Initial claims momentum",classification:"improving",short:"Four versus thirteen weeks.",observation_date:"2026-10-17",feature_as_of_date:"2026-10-22",inputs:[{label:"Four-week average",feature_name:"moving_average_4w",value:197250,unit:"persons"},{label:"Thirteen-week average",feature_name:"moving_average_13w",value:200000,unit:"persons"}],rule:"A lower four-week average indicates improvement."}]};
 const report=briefMarkdown(briefModel(data),data,data.assembled_at);
 expect(report).toContain("Quarterly pace relative to annual growth");expect(report).toContain("2.220000 percent [qoq_annualized]");expect(report).toContain("2.190000 percent [yoy]");
 expect(report).toContain("Initial claims: 4-week average relative to 13-week average");expect(report).toContain("197,250.000000 persons [moving_average_4w]");
});
