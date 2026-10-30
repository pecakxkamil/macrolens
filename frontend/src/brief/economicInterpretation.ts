import type { PreparedReading } from "./readingComparisons";
import type { PreparedFedTarget } from "./fedTarget";
import { readingVariant, flowFact } from "./readingFacts";
import { formatObservationDate } from "../format";

export type Interpretation = { tone: "favorable" | "unfavorable" | "mixed"; symbol: string; label: string; reason: string };
type Rule = { kind: "flow" | "jobs" | "inverse" | "housing" | "pmi" | "context"; features: readonly string[]; up?: string; down?: string; reason?: string };

// Editorial, domain-specific rules. These are not publisher classifications,
// market signals, consensus surprises, or a composite economic score.
export const interpretationRules: Record<string, Rule> = {
  payrolls: { kind: "jobs", features: ["monthly_change"] },
  unemployment: { kind: "inverse", features: ["level"],
    down: "Usually favorable for labor: lower unemployment; participation also matters.",
    up: "Usually unfavorable for labor: higher unemployment; participation also matters." },
  initial_claims: { kind: "inverse", features: ["raw"],
    down: "Usually favorable for labor: fewer new claims; one week does not establish a trend.",
    up: "Usually unfavorable for labor: more new claims; one week does not establish a trend." },
  job_openings: { kind: "context", features: ["level"], reason: "Mixed: vacancies describe labor demand, not completed hires; labor-market tightness matters." },
  average_hourly_earnings: { kind: "context", features: ["mom"], reason: "Mixed: wages support income but may add cost pressure; productivity and workforce composition matter." },
  headline_cpi: { kind: "context", features: ["mom"], reason: "Monthly consumer prices affect purchasing power and the interest-rate outlook." },
  core_cpi: { kind: "context", features: ["mom"], reason: "Core CPI measures consumer prices excluding food and energy." },
  core_pce: { kind: "context", features: ["mom"], reason: "Context-dependent: monthly core PCE needs broader context; the Fed's 2% goal concerns annual headline PCE." },
  producer_ppi: { kind: "context", features: ["mom"], reason: "PPI measures producers' selling prices, not their production costs." },
  real_gdp: { kind: "flow", features: ["qoq_annualized"] },
  industrial_production: { kind: "flow", features: ["mom"] },
  manufacturing_pmi: { kind: "pmi", features: ["raw"] },
  services_pmi: { kind: "pmi", features: ["raw"] },
  real_consumption: { kind: "flow", features: ["mom"] },
  real_disposable_income: { kind: "flow", features: ["mom"] },
  retail_sales: { kind: "context", features: ["mom"], reason: "Mixed: nominal sales include price changes and do not establish growth in real consumption." },
  housing_starts: { kind: "housing", features: ["level"],
    up: "Usually favorable for residential activity: a higher seasonally adjusted annualized pace of housing starts, not actual starts within one month.",
    down: "Usually unfavorable for residential activity: a lower seasonally adjusted annualized pace of housing starts, not actual starts within one month." },
  building_permits: { kind: "housing", features: ["level"],
    up: "Usually favorable for the construction pipeline: a higher seasonally adjusted annualized pace of permits, not actual permits within one month; permits do not guarantee completed construction.",
    down: "Usually unfavorable for the construction pipeline: a lower seasonally adjusted annualized pace of permits, not actual permits within one month or actual starts." },
  mortgage_rate: { kind: "context", features: ["level"], reason: "Context-dependent: mortgage rates affect affordability, but also reflect inflation and broader interest-rate conditions." },
  yield_curve_2s10s: { kind: "context", features: ["spread"], reason: "Context-dependent: the spread alone does not identify which yield moved or establish recession risk." },
  nfci: { kind: "context", features: ["level"],
    up: "Mixed: tighter financing conditions, not an overall judgment on economic health.",
    down: "Mixed: looser financing conditions, not an overall judgment on economic health." },
};
export const fedInterpretationRule = "This is the last stored decision, not a new decision today.";

