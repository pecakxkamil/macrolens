import { afterEach, expect, test } from "vitest";
import { economicInterpretation, fedDecisionMarkers, interpretationRules } from "./economicInterpretation";
import { prepareReading } from "./readingComparisons";
import { readingHoverText } from "./readingHoverText";
import { prepareFedTarget } from "./fedTarget";
import { domainSelection } from "./briefModel";
import { setLanguage, tText } from "../i18n/language";
import type { OverviewReadingComparison } from "../api/macrolens";

afterEach(() => setLanguage("en"));
function reading(key: string, current: number, previous: number | null) {
  const unit = key === "payrolls" ? "thousands" : key === "initial_claims" ? "claims" : key === "job_openings" ? "thousands of openings" : ["manufacturing_pmi", "services_pmi", "nfci"].includes(key) ? "index" : ["housing_starts", "building_permits"].includes(key) ? "thousands SAAR" : key === "yield_curve_2s10s" ? "percentage points" : "percent";
  const feature_name = key === "payrolls" ? "monthly_change" : key === "real_gdp" ? "qoq_annualized" : ["initial_claims", "manufacturing_pmi", "services_pmi"].includes(key) ? "raw" : key === "yield_curve_2s10s" ? "spread" : ["unemployment", "job_openings", "housing_starts", "building_permits", "mortgage_rate", "nfci"].includes(key) ? "level" : "mom";
  const point = (value: number, date: string) => ({ value, observation_date: date, feature_as_of_date: null });
  return prepareReading(key, "TEST", { component: key, series_id: "TEST", unit, feature_name, frequency: "monthly",
    current: point(current, "2024-02-01"), previous: previous === null ? null : point(previous, "2024-01-01"),
    change: previous === null ? null : current - previous, change_unit: unit === "percent" ? "percentage points" : unit,
  } as OverviewReadingComparison);
}

