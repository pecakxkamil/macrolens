import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import App from "../App";
import { EconomyBrief } from "./EconomyBrief";
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
    const feature_name = component === "payrolls" ? "monthly_change" : component === "initial_claims" ? "moving_average_4w" : component === "real_gdp" ? "qoq_annualized" : component === "cfnai" ? "moving_average_3m" : component === "yield_curve_2s10s" ? "spread" : ["headline_cpi", "core_cpi", "core_pce", "industrial_production", "real_consumption", "real_disposable_income", "retail_sales"].includes(component) ? "mom" : "level";
    const unit = component === "payrolls" ? "thousands" : component === "initial_claims" ? "persons" : ["cfnai", "nfci"].includes(component) ? "index" : ["housing_starts", "building_permits"].includes(component) ? "thousands SAAR" : component === "yield_curve_2s10s" ? "percentage points" : "percent";
    const change_unit = unit === "percent" ? "percentage points" : unit === "index" ? "index points" : unit;
    const current = component === "unemployment" ? 4.2 : feature_name === "mom" ? .3 : 3.2, previous = component === "unemployment" ? 4.1 : feature_name === "mom" ? .1 : 3;
    return { domain: domain.key, component, series_id, feature_name, label: readingLabels[component], frequency, unit, change_unit,
      current: { value: current, observation_date: dates[0], feature_as_of_date: "2026-10-08" },
      previous: { value: previous, observation_date: dates[1], feature_as_of_date: "2026-10-08" },
      three_periods_ago: { value: 2.8, observation_date: dates[2], feature_as_of_date: "2026-10-08" },
      context_yoy: feature_name === "mom" ? { current: { value: 3.2, observation_date: dates[0], feature_as_of_date: "2026-10-08" }, previous: { value: 3, observation_date: dates[1], feature_as_of_date: "2026-10-08" }, three_periods_ago: { value: 2.8, observation_date: dates[2], feature_as_of_date: "2026-10-08" } } : null,
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
afterEach(() => { cleanup(); setLanguage("en"); vi.unstubAllGlobals(); vi.restoreAllMocks(); window.location.hash = ""; });

test("Overview prioritizes 17 numeric readings and a Fed target range across six domains and preserves three navigation links", async () => {
  const fetch = mockApi(); render(<App />); await screen.findByRole("heading", { name: "Labor" });
  expect(document.querySelectorAll(".overview-domain")).toHaveLength(6);
  expect(document.querySelectorAll(".overview-reading")).toHaveLength(17);
  for (const card of document.querySelectorAll(".overview-domain")) {
    expect(card.querySelectorAll("table")).toHaveLength(card.getAttribute("aria-label") === "Financial Conditions brief" ? 2 : 3); expect(card.querySelector("details")).toBeNull();
    expect(card.textContent).not.toMatch(/momentum|accelerating|decelerating|Feature as-of|PAYEMS|CPIAUCSL/);
  }
  expect(within(screen.getByRole("navigation")).getAllByRole("link")).toHaveLength(3);
  expect(screen.queryByText("At a glance")).not.toBeInTheDocument();
  expect(screen.queryByText("Latest reading comparisons")).not.toBeInTheDocument();
  expect(screen.queryByText("Supporting MCI")).not.toBeInTheDocument();
  expect(screen.queryByText("Cross-currents")).not.toBeInTheDocument();
  expect(screen.queryByText("How this is assessed")).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(1); expect(String(fetch.mock.calls[0][0])).toMatch(/\/brief$/);
});

test("each reading displays latest, previous and three-period values and periods without expansion", async () => {
  const data = fixture(); mockApi(data); render(<EconomyBrief />); await screen.findByRole("heading", { name: "Labor" });
  const model = briefModel(data);
  for (const domain of model.domains) for (const reading of domain.compact) {
    const section = screen.getByRole("region", { name: reading.label });
    const cells = section.querySelectorAll("tbody td");
    for (const [i, point] of [reading.current, reading.previous, reading.earlier].entries()) {
      expect(cells[i].querySelector("strong")).toHaveTextContent(point.value);
      expect(cells[i].querySelector("time")).toHaveTextContent(point.period);
      expect(cells[i].closest("details")).toBeNull();
    }
    expect(within(section).getByRole("link", { name: reading.label })).toHaveAttribute("href", reading.indicatorHref);
    expect(within(section).getAllByRole("link").some(link => reading.sources.some(source => source.url === link.getAttribute("href")))).toBe(true);
  }
});

test.each([
  ["CPI MoM", "Previous month", "3 months earlier", "Jun 2026"],
  ["Real GDP QoQ annualized", "Previous quarter", "3 quarters earlier", "Q4 2025"],
  ["Initial claims, 4W average", "Previous week", "3 weeks earlier", "Sep 12, 2026"],
  ["10Y minus 2Y Treasury spread", "Previous observation", "3 observations earlier", "Oct 1, 2026"],
])("%s labels the correct comparison frequency", async (name, previous, earlier, day) => {
  mockApi(); render(<EconomyBrief />); const region = await screen.findByRole("region", { name });
  expect(within(region).getByRole("columnheader", { name: previous })).toBeInTheDocument();
  expect(within(region).getByRole("columnheader", { name: earlier })).toBeInTheDocument();
  expect(region).toHaveTextContent(day); expect(region).not.toHaveTextContent("calendar days");
});

test.each([
  ["unemployment", 4.2, 4.1, "negative"], ["unemployment", 4.1, 4.2, "positive"],
  ["initial_claims", 210000, 200000, "negative"], ["initial_claims", 190000, 200000, "positive"],
  ["payrolls", 200, 100, "positive"], ["payrolls", 100, 200, "negative"],
  ["real_gdp", 3, 2, "positive"], ["real_consumption", 1, 2, "negative"],
  ["industrial_production", 3, 2, "positive"], ["real_disposable_income", 3, 2, "positive"],
  ["headline_cpi", 2, 3, "neutral"], ["core_pce", 3, 2, "neutral"],
  ["headline_cpi", -.1, .1, "neutral"], ["core_cpi", .1, -.1, "neutral"],
  ["core_pce", -.2, -.1, "neutral"],
  ["yield_curve_2s10s", 1, .5, "neutral"], ["mortgage_rate", 7, 6, "neutral"],
  ["retail_sales", 5, 4, "neutral"], ["nfci", .2, .1, "neutral"],
  ["unemployment", 4, 4, "neutral"],
])("direction for %s (%s vs %s) has explicit presentation color %s", (component, current, previous, tone) => {
  const item = fixture().reading_comparisons!.data!.find(x => x.component === component)!;
  item.current!.value = current as number; item.previous!.value = previous as number; item.change = (current as number) - (previous as number);
  expect(comparisonTone(item)).toBe(tone);
  const reading = prepareReading(item.component, item.series_id, item);
  expect(reading.arrow).toBe(current === previous ? "\u2014" : current > previous ? "\u2191" : "\u2193");
});

test("color applies to the arrow/difference and rising unemployment remains numerically up", async () => {
  mockApi(); render(<EconomyBrief />); const region = await screen.findByRole("region", { name: "Unemployment rate" });
  expect(region.querySelector(".overview-change")).toHaveClass("overview-change--negative");
  expect(region.querySelector(".overview-change")).toHaveTextContent("\u2191 0.1 pp");
  expect(region.querySelector(".overview-value--latest strong")).toHaveTextContent("4.2");
  expect(region.querySelector(".overview-value--latest strong")?.className).toBe("");
});

test("missing required periods stay blank with their expected dates; zero stays numeric", async () => {
  const data = fixture(), item = data.reading_comparisons!.data![1];
  item.previous = null; item.three_periods_ago!.value = 0; item.change = null;
  mockApi(data); render(<EconomyBrief />); const region = await screen.findByRole("region", { name: "Unemployment rate" });
  const cells = region.querySelectorAll("tbody td"); expect(cells[1]).toHaveTextContent("\u2014"); expect(cells[1]).toHaveTextContent("Aug 2026");
  expect(cells[2].querySelector("strong")).toHaveTextContent("0");
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
  const table = document.querySelectorAll(".overview-values")[1];
  expect(table).toHaveTextContent("4,2"); expect(table).toHaveTextContent("pkt proc."); expect(table).toHaveTextContent("Poprzedni miesi");
  const report = briefMarkdown(briefModel(data), data, data.assembled_at);
  expect(report).toContain("4,2"); expect(report).toContain("3 miesi"); expect(report).toContain("https://fred.stlouisfed.org/series/UNRATE");
  expect(document.documentElement.lang).toBe("pl"); expect(fetch).toHaveBeenCalledTimes(1);
});

test("repeated low releases remain grouped and all dates are kept in the report", async () => {
  const data = fixture(), original = data.calendar.data!.events[0];
  data.calendar.data!.events.push(...[19,20,21].map(day => ({ ...original, release_id: 15, release_name: "H.15 Selected Interest Rates", importance: "low" as const, release_datetime_utc: null, release_time: null, source_timezone: null, release_date: `2026-10-${day}`, source_link: "https://www.federalreserve.gov/releases/h15/" })));
  mockApi(data); render(<EconomyBrief />); await screen.findByText("H.15 Selected Interest Rates - 3 publications");
  const report = briefMarkdown(briefModel(data), data, data.assembled_at); for (const day of [19,20,21]) expect(report).toContain(`2026-10-${day}`);
  expect(document.querySelectorAll(".overview-domain")[5].compareDocumentPosition(document.querySelector('[aria-labelledby="brief-policy"]')! ) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

test("empty and unavailable calendar states stay distinct", async () => {
  const data = fixture(); data.calendar.data!.events = []; mockApi(data); const { unmount } = render(<EconomyBrief />);
  await screen.findAllByText(/No tracked releases in the next 7 days/); unmount();
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

test("next FOMC decision is independent of seven-day preview, with CME link and DST-aware time", async () => {
  const data = fixture();
  data.policy = { status: "ready", error: null, data: { schedule_status: "available", retrieved_at: "2026-10-19T09:00:00Z", source_url: "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", market_probabilities: { status: "not_integrated", source_url: "https://www.cmegroup.com/fedwatch" },
    next_decision: { release_id: null, event_id: "fomc:2026-10-28", event_type: "fomc_decision", release_name: "FOMC policy decision", release_date: "2026-10-28", meeting_start_date: "2026-10-27", meeting_end_date: "2026-10-28", release_time: "14:00:00", source_timezone: "America/New_York", release_datetime_utc: "2026-10-28T18:00:00Z", retrieved_at: "2026-10-19T09:00:00Z", time_source_url: "https://www.federalreserve.gov/newsevents/2026-october.htm", importance: "high", source_link: "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", date_precision: "date", series: [] } } };
  mockApi(data); render(<EconomyBrief />);
  await screen.findByText("Oct 28, 2026 - 19:00 PL");
  expect(screen.getByRole("link", { name: "View market probabilities on CME FedWatch" })).toHaveAttribute("href", "https://www.cmegroup.com/fedwatch");
  expect(screen.getByText(/Market probabilities are not integrated/)).toBeInTheDocument();
  const model = briefModel(data);
  const report = briefMarkdown(model, data, data.assembled_at);
  const main = report.split("## Audit details")[0];
  expect(main).toContain(model.policy.headline);
  expect(main).toContain("CME probabilities and PMI data are not integrated or exported");
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


test("seven monthly activity/inflation rows compare MoM and show same-month YoY context", async () => {
  const data = fixture(); mockApi(data); render(<EconomyBrief />); await screen.findByRole("heading", { name: "Labor" });
  for (const item of data.reading_comparisons!.data!.filter(row => row.feature_name === "mom")) {
    const region = screen.getByRole("region", { name: item.label });
    const points = region.querySelectorAll("tbody td");
    expect(points[0].querySelector("strong")).toHaveTextContent("0.3");
    expect(points[1].querySelector("strong")).toHaveTextContent("0.1");
    expect(points[0].querySelector(".overview-yoy")).toHaveTextContent("3.20% YoY");
    expect(region.querySelector(".overview-change")).toHaveTextContent("+0.2 percentage points");
    expect(item.context_yoy!.current!.observation_date).toBe(item.current!.observation_date);
  }
  expect(data.reading_comparisons!.data!.filter(row => row.feature_name === "mom")).toHaveLength(7);
  expect(data.reading_comparisons!.data!.find(row => row.component === "real_gdp")!.feature_name).toBe("qoq_annualized");
});

test("YoY from another month is never shown next to current MoM", async () => {
  const data = fixture(), cpi = data.reading_comparisons!.data!.find(row => row.component === "headline_cpi")!;
  cpi.context_yoy!.current!.observation_date = "2026-08-01";
  mockApi(data); render(<EconomyBrief />); const region = await screen.findByRole("region", { name: "CPI MoM" });
  expect(region.querySelector(".overview-yoy")).toHaveTextContent("\u2014 YoY");
  expect(region.querySelector(".overview-yoy")).not.toHaveTextContent("3.2");
  expect(readingReportLine(briefModel(data).domains[1].compact[0])).toContain("YoY: \u2014");
});

test("Fed target block shows bounds, effective date, last rate change and explicit data freshness", async () => {
  const data = fixture(); mockApi(data); render(<EconomyBrief />); const block = await screen.findByRole("region", { name: "Fed target range" });
  expect(block).toHaveTextContent("3.75\u20134.00%"); expect(block).toHaveTextContent("Effective sinceSep 17, 2026");
  expect(block).toHaveTextContent("Last rate change+25 bp"); expect(block).toHaveTextContent("Observed through: Oct 18, 2026");
  expect(block).toHaveTextContent("Retrieved: Oct 19, 2026"); expect(block).not.toHaveTextContent("Last decision");
  expect(block.querySelector("table")).toBeNull();
  expect(within(block).getByRole("link", { name: "Lower bound source" })).toHaveAttribute("href", "https://fred.stlouisfed.org/series/DFEDTARL");
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
  item.change = delta;
  const reading = prepareReading(item.component, item.series_id, item);
  expect(reading.arrow).toBe("\u2014"); expect(reading.compactChange).toBe("\u2014"); expect(reading.tone).toBe("neutral");
  expect(readingReportLine(reading)).toContain(reading.change);
});

test("a visible rate change keeps a keyboard-accessible exact tooltip using the existing component", async () => {
  const data = fixture(), item = data.reading_comparisons!.data!.find(row => row.component === "headline_cpi")!;
  item.change = .0051; mockApi(data); render(<EconomyBrief />);
  const region = await screen.findByRole("region", { name: "CPI MoM" });
  const button = within(region).getByRole("button", { name: "CPI MoM: Change vs previous month" });
  expect(button).toHaveTextContent("\u2191"); expect(button).not.toHaveTextContent("0.0051");
  button.focus(); expect(button).toHaveFocus();
  const tooltip = document.getElementById(button.getAttribute("aria-describedby")!);
  expect(tooltip).toHaveAttribute("role", "tooltip"); expect(tooltip).toHaveTextContent("+0.0051 percentage points");
  fireEvent.click(button); expect(button).toHaveAttribute("aria-expanded", "true");
  fireEvent.keyDown(button, { key: "Escape" }); expect(button).toHaveAttribute("aria-expanded", "false");
  expect(briefMarkdown(briefModel(data), data, data.assembled_at)).toContain("+0.0051 percentage points");
});

test("compact calendar omits coverage and unknown times; five Polish publications have correct wording and no empty list", async () => {
  const data = fixture(), original = data.calendar.data!.events[0];
  data.calendar.data!.events = [19,20,21,22,23].map(day => ({ ...original, release_id: 15, release_name: "H.15 Selected Interest Rates", importance: "low" as const, release_datetime_utc: null, release_time: null, source_timezone: null, release_date: `2026-10-${day}` }));
  setLanguage("pl"); mockApi(data); render(<EconomyBrief />);
  await screen.findByText(/H.15.*5 publikacji/);
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
  ["en", "initial_claims", 198500, "198,500 people"], ["pl", "initial_claims", 198500, "198\u00a0500 os."],
  ["en", "housing_starts", 1275, "1,275 k"], ["pl", "building_permits", 1403, "1\u00a0403 tys."],
  ["en", "headline_cpi", .65, "0.65%"], ["pl", "headline_cpi", .65, "0,65%"],
  ["en", "unemployment", 4.2, "4.2%"], ["pl", "unemployment", 4.2, "4,2%"],
  ["en", "yield_curve_2s10s", .33, "0.33 pp"], ["pl", "yield_curve_2s10s", .33, "0,33 pp"],
  ["en", "nfci", -.5, "-0.50"], ["pl", "cfnai", -.5, "-0,50"],
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
    item.change = delta;
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
  expect(reading.tooltip).toContain("Difference: -0.36 percentage points."); expect(reading.tone).toBe("neutral");
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
  expect(level.compactChange).toBe("\u2191 250 people"); expect(level.tooltip).toContain("Value higher than in the previous week.");
  expect(level.tooltip).not.toContain("rate:"); expect(level.tooltip).toContain("Current value: 198,500 people");
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

test("all rendered values include units and level changes reuse the keyboard tooltip without report abbreviations", async () => {
  const data = fixture(); mockApi(data); render(<EconomyBrief />); await screen.findByRole("heading",{name:"Labor"});
  const model = briefModel(data);
  for (const reading of model.domains.flatMap(domain=>domain.compact)) {
    const region = screen.getByRole("region",{name:reading.label});
    for (const [i,point] of [reading.current,reading.previous,reading.earlier].entries()) expect(region.querySelectorAll("strong")[i]).toHaveTextContent(point.display);
    const button = within(region).getByRole("button",{name:`${reading.label}: ${reading.labels.change}`});
    button.focus(); expect(button).toHaveFocus();
    expect(document.getElementById(button.getAttribute("aria-describedby")!)).toHaveTextContent(reading.tooltip);
  }
  const housing = model.domains[4].compact[0];
  expect(readingReportLine(housing)).toContain("thousand homes/year (annualized)");
  expect(readingReportLine(housing)).not.toContain(" k");
});

test("FOMC and seven-day releases share one event block with one collapsed provenance block", async () => {
  mockApi(); render(<EconomyBrief />); const region = await screen.findByRole("region",{name:"Upcoming events"});
  expect(within(region).getByRole("heading",{name:"Next FOMC decision"})).toBeInTheDocument();
  expect(within(region).getByRole("heading",{name:"Upcoming releases - next 7 days"})).toBeInTheDocument();
  expect(within(region).getByText(/2026-10-18.*2026-10-24/)).toBeInTheDocument();
  expect(within(region).getByRole("link",{name:"View full calendar"})).toHaveAttribute("href","#/overview/calendar");
  const details = region.querySelector(".overview-event-details")!;
  expect(details).not.toHaveAttribute("open"); expect(details.querySelector("summary")).toHaveTextContent("Event sources and schedule details");
  expect(region.querySelectorAll(".overview-event-details")).toHaveLength(1);
});
