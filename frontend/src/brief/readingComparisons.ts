import type { OverviewReadingComparison } from "../api/macrolens";
import { formatObservationDate } from "../format";
import { getLocale } from "../i18n/language";

// Presentation only: no thresholds, classifications or scoring are calculated.
const directionStyle: Record<string, "increase" | "decrease" | "neutral"> = {
  payrolls: "increase", unemployment: "decrease", initial_claims: "decrease",
  headline_cpi: "neutral", core_cpi: "neutral", core_pce: "neutral",
  real_gdp: "increase", cfnai: "increase", industrial_production: "increase",
  real_consumption: "increase", real_disposable_income: "increase",
  housing_starts: "increase", building_permits: "increase",
  retail_sales: "neutral", mortgage_rate: "neutral", fed_funds_rate: "neutral",
  yield_curve_2s10s: "neutral", nfci: "neutral",
};
export const readingLabels: Record<string, string> = {
  payrolls: "Payroll monthly change", unemployment: "Unemployment rate", initial_claims: "Initial claims, 4W average",
  headline_cpi: "CPI MoM", core_cpi: "Core CPI MoM", core_pce: "Core PCE MoM", real_gdp: "Real GDP QoQ annualized",
  cfnai: "CFNAI, 3M average", industrial_production: "Industrial production MoM", real_consumption: "Real consumption MoM",
  real_disposable_income: "Real disposable income MoM", retail_sales: "Nominal retail sales MoM",
  housing_starts: "Housing starts", building_permits: "Building permits", mortgage_rate: "30Y mortgage rate",
  fed_funds_rate: "Effective Fed Funds Rate", yield_curve_2s10s: "10Y minus 2Y Treasury spread", nfci: "NFCI",
};
const missing = "\u2014";
export function readingNumber(value: number | null | undefined, unit: string, precision = unit === "percent" ? 2 : unit === "persons" || unit === "thousands SAAR" ? 0 : undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return missing;
  return new Intl.NumberFormat(getLocale(), { minimumFractionDigits: precision ?? 0, maximumFractionDigits: precision ?? 2 }).format(Math.abs(value) < .5 * 10 ** -(precision ?? 2) ? 0 : value);
}
function displayedDelta(item: OverviewReadingComparison): number {
  const precision = item.component === "unemployment" ? 1 : item.unit === "persons" || item.unit === "thousands SAAR" ? 0 : 2;
  return Number(item.change?.toFixed(precision));
}
export function readingUnit(unit: string): string {
  return ({ percent: "%", "percentage points": "pp", thousands: "thousand jobs", persons: "people", index: "index points", "thousands SAAR": "thousand homes/year (annualized)" } as Record<string, string>)[unit] ?? unit;
}
export function comparisonLabels(frequency: string) {
  if (frequency === "daily") return { previous: "Previous observation", earlier: "3 observations earlier", change: "Change vs previous observation" };
  if (frequency === "quarterly") return { previous: "Previous quarter", earlier: "3 quarters earlier", change: "Change vs previous quarter" };
  if (frequency === "weekly") return { previous: "Previous week", earlier: "3 weeks earlier", change: "Change vs previous week" };
  return { previous: "Previous month", earlier: "3 months earlier", change: "Change vs previous month" };
}
export function comparisonTone(item?: OverviewReadingComparison): "positive" | "negative" | "neutral" {
  if (!item?.current || !item.previous || item.change === null || !Number.isFinite(item.change) || displayedDelta(item) === 0) return "neutral";
  const style = directionStyle[item.component] ?? "neutral";
  if (style === "neutral") return "neutral";
  const improves = style === "increase" ? item.change > 0 : item.change < 0;
  return improves ? "positive" : "negative";
}
export function prepareReading(key: string, series: string, item?: OverviewReadingComparison) {
  const unit = item?.unit ?? "";
  const point = (value: OverviewReadingComparison["current"] | undefined, expected?: string | null, context?: OverviewReadingComparison["current"]) => ({
    value: readingNumber(value?.value, unit, key === "unemployment" ? 1 : undefined),
    period: value?.observation_date || expected ? formatObservationDate(value?.observation_date ?? expected!, item?.frequency) : missing,
    date: value?.observation_date ?? expected ?? undefined,
    yoy: item?.feature_name === "mom" ? readingNumber(context?.observation_date === (value?.observation_date ?? expected) ? context?.value : null, "percent") : undefined,
  });
  const change = item?.change;
  const delta = typeof change === "number" && Number.isFinite(change) ? change : null;
  const roundedDelta = delta === null ? null : displayedDelta(item!);
  const rate = ["mom", "yoy", "annualized_3m", "qoq_annualized"].includes(item?.feature_name ?? "");
  const arrow = roundedDelta === null || roundedDelta === 0 ? missing : roundedDelta > 0 ? "\u2191" : "\u2193";
  const difference = delta === null ? missing : `${delta > 0 ? "+" : ""}${readingNumber(delta, item!.change_unit)} ${readingUnit(item!.change_unit)}`;
  const exactDifference = delta === null ? missing : `${delta > 0 ? "+" : ""}${new Intl.NumberFormat(getLocale(), { maximumSignificantDigits: 15 }).format(delta)} ${readingUnit(item!.change_unit)}`;
  return { key, rate, exactDifference, label: readingLabels[key] ?? item?.label ?? key,
    indicatorHref: `#/explore/indicators/${series.split(" / ")[0]}`,
    sources: series.split(" / ").map((id) => ({ label: id, url: `https://fred.stlouisfed.org/series/${id}` })),
    unit: readingUnit(unit), current: point(item?.current, undefined, item?.context_yoy?.current), previous: point(item?.previous, item?.expected_previous_observation_date, item?.context_yoy?.previous),
    earlier: point(item?.three_periods_ago, item?.expected_three_periods_ago_date, item?.context_yoy?.three_periods_ago), labels: comparisonLabels(item?.frequency ?? "monthly"),
    arrow, difference, change: delta === null ? missing : `${arrow} ${exactDifference}`,
    compactChange: delta === null ? missing : rate ? arrow : `${arrow} ${roundedDelta! > 0 ? "+" : ""}${readingNumber(roundedDelta, item!.change_unit, key === "unemployment" ? 1 : undefined)} ${readingUnit(item!.change_unit)}`,
    tone: comparisonTone(item), raw: item };
}
export type PreparedReading = ReturnType<typeof prepareReading>;
export function readingReportLine(reading: PreparedReading): string {
  const value = (point: PreparedReading["current"]) => `${point.value} (${point.period})${point.yoy !== undefined ? `; YoY: ${point.yoy}${point.yoy === missing ? "" : "%"}` : ""}`;
  return `${reading.label}${reading.unit ? ` [${reading.unit}]` : ""}: Latest: ${value(reading.current)}; ${reading.labels.previous}: ${value(reading.previous)}; ${reading.labels.earlier}: ${value(reading.earlier)}; ${reading.labels.change}: ${reading.change}.`;
}