function assessment(tone: Interpretation["tone"], reason: string): Interpretation {
  return { tone, reason, symbol: tone === "favorable" ? "+" : tone === "unfavorable" ? "\u2212" : "\u00b1",
    label: tone === "favorable" ? "Usually favorable for this economic area" : tone === "unfavorable" ? "Usually unfavorable for this economic area" : "Mixed or context-dependent economic meaning" };
}
export function economicInterpretation(reading: PreparedReading): Interpretation | null {
  const rule = interpretationRules[reading.key], raw = reading.raw;
  if (!rule || !raw || !rule.features.includes(raw.feature_name) || !["higher", "lower"].includes(reading.comparison)) return null;
  const current = raw.current!.value, previous = raw.previous!.value, higher = reading.comparison === "higher";
  if (rule.kind === "inverse" || rule.kind === "housing") {
    if (current < 0 || previous < 0) return null;
    const favorable = rule.kind === "inverse" ? !higher : higher;
    return assessment(favorable ? "favorable" : "unfavorable", higher ? rule.up! : rule.down!);
  }
  const variant = readingVariant(reading);
  if (rule.kind === "context") {
    if (["headline_cpi","core_cpi","core_pce","producer_ppi","average_hourly_earnings","retail_sales"].includes(reading.key)) {
      const definition=reading.key==="average_hourly_earnings"?" Productivity and workforce composition matter for interpreting average hourly pay.":reading.key==="retail_sales"?" The measure includes price changes, not just quantities purchased.":reading.key==="core_cpi"?" Core CPI excludes food and energy.":reading.key==="core_pce"?" Core PCE excludes food and energy; the Fed's 2% goal concerns annual headline PCE.":reading.key==="producer_ppi"?" PPI measures selling prices received by producers, not production costs.":"";
      return assessment("mixed",`${flowFact(reading,variant)}${definition}`);
    }
    return assessment("mixed", rule.reason ?? (higher ? rule.up! : rule.down!));
  }
  if (rule.kind === "pmi") {
    if (current < 0 || current > 100 || previous < 0 || previous > 100) return null;
    const displayed = Number(current.toFixed(2));
    if (displayed > 50 && higher) return assessment("favorable", "Usually favorable for this sector: above 50 and a stronger expansion signal.");
    if (displayed < 50 && !higher) return assessment("unfavorable", "Usually unfavorable for this sector: below 50 and a stronger contraction signal.");
    return assessment("mixed", displayed > 50 ? "Mixed: still above 50, but the expansion signal weakened." : displayed < 50 ? "Mixed: still below 50, despite a milder contraction signal." : "Mixed: at the sector's no-change threshold of 50.");
  }
  if (reading.key === "industrial_production") {
    const variants: Record<string, [Interpretation["tone"], string]> = {
      growingFaster: ["favorable", "Usually favorable for industry: production is still growing and its monthly growth rate increased."],
      turnPositive: ["favorable", "Usually favorable for industry: production returned to growth after the previous monthly decline."],
      fromZeroUp: ["favorable", "Usually favorable for industry: production grew after an unchanged month."],
      growingSlower: ["mixed", "Mixed: production is still growing, but its monthly growth rate slowed."],
      turnNegative: ["unfavorable", "Usually unfavorable for industry: production fell after the previous monthly increase."],
      declineDeepening: ["unfavorable", "Usually unfavorable for industry: the monthly production decline deepened."],
      fromZeroDown: ["unfavorable", "Usually unfavorable for industry: production fell after an unchanged month."],
      declineEasing: ["mixed", "Mixed: the monthly production decline eased, but production is still falling."],
    };
    if (variants[variant]) return assessment(...variants[variant]);
  }
  if (["growingFaster", "turnPositive", "fromZeroUp"].includes(variant)) return assessment("favorable", flowFact(reading,variant));
  if (["turnNegative", "declineDeepening", "fromZeroDown"].includes(variant)) return assessment("unfavorable", flowFact(reading,variant));
  return assessment("mixed",flowFact(reading,variant));
}
// The range has no adjacent previous reading. Its markers refer explicitly to
// the last recorded decision, beside that dated change rather than today's range.
export function fedDecisionMarkers(target: PreparedFedTarget) {
  const raw = target.raw, change = raw?.last_rate_change;
  if (target.range === "\u2014" || !change || ![change.lower_change_bps, change.upper_change_bps, change.previous_lower, change.previous_upper].every(Number.isFinite)) return null;
  const lower = change.lower_change_bps, upper = change.upper_change_bps;
  const higher = lower >= 0 && upper >= 0 && (lower > 0 || upper > 0);
  const lowerRate = lower <= 0 && upper <= 0 && (lower < 0 || upper < 0);
  if (!higher && !lowerRate) return null;
  return { arrow: higher ? "\u2191" : "\u2193", tone: higher ? "positive" : "negative",
    interpretation: assessment("mixed", `${higher?"The last recorded rate increase restrains borrowing and spending.":"The last recorded rate cut can support borrowing and spending."} ${fedInterpretationRule} Effective since: ${formatObservationDate(change.effective_date, "daily")}.`) };
}
