import type { OverviewReadingComparison } from "../api/macrolens";
import { formatObservationDate } from "../format";
import { getLanguage, getLocale } from "../i18n/language";

// Arrow colors describe numerical direction only, never economic desirability.
export type ReadingDirection = "higher" | "lower" | "unchanged" | "unavailable";
export const readingLabels: Record<string, string> = {
  payrolls: "Nonfarm payrolls (NFP)", unemployment: "Unemployment rate", initial_claims: "Initial jobless claims", job_openings: "JOLTS job openings", average_hourly_earnings: "Hourly earnings MoM",
  manufacturing_pmi: "ISM Manufacturing PMI", services_pmi: "ISM Services PMI", producer_ppi: "Producer inflation PPI MoM", headline_cpi: "CPI MoM", core_cpi: "Core CPI MoM", core_pce: "Core PCE MoM", real_gdp: "Real GDP QoQ, annualized",
  cfnai: "CFNAI, 3M average", industrial_production: "Industrial production MoM", real_consumption: "Real consumption MoM",
  real_disposable_income: "Real disposable income MoM", retail_sales: "Nominal retail sales MoM",
  housing_starts: "Housing starts", building_permits: "Building permits", mortgage_rate: "30Y mortgage rate",
  fed_funds_rate: "Effective Fed Funds Rate", yield_curve_2s10s: "10Y–2Y Treasury spread", nfci: "NFCI",
};
const missing = "\u2014";
export function readingNumber(value: number | null | undefined, unit: string, precision = ["percent", "index", "percentage points"].includes(unit) ? 2 : ["persons", "claims", "thousands SAAR"].includes(unit) ? 0 : undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return missing;
  return new Intl.NumberFormat(getLocale(), { useGrouping: true, minimumFractionDigits: precision ?? 0, maximumFractionDigits: precision ?? 2 }).format(Math.abs(value) < .5 * 10 ** -(precision ?? 2) ? 0 : value);
}
function displayedDelta(item: OverviewReadingComparison): number {
  const precision = item.component === "unemployment" ? 1 : item.unit === "persons" || item.unit === "thousands SAAR" ? 0 : 2;
  return Number(item.change?.toFixed(precision));
}
export function readingUnit(unit: string): string {
  return ({ percent: "%", "percentage points": "pp", thousands: "thousand jobs", persons: "people", claims: "claims", "thousands of openings": "thousand openings", index: "index points", "thousands SAAR": "thousand homes/year (annualized)" } as Record<string, string>)[unit] ?? unit;
}
export function comparisonLabels(frequency: string) {
  if (frequency === "daily") return { previous: "Previous observation", earlier: "3 observations earlier", change: "Change vs previous observation" };
  if (frequency === "quarterly") return { previous: "Previous quarter", earlier: "3 quarters earlier", change: "Change vs previous quarter" };
  if (frequency === "weekly") return { previous: "Previous week", earlier: "3 weeks earlier", change: "Change vs previous week" };
  return { previous: "Previous month", earlier: "3 months earlier", change: "Change vs previous month" };
}
function screenNumber(key: string, unit: string, value?: number | null): string {
  return key === "job_openings" && typeof value === "number"
    ? readingNumber(value / 1000, "millions", 2)
    : readingNumber(value, unit, key === "unemployment" ? 1 : undefined);
}
export function comparisonDirection(item?: OverviewReadingComparison): ReadingDirection {
  if (!item?.current || !item.previous || !Number.isFinite(item.current.value) || !Number.isFinite(item.previous.value)
    || item.change === null || !Number.isFinite(item.change)) return "unavailable";
  if (screenNumber(item.component, item.unit, item.current.value) === screenNumber(item.component, item.unit, item.previous.value)) return "unchanged";
  return item.current.value > item.previous.value ? "higher" : "lower";
}
export function comparisonTone(item?: OverviewReadingComparison): "positive" | "negative" | "neutral" {
  if(item?.bea_direct)return "neutral";
  const direction = comparisonDirection(item);
  return direction === "higher" ? "positive" : direction === "lower" ? "negative" : "neutral";
}
// Compact units are local to Overview; reports keep the full unit definition.
export function compactReadingValue(value: string, unit: string): string {
  if (value === missing) return missing;
  const suffix = ({ percent: "%", "percentage points": " pp", thousands: getLanguage() === "pl" ? " tys." : " k", persons: getLanguage() === "pl" ? " os." : " people", claims: getLanguage() === "pl" ? " wniosk\u00f3w" : " claims", "thousands SAAR": getLanguage() === "pl" ? " tys." : " k" } as Record<string, string>)[unit] ?? "";
  return value + suffix;
}
function fullUnit(unit: string): string { return unit === "percentage points" ? "percentage points" : readingUnit(unit); }
function exactNumber(value: number): string { return new Intl.NumberFormat(getLocale(), { useGrouping: true, maximumSignificantDigits: 12 }).format(value); }
export function prepareReading(key: string, series: string, item?: OverviewReadingComparison) {
  const unit = item?.unit ?? "";
  const point = (value: OverviewReadingComparison["current"] | undefined, expected?: string | null, context?: OverviewReadingComparison["current"]) => {
    const formatted = readingNumber(value?.value, unit, value?.published_precision ?? (key === "unemployment" ? 1 : undefined));
    const screenValue = value?.published_precision !== undefined && value?.published_precision !== null ? formatted : screenNumber(key, unit, value?.value);
    const screenSuffix = key === "job_openings" && formatted !== missing ? getLanguage() === "pl" ? " mln" : " m" : compactReadingValue("", unit);
    return {
      screenValue, screenSuffix: formatted === missing ? "" : screenSuffix,
      value: formatted, suffix: formatted === missing ? "" : compactReadingValue("", unit), display: screenValue === missing ? missing : screenValue + screenSuffix,
      period: value?.observation_date || expected ? formatObservationDate(value?.observation_date ?? expected!, item?.frequency) : missing,
      date: value?.observation_date ?? expected ?? undefined,
      yoy: item?.feature_name === "mom" && series !== "PPIFIS" ? readingNumber(context?.observation_date === (value?.observation_date ?? expected) ? context?.value : null, "percent",context?.published_precision??undefined) : undefined,
    };
  };
  const current = point(item?.current, undefined, item?.context_yoy?.current);
  const previous = point(item?.previous, item?.expected_previous_observation_date, item?.context_yoy?.previous);
  const earlier = point(item?.three_periods_ago, item?.expected_three_periods_ago_date, item?.context_yoy?.three_periods_ago);
  const change = item?.change;
  const delta = item?.current && item.previous && typeof change === "number" && Number.isFinite(change) ? change : null;
  const roundedDelta = delta === null ? null : displayedDelta(item!);
  const rate = ["mom", "yoy", "annualized_3m", "qoq_annualized"].includes(item?.feature_name ?? "");
  const comparison = comparisonDirection(item);
  const arrow = comparison === "unavailable" ? "?" : comparison === "unchanged" ? missing : comparison === "higher" ? "\u2191" : "\u2193";
  const difference = delta === null ? missing : `${delta > 0 ? "+" : ""}${readingNumber(delta, item!.change_unit,item?.bea_direct?1:undefined)} ${readingUnit(item!.change_unit)}`;
  const exactDifference = delta === null ? missing : `${delta > 0 ? "+" : ""}${exactNumber(delta)} ${readingUnit(item!.change_unit)}`;
  const fullDifference = delta === null ? missing : `${delta > 0 ? "+" : ""}${exactNumber(delta)} ${fullUnit(item!.change_unit)}`;
  const period = ({ quarterly: "quarter", weekly: "week", daily: "observation" } as Record<string, string>)[item?.frequency ?? ""] ?? "month";
  const subject = rate ? "Rate" : "Value";
  const direction = roundedDelta === 0 ? `${subject} unchanged at displayed precision.` : `${subject} ${delta! > 0 ? "higher" : "lower"} than in the previous ${period}.`;
  const exactPoint = (value: OverviewReadingComparison["current"] | undefined) => value ? `${exactNumber(value.value)}${unit === "percent" ? "%" : ` ${fullUnit(unit)}`}` : missing;
  const tooltip = delta === null ? `${comparisonLabels(item?.frequency ?? "monthly").change}: ${missing}` : `${direction} Previous ${rate ? "rate" : "value"}: ${exactPoint(item?.previous)} (${previous.period}). Current ${rate ? "rate" : "value"}: ${exactPoint(item?.current)} (${current.period}). Difference: ${fullDifference}.`;
  const magnitude = delta === null ? missing : compactReadingValue(readingNumber(Math.abs(roundedDelta!), item!.change_unit, key === "unemployment" ? 1 : undefined), item!.change_unit);
  return { key, rate, exactDifference, tooltip, hasChange: delta !== null, label: readingLabels[key] ?? item?.label ?? key,
    indicatorHref: `#/explore/indicators/${series.split(" / ")[0]}`,
    sources: series.split(" / ").map((id) => ({ label: id, url: item?.source_url ?? (id.startsWith("ISM_") ? "https://www.ismworld.org/" : `https://fred.stlouisfed.org/series/${id}`) })),
    unit: readingUnit(unit), reportUnit: fullUnit(unit), current, previous, earlier, labels: comparisonLabels(item?.frequency ?? "monthly"),
    claimsAverage: key === "initial_claims" && item?.current && item.context_moving_average_4w?.observation_date === item.current.observation_date && Number.isFinite(item.context_moving_average_4w.value)
      ? { value: readingNumber(item.context_moving_average_4w.value, "claims"), date: item.current.observation_date } : null,
    comparison, arrow, difference, change: fullDifference,
    compactChange: delta === null ? missing : rate ? arrow : `${arrow === missing ? "" : `${arrow} `}${magnitude}`,
    tone: comparisonTone(item), raw: item };
}
export type PreparedReading = ReturnType<typeof prepareReading>;
export function readingReportLine(reading: PreparedReading): string {
  const value = (point: PreparedReading["current"]) => `${point.value} (${point.period})${point.yoy !== undefined ? `; YoY: ${point.yoy}${point.yoy === missing ? "" : "%"}` : ""}`;
  const bea=reading.raw?.bea_direct;
  const evidence=bea?` Source: U.S. Bureau of Economic Analysis; ${bea.source_url}; published precision: one decimal; method: published rate or level; captured snapshot, not verified first print; retrieved: ${bea.actual_provenance?.retrieved_at}; hash: ${bea.actual_provenance?.raw_hash}; stage: ${bea.actual_provenance?.estimate_stage ?? 'monthly'}; comparison: ${bea.comparison_status}; annual context source: ${bea.annual_context_source ?? "BEA or unavailable"}; FRED alternative: ${JSON.stringify(bea.fred_alternative)}; source comparison: ${bea.source_comparison}; policy: ${bea.usage_rights?.terms_url}; ${bea.usage_rights?.modifications}`:'';
  return `${evidence} ${reading.label}${reading.reportUnit ? ` [${reading.reportUnit}]` : ""}: Latest: ${value(reading.current)}; ${reading.labels.previous}: ${value(reading.previous)}; ${reading.labels.earlier}: ${value(reading.earlier)}; ${reading.labels.change}: ${reading.change}.${reading.claimsAverage ? ` Same-week 4W average: ${reading.claimsAverage.value} claims (${reading.current.period}).` : ""}`;
}
