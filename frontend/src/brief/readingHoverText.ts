import type { PreparedReading } from "./readingComparisons";
import { readingNumber } from "./readingComparisons";

// Screen-only rounding and wording; report values retain their original precision.
function readingHoverContent(reading: PreparedReading) {
  const raw = reading.raw;
  if (!raw?.current || !raw.previous || reading.comparison === "unavailable" || raw.change === null) return { lines: [reading.label, "Comparison unavailable."], text: "Comparison unavailable." };
  const precision = ["claims", "persons", "thousands", "thousands SAAR", "thousands of openings"].includes(raw.unit) ? 0 : 2;
  const delta = Number(raw.change.toFixed(precision));
  const period = ({daily:"observation",weekly:"week",quarterly:"quarter"} as Record<string,string>)[raw.frequency] ?? "month";
  const special: Record<string, [string,string]> = {
    housing_starts: ["More housing starts than in the previous month (seasonally adjusted, annualized).", "Fewer housing starts than in the previous month (seasonally adjusted, annualized)."],
    building_permits: ["More building permits than in the previous month (seasonally adjusted, annualized).", "Fewer building permits than in the previous month (seasonally adjusted, annualized)."],
    initial_claims: ["More new jobless claims than in the previous week.", "Fewer new jobless claims than in the previous week."],
  };
  const description = reading.comparison === "unchanged" ? `${reading.label}: unchanged at displayed precision.`
    : special[reading.key]?.[reading.comparison === "higher" ? 0 : 1] ?? `${reading.label}: ${reading.rate ? "Rate" : "Value"} ${reading.comparison === "higher" ? "higher" : "lower"} than in the previous ${period}.`;
  const unit = ({percent:"percentage points", "percentage points":"percentage points", "thousands SAAR":"thousand homes/year (annualized)", thousands:"thousand jobs", "index":"index points"} as Record<string,string>)[raw.unit] ?? raw.change_unit;
  const shortUnit = raw.unit === "thousands SAAR" ? "thousand (annualized)" : unit;
  const difference = raw.change !== 0 && delta === 0
    ? `Change smaller than ${readingNumber(10 ** -precision, "", precision)} ${shortUnit}.`
    : `Difference: ${delta > 0 ? "+" : ""}${readingNumber(delta, "", precision)} ${shortUnit}.`;
  const prefix = `${reading.label}: `;
  const body = description.startsWith(prefix) ? description.slice(prefix.length) : description;
  const comparison = `${body.charAt(0).toUpperCase()}${body.slice(1)} ${reading.current.period} vs ${reading.previous.period}.`;
  return { lines: [reading.label, comparison, difference], text: `${description} ${reading.current.period} vs ${reading.previous.period}. ${difference}` };
}

export function readingHoverLines(reading: PreparedReading): string[] {
  return readingHoverContent(reading).lines;
}

export function readingHoverText(reading: PreparedReading): string {
  return readingHoverContent(reading).text;
}
