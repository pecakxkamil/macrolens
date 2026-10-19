import type { EconomyBriefResponse } from "../api/macrolens";
import { warsawDate } from "../datePeriods";
import { formatObservationDate } from "../format";
import { readingNumber } from "./readingComparisons";
const missing = "\u2014";
export function prepareFedTarget(data: EconomyBriefResponse["fed_target"]) {
  const raw = data?.data;
  const valid = raw?.availability === "available" && raw.lower !== null && raw.upper !== null && raw.lower <= raw.upper;
  const date = (value: string | null | undefined) => value ? formatObservationDate(value, "daily") : missing;
  const bps = (value: number) => `${value > 0 ? "+" : ""}${readingNumber(value, "bp")} bp`;
  const change = valid ? raw.last_rate_change : null;
  const lastChange = change ? change.change_bps !== null ? bps(change.change_bps) : `Lower: ${bps(change.lower_change_bps)}; upper: ${bps(change.upper_change_bps)}` : missing;
  return {
    range: valid ? `${readingNumber(raw.lower, "percent")}\u2013${readingNumber(raw.upper, "percent")}%` : missing,
    effective: date(valid ? raw.effective_date : null), lastChange,
    observed: date(raw?.observation_date), retrieved: date(raw?.retrieved_at ? warsawDate(new Date(raw.retrieved_at)) : null),
    sources: raw?.sources ?? ["DFEDTARL", "DFEDTARU"].map(series_id => ({ series_id, url: `https://fred.stlouisfed.org/series/${series_id}`, observation_date: null, retrieved_at: null })),
    raw,
  };
}
export type PreparedFedTarget = ReturnType<typeof prepareFedTarget>;
export function fedTargetReportLine(target: PreparedFedTarget): string {
  return `Fed target range: ${target.range}. Effective since: ${target.effective}. Last rate change: ${target.lastChange}. Observed through: ${target.observed}. Retrieved: ${target.retrieved}.`;
}