test("every current Overview measure has an explicit interpretation policy", () => {
  expect(Object.keys(interpretationRules).sort()).toEqual(domainSelection.flatMap(d => d.readings.map(([key]) => key)).sort());
});
test.each([
  ["unemployment", 4, 4.1, "\u2193", "negative", "favorable", "+"],
  ["unemployment", 4.1, 4, "\u2191", "positive", "unfavorable", "\u2212"],
  ["initial_claims", 199000, 200000, "\u2193", "negative", "favorable", "+"],
  ["payrolls", 3.2, 3, "\u2191", "positive", "favorable", "+"],
  ["payrolls", 29, 133, "\u2193", "negative", "mixed", "\u00b1"],
  ["payrolls", -10, -30, "\u2191", "positive", "mixed", "\u00b1"],
  ["real_gdp", -1, -2, "\u2191", "positive", "mixed", "\u00b1"],
  ["real_gdp", -2, -1, "\u2193", "negative", "unfavorable", "\u2212"],
  ["real_gdp", 1, -1, "\u2191", "positive", "favorable", "+"],
  ["real_gdp", .5, 1, "\u2193", "negative", "mixed", "\u00b1"],
  ["real_consumption", 0, 1, "\u2193", "negative", "mixed", "\u00b1"],
  ["manufacturing_pmi", 55, 54, "\u2191", "positive", "favorable", "+"],
  ["manufacturing_pmi", 54.5, 54.6, "\u2193", "negative", "mixed", "\u00b1"],
  ["services_pmi", 47, 49, "\u2193", "negative", "unfavorable", "\u2212"],
  ["services_pmi", 49, 47, "\u2191", "positive", "mixed", "\u00b1"],
  ["services_pmi", 50, 49, "\u2191", "positive", "mixed", "\u00b1"],
  ["headline_cpi", .2, .4, "\u2193", "negative", "mixed", "\u00b1"],
  ["core_pce", -.2, -.1, "\u2193", "negative", "mixed", "\u00b1"],
  ["producer_ppi", .4, .2, "\u2191", "positive", "mixed", "\u00b1"],
  ["housing_starts", 1275, 1309, "\u2193", "negative", "unfavorable", "\u2212"],
  ["building_permits", 1400, 1300, "\u2191", "positive", "favorable", "+"],
  ["average_hourly_earnings", .4, .2, "\u2191", "positive", "mixed", "\u00b1"],
] as const)("%s %s vs %s separates arrow %s/%s from interpretation %s", (key, current, previous, arrow, tone, interpretation, symbol) => {
  const r = reading(key, current, previous), result = economicInterpretation(r);
  expect(r.arrow).toBe(arrow); expect(r.tone).toBe(tone);
  expect(result?.tone).toBe(interpretation); expect(result?.symbol).toBe(symbol);
});
test("a smaller negative growth rate remains contraction, not expansion", () => {
  expect(economicInterpretation(reading("payrolls", -10, -30))?.reason).toContain("still falling");
  expect(economicInterpretation(reading("real_gdp", -1, -2))?.reason).toContain("still falling");
});
test.each(["job_openings", "average_hourly_earnings", "headline_cpi", "core_cpi", "core_pce", "producer_ppi", "retail_sales", "mortgage_rate", "yield_curve_2s10s", "nfci"])("%s avoids an unconditional economic judgment", key => {
  for (const [c, p] of [[30, 10], [10, 30]]) expect(economicInterpretation(reading(key, c, p))?.tone).toBe("mixed");
});
test.each(["en", "pl"] as const)("equal screen values have no new economic interpretation in %s", lang => {
  setLanguage(lang);
  for (const r of [reading("headline_cpi", .304, .296), reading("unemployment", 4.14, 4.06), reading("job_openings", 7084, 7081), reading("real_gdp", 1, 1)]) {
    expect(r.arrow).toBe("\u2014"); expect(r.tone).toBe("neutral"); expect(economicInterpretation(r)).toBeNull();
    expect(readingHoverText(r)).toContain("unchanged at displayed precision");
  }
  // A visible change across a rounding boundary still receives a direction.
  const crossed = reading("headline_cpi", .3051, .3049);
  expect(crossed.current.screenValue).not.toBe(crossed.previous.screenValue); expect(crossed.arrow).toBe("\u2191");
});
test("missing comparisons are distinct from unchanged readings; unsupported measures receive no assessment", () => {
  const r = reading("unemployment", 4, null);
  expect(r.arrow).toBe("?"); expect(r.comparison).toBe("unavailable"); expect(economicInterpretation(r)).toBeNull();
  expect(readingHoverText(r)).toBe("Comparison unavailable.");
  const bad = reading("real_gdp", 3, 2); bad.raw!.feature_name = "level"; expect(economicInterpretation(bad)).toBeNull();
  const nan = reading("headline_cpi", NaN, .2); expect(economicInterpretation(nan)).toBeNull();
  expect(economicInterpretation(reading("unknown", 2, 1))).toBeNull();
});
test("all configured explanations translate in both directions without changing source precision", () => {
  for (const key of Object.keys(interpretationRules)) for (const [c, p] of [[3, 2], [2, 3], [-1, -2], [54, 53], [49, 47]]) {
    const r = reading(key, c, p), result = economicInterpretation(r);
    if (!result) continue;
    setLanguage("pl"); expect(tText(result.reason)).not.toBe(result.reason); expect(tText(result.label)).not.toBe(result.label); setLanguage("en");
    expect(r.raw!.current!.value).toBe(c); expect(r.raw!.previous!.value).toBe(p);
  }
});
test("Fed markers refer to the dated stored decision and require an actual prior range", () => {
  const target = { range: "3.75-4.00%", raw: { last_rate_change: { effective_date: "2026-09-17", lower_change_bps: 25, upper_change_bps: 25, previous_lower: 3.5, previous_upper: 3.75 } } } as ReturnType<typeof prepareFedTarget>;
  const result = fedDecisionMarkers(target)!;
  expect(result.arrow).toBe("\u2191"); expect(result.interpretation.tone).toBe("mixed");
  expect(result.interpretation.reason).toContain("Sep 17, 2026"); expect(result.interpretation.reason).toContain("not a new decision today");
  expect(fedDecisionMarkers(prepareFedTarget(undefined))).toBeNull();
  target.raw!.last_rate_change!.lower_change_bps = -25; target.raw!.last_rate_change!.upper_change_bps = -25;
  expect(fedDecisionMarkers(target)?.tone).toBe("negative");
});


test.each(["headline_cpi","core_cpi","producer_ppi"])("%s reason follows the actual price transition while its marker remains mixed",key=>{
 for(const [c,p,phrase] of [[.65,.4,"more quickly"],[.2,.4,"more slowly"],[-.1,.2,"fell after"],[-.1,-.2,"fell less sharply"]] as const){
  const note=economicInterpretation(reading(key,c,p))!;expect(note.reason).toContain(phrase);expect(note.tone).toBe("mixed");expect(note.symbol).toBe("\u00b1");expect(note.reason).not.toMatch(/whether inflation is sustainably moderating|costs and demand/);
 }
});

test("consumption and income reasons distinguish renewed growth from acceleration and a new decline from deeper declines",()=>{
 expect(economicInterpretation(reading("real_consumption",.55,.05))?.reason).toContain("growth rate increased");
 expect(economicInterpretation(reading("real_consumption",.2,-.1))?.reason).toContain("rose after the previous decline");
 expect(economicInterpretation(reading("real_disposable_income",-.03,.31))?.reason).toContain("fell after the previous increase");
 expect(economicInterpretation(reading("real_disposable_income",-.2,-.1))?.reason).toContain("fell more sharply");
 expect(economicInterpretation(reading("average_hourly_earnings",.13,.32))?.reason).toContain("workforce composition");
});
