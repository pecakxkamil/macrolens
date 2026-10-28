import { availabilityPresentation, availabilityTime, availabilityReportDetails } from "./sourceCheckPresentation";
import { overviewUpcomingEvents, upcomingEventReport, eventImportanceNote } from "./upcomingEvents";
import { prepareFedTarget, fedTargetReportLine } from "./fedTarget";
import { prepareReading, readingReportLine } from "./readingComparisons";
import { warsawDate, previousMonthEnd } from "../datePeriods";
export { warsawDate, previousMonthEnd } from "../datePeriods";
import { getLocale, getLanguage, t } from "../i18n/language";
import type { BriefClassificationBasis, BriefComparison, CalendarEvent, EconomyBriefResponse, MacroStateReading, MciHistoryResponse } from "../api/macrolens";
import { formatClassification, formatNumber, formatObservationDate } from "../format";
import { formatCalendarDate, formatPolandTime, groupCalendarEvents } from "../calendar/calendarDates";

export type PitState = { status: "loading" | "unavailable"; data?: undefined } | { status: "ready"; data: MciHistoryResponse };
export const domainSelection = [
  { key: "labor", name: "Labor", readings: [["payrolls", "PAYEMS"], ["unemployment", "UNRATE"], ["initial_claims", "ICSA"], ["job_openings", "JTSJOL"], ["average_hourly_earnings", "CES0500000003"]] },
  { key: "inflation", name: "Inflation", readings: [["headline_cpi", "CPIAUCSL"], ["core_cpi", "CPILFESL"], ["core_pce", "PCEPILFE"], ["producer_ppi", "PPIFIS"]] },
  { key: "growth", name: "Growth", readings: [["real_gdp", "GDPC1"], ["industrial_production", "INDPRO"], ["manufacturing_pmi", "ISM_MANUFACTURING_PMI"], ["services_pmi", "ISM_SERVICES_PMI"]] },
  { key: "consumer", name: "Consumer", readings: [["real_consumption", "PCEC96"], ["real_disposable_income", "DSPIC96"], ["retail_sales", "RSAFS"]] },
  { key: "housing", name: "Housing", readings: [["housing_starts", "HOUST"], ["building_permits", "PERMIT"], ["mortgage_rate", "MORTGAGE30US"]] },
  { key: "financial_conditions", name: "Financial Conditions", readings: [["yield_curve_2s10s", "DGS2 / DGS10"], ["nfci", "NFCI"]] },
] as const;
// Additional readings already supplied by Macro State; the first screen stays curated.
const additionalReadings: Record<string, Array<[string, string]>> = {
  labor: [["continuing_claims", "CCSA"], ["job_openings", "JTSJOL"], ["labor_force_participation", "CIVPART"], ["average_hourly_earnings", "CES0500000003"]],
  inflation: [["headline_pce", "PCEPI"], ["employment_cost_index", "ECIALLCIV"], ["average_hourly_earnings", "CES0500000003"]],
  growth: [["cfnai", "CFNAI"], ["capacity_utilization", "TCU"], ["durable_goods_orders", "DGORDER"]],
  consumer: [["saving_rate", "PSAVERT"]],
  housing: [["new_home_sales", "HSN1F"]],
  financial_conditions: [["fed_funds_rate", "DFF"], ["treasury_2y", "DGS2"], ["treasury_10y", "DGS10"], ["real_yield_10y", "DFII10"]],
};
function detailReadings(spec: typeof domainSelection[number]): ReadonlyArray<readonly [string, string]> {
  return [...spec.readings, ...additionalReadings[spec.key].filter(([key]) => !spec.readings.some(([selected]) => selected === key))];
}
export function shortTimestamp(instant: string): string {
  return new Intl.DateTimeFormat(getLanguage() === "pl" ? "pl-PL" : "en-GB", { timeZone: "Europe/Warsaw", year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", timeZoneName: "short" }).format(new Date(instant));
}
export function displayValue(value: number, unit: string): string {
  const number = (value: number, precision = 2) => new Intl.NumberFormat(getLocale(), { maximumFractionDigits: precision }).format(value);
  if (unit === "percent") return `${number(value)}%`;
  if (unit === "percentage points") return `${number(value)} ${getLanguage() === "pl" ? "pkt proc." : "pp"}`;
  if (unit === "thousands") return `${number(value)} thousand jobs`;
  if (unit === "persons") return `${number(value, 0)} people`;
  if (unit === "thousands SAAR") return `${number(value / 1000, 3)} million homes/year (annualized)`;
  return `${number(value)} ${unit === "index" ? "index points" : unit}`;
}
export function basisText(basis: BriefClassificationBasis): string {
  const inputs = basis.inputs.map((input) => `${input.label}: ${formatNumber(input.value, 6)} ${input.unit} [${input.feature_name}]`).join("; ");
  const windowLabel = basis.component === "real_gdp" && basis.field === "momentum" ? "Quarterly pace relative to annual growth"
    : ["initial_claims","continuing_claims"].includes(basis.component) && basis.field === "momentum" ? `${basis.component === "initial_claims" ? "Initial claims" : "Continuing claims"}: 4-week average relative to 13-week average`
    : basis.inputs.some(input=>input.feature_name==="annualized_3m") ? `${basis.label}: 3-month annualized pace relative to annual pace` : null;
  const votes = basis.component_classifications ? ` Component assessments: ${Object.entries(basis.component_classifications).map(([key, value]) => `${key}: ${formatClassification(value)}`).join("; ")}.` : "";
  return `${windowLabel ?? basis.label}: ${windowLabel ? "Stored rule result: " : ""}${formatClassification(basis.classification)}. ${basis.short}. ${inputs ? `Inputs: ${inputs}. ` : ""}${basis.observation_date ? `All inputs end at observation period ${basis.observation_date}; feature as-of ${basis.feature_as_of_date}. ` : ""}Rule: ${basis.rule}${votes}`;
}
export function timestamp(instant: string): string {
  return `${new Intl.DateTimeFormat(getLanguage() === "pl" ? "pl-PL" : "en-GB", { timeZone: "Europe/Warsaw", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", timeZoneName: "short" }).format(new Date(instant))} (Europe/Warsaw; ${instant})`;
}
function period(day: string, frequency: string) { return `${formatObservationDate(day, frequency)} [${day}]`; }
function frequency(domain: string, key: string): string {
  if (key === "initial_claims" || key === "continuing_claims" || key === "mortgage_rate" || key === "nfci") return "weekly";
  if (key === "real_gdp" || key === "employment_cost_index") return "quarterly";
  if (domain === "financial_conditions") return "daily";
  return "monthly";
}
export function readingText(reading: MacroStateReading | undefined, series: string, domain: string): string {
  if (!reading || !Number.isFinite(reading.value)) return `${reading?.label ?? series}: Unavailable (${series}).`;
  return `${reading.label}: ${formatNumber(reading.value, 2)} ${reading.unit} (${series}). Observation period: ${period(reading.observation_date, frequency(domain, reading.key))}. Feature as-of: ${reading.feature_as_of_date}. `.trim();
}
export function changeText(item: BriefComparison): string {
  if (!item.current) return `${item.label} (${item.series_id}, ${item.feature_name}): Unavailable. No finite stored reading.`;
  const current = `${formatNumber(item.current.value, 2)} ${item.unit} for ${period(item.current.observation_date, item.frequency)} (feature as-of ${item.current.feature_as_of_date})`;
  const previous = item.previous ? `${formatNumber(item.previous.value, 2)} ${item.unit} for ${period(item.previous.observation_date, item.frequency)} (feature as-of ${item.previous.feature_as_of_date})` : `Unavailable for expected period ${item.expected_previous_observation_date}`;
  const delta = item.change === null ? "Unavailable" : `${item.change > 0 ? "+" : ""}${formatNumber(item.change, 2)} ${item.change_unit}`;
  const trailing = item.latest_stored_observation_date && item.latest_stored_observation_date > item.current.observation_date ? ` Newer stored period ${item.latest_stored_observation_date} has no finite reading.` : "";
  return `${item.label} (${item.series_id}, ${item.feature_name}): ${current}; previous: ${previous}. ${item.change_type}: ${delta}.${trailing}`;
}
export function eventText(event: CalendarEvent): string {
  if(event.event_type?.startsWith('michigan_')||event.event_type==='adp_monthly')return `${event.release_name} - ${formatCalendarDate(event.release_date)} - ${formatPolandTime(event.release_datetime_utc)}. Survey month: ${event.reference_period??"Reference period unconfirmed"}. Stage: ${event.publication_stage}. Numerical integration: publisher permission required. Official reports: ${event.publisher_reports_url}.`;
  const known = event.release_datetime_utc && !Number.isNaN(new Date(event.release_datetime_utc).getTime());
  const day = known ? warsawDate(new Date(event.release_datetime_utc!)) : event.release_date;
  return `${event.release_name} - ${formatCalendarDate(day)} [${day}] - ${formatPolandTime(event.release_datetime_utc)}. ${formatClassification(event.importance)} importance. ${event.event_type === "fomc_decision" ? "Official Federal Reserve policy decision. " : ""}Covers: ${event.event_type?.startsWith('fomc_') ? "monetary policy" : event.series.length ? event.series.map((series) => `${series.short_name || series.name} (${series.series_id})`).join(", ") : "release description unavailable"}.`;
}
export const scopeNote = "Current-vintage snapshot and stored feature comparisons may contain revisions. Sections have different observation periods and feature as-of dates; they do not share one economic reference date.";
export const dateNote = "Observation period, publication date, vintage date and retrieval time are different. Feature as-of is computation metadata, not a verified publication date. These readings are not historical actual-at-release values. Snapshot as-of and assembly time are not publication dates.";
export const calendarNote = "Times shown in Poland local time (Europe/Warsaw). Macro release dates come from FRED with official publisher time conventions; FOMC decisions use the Federal Reserve schedule and explicitly confirmed times. FRED does not guarantee publication times. Stored schedules may change. No consensus, surprises or forecasts.";
export const mciNote = "Experimental descriptive index. PIT MCI reconstructs only its component vintages known at each historical month-end. Other brief sections remain current-vintage. The score is descriptive and is not validated to predict recessions or markets.";
export const aiInstruction = "Optional instruction for an external AI: Interpret only the supplied data, identify contradictions and limitations, separate facts from hypotheses, do not invent missing data, and do not generate trading signals.";

function comparisonSummary(item: BriefComparison): string {
  if (!item.current) return `${item.label}: reading unavailable.`;
  const current = `${displayValue(item.current.value, item.unit)} (${formatObservationDate(item.current.observation_date, item.frequency)})`;
  if (!item.previous || item.change === null) return `${item.label}: ${current}; previous period unavailable.`;
  return `${item.label}: ${current}, versus ${displayValue(item.previous.value, item.unit)} (${formatObservationDate(item.previous.observation_date, item.frequency)}); change ${item.change > 0 ? "+" : ""}${displayValue(item.change, item.change_unit)}.`;
}
function eventSummary(event: CalendarEvent): string {
  const known = event.release_datetime_utc && !Number.isNaN(new Date(event.release_datetime_utc).getTime());
  const day = known ? warsawDate(new Date(event.release_datetime_utc!)) : event.release_date;
  return `${event.release_name} - ${formatCalendarDate(day)}${known ? `, ${formatPolandTime(event.release_datetime_utc)}` : ""}`;
}
function synthesize(domains: Array<{ name: string; evidence: string[]; missing: boolean }>, crossCurrents: string[]): string {
  const available = domains.filter((domain) => domain.evidence.length);
  if (!available.length) return "A synthesis is unavailable because the domain assessments are missing. Available readings and calendar coverage are listed separately.";
  const clauses = available.map((domain) => {
    const selected = domain.name === "Financial Conditions" ? domain.evidence.slice(-2) : domain.evidence.slice(0, 2);
    return selected.map((text) => text.replace(/\.$/, "")).join(", ");
  });
  const sentences = [];
  for (let i = 0; i < clauses.length; i += 2) sentences.push(`${clauses.slice(i, i + 2).join("; ")}.`);
  const limited = domains.some((domain) => domain.missing);
  if (limited) sentences[0] = `Limited coverage (${available.length} of six domain assessments available): ${sentences[0]}`;
  if (sentences.length === 1) sentences.push("This covers only the available domain assessments, without an overall economy classification.");
  if (crossCurrents.length) sentences[sentences.length - 1] = sentences[sentences.length - 1].replace(/\.$/, "") + `; cross-current: ${crossCurrents[0].replace(/\.$/, "")}.`;
  return sentences.join(" ");
}

export function briefModel(data: EconomyBriefResponse, pit: PitState = { status: "unavailable" }, now = new Date()) {
  const domains = domainSelection.map((spec) => {
    const domain = data.state.data?.domains[spec.key];
    const evidence = domain?.evidence ?? [];
    const basis = data.classification_basis?.[spec.key] ?? [];
    const compact = spec.readings.map(([key, series]) => prepareReading(key, series,
      data.reading_comparisons?.data?.find((item) => item.domain === spec.key && item.component === key)));
    return { key: spec.key, name: spec.name, asOf: domain?.as_of_date ?? data.snapshot.data?.component_as_of_dates[spec.key] ?? "Unavailable",
      compact, freshnessIssues: compact.filter(reading => reading.raw?.latest_stored_observation_date && (!reading.raw.current || reading.raw.latest_stored_observation_date > reading.raw.current.observation_date)), basis: basis.map(basisText),
      assessmentNote: ["inflation", "growth", "consumer"].includes(spec.key) ? "Momentum compares recent growth with annual growth, not consecutive readings." : spec.key === "labor" ? "Momentum uses multi-month and multi-week comparisons." : spec.key === "housing" ? "Directions describe monthly activity changes and the 4-week mortgage-rate change." : "NFCI level and 4-week direction describe different measures.",
      summary: evidence.slice(0, 2).join(" ") || "Interpretation unavailable; no replacement classification was generated.", evidence,
      indicatorHref: `#/explore/indicators/${spec.key === "consumer" ? "RSAFS" : spec.readings[0][1]}`,
      readings: detailReadings(spec).filter(([key]) => !["job_openings", "average_hourly_earnings", "producer_ppi", "manufacturing_pmi", "services_pmi"].includes(key)).filter(([key]) => spec.readings.some(([selected]) => selected === key) || domain?.readings.some((reading) => reading.key === key)).map(([key, series]) => readingText(domain?.readings.find((reading) => reading.key === key), series, spec.key)),
      missing: !domain || spec.readings.filter(([key]) => !["producer_ppi", "manufacturing_pmi", "services_pmi"].includes(key)).some(([key]) => !Number.isFinite(domain.readings.find((reading) => reading.key === key)?.value)) };
  });
  const changes = data.changes.status === "ready" && data.changes.data ? data.changes.data.map(changeText) : ["Reading comparisons unavailable."];
  const events = data.calendar.status === "ready" && data.calendar.data ? groupCalendarEvents(data.calendar.data.events).flatMap((group) => group.events) : [];
  const calendar = data.calendar.status !== "ready" || !data.calendar.data ? ["Release calendar unavailable; upcoming coverage is unknown."] : events.length ? events.map(eventText) : ["No tracked releases in the next 7 days in the stored calendar. This does not establish that no economic publications exist."];
  const row = pit.status === "ready" ? pit.data.observations[pit.data.observations.length - 1] : undefined;
  const mci = row ? `Point-in-time MCI: ${row.mci === null ? "Unavailable (missing components)" : `${formatNumber(row.mci, 2)} / 100`}. As-of month-end: ${row.observation_date}. Mode: point_in_time. History assembled as-of: ${pit.data?.as_of_date}.` : `Point-in-time MCI: ${pit.status === "loading" ? "Loading; not yet included" : "Unavailable"}.`;
  const crossCurrents = data.state.data?.cross_currents.map((item) => `${data.state.data!.domains[item.domain]?.name ?? item.domain}: ${item.summary} Evidence: ${item.evidence.map((entry) => `${entry.label}: ${formatClassification(entry.classification)}`).join("; ")}.`) ?? [];
  const missing = [!data.snapshot.data && "USA Economy Now unavailable", !data.state.data && "Macro State unavailable",
    domains.some((domain) => domain.compact.some((reading) => !reading.raw?.current)) && "Some domain readings unavailable", data.reading_comparisons?.status !== "ready" && "Reading comparisons unavailable",
    data.changes.data?.some((item) => item.change === null) && "Some prior-period comparisons unavailable", data.calendar.status !== "ready" && "Calendar unavailable",
    row?.mci === null && "PIT MCI score unavailable"].filter(Boolean) as string[];
  const completeness = missing.length ? `Partial brief - ${missing.join("; ")}.` : "All selected sections are available. This describes completeness, not how recent the observations are.";
  const lowGroups = new Map<string, CalendarEvent[]>();
  for (const event of events.filter((event) => event.importance === "low")) {
    const key = `${event.release_id}|${event.release_name}`;
    lowGroups.set(key, [...(lowGroups.get(key) ?? []), event]);
  }
  const repeated = [...lowGroups.values()].filter((group) => group.length > 1);
  const grouped = new Set(repeated.flat());
  const policyData = data.policy?.data;
  const nextDecision = policyData?.next_decision;
  const policy = {
    headline: nextDecision ? `${formatCalendarDate(nextDecision.release_date)} - ${formatPolandTime(nextDecision.release_datetime_utc)}` : "Next FOMC decision unavailable in the stored schedule.",
    status: policyData?.schedule_status ?? "unavailable",
    sourceUrl: policyData?.source_url ?? "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    fedwatchUrl: policyData?.market_probabilities.source_url ?? "https://www.cmegroup.com/fedwatch",
    metadata: nextDecision ? `Meeting dates: ${nextDecision.meeting_start_date} through ${nextDecision.meeting_end_date}. Schedule retrieved: ${nextDecision.retrieved_at}. Source time: ${nextDecision.release_time ?? "Time unavailable"}; source timezone: ${nextDecision.source_timezone ?? "Unavailable"}; UTC: ${nextDecision.release_datetime_utc ?? "Unavailable"}.` : `Schedule status: ${policyData?.schedule_status ?? "unavailable"}. Schedule retrieved: ${policyData?.retrieved_at ?? "Unavailable"}.`,
    timeSourceUrl: nextDecision?.time_source_url,
    note: "Market probabilities are not integrated. View the provider's probabilities and methodology on CME FedWatch.",
  };
  return { upcoming: overviewUpcomingEvents(data, now), domains, changes, calendar, mci, crossCurrents, completeness, policy, fedTarget: prepareFedTarget(data.fed_target),
    synthesis: synthesize(domains, data.state.data?.cross_currents.map((item) => item.summary) ?? []),
    mciHeadline: row ? `Point-in-time MCI: ${row.mci === null ? "Unavailable" : `${formatNumber(row.mci)} / 100`} - ${formatObservationDate(row.observation_date, "monthly")}` : mci,
    changeSummaries: data.changes.data?.map(comparisonSummary) ?? ["Reading comparisons unavailable."],
    calendarItems: events.filter((event) => !grouped.has(event)).map(eventSummary),
    calendarGroups: repeated.map((group) => ({ name: group[0].release_name, summary: `${group[0].release_name} - ${group.length} ${getLanguage() === "pl" ? new Intl.PluralRules("pl").select(group.length) === "few" ? "publikacje" : "publikacji" : "publications"}`, dates: group.map((event) => formatCalendarDate(event.release_date)).join("; "), events: group.map(eventSummary) })),
    crossCurrentStatus: data.state.status !== "ready" ? "Cross-currents unavailable." : "No curated cross-currents match the current classifications.",
    sources: ["MacroLens USA Economy Now and Macro State: existing deterministic classifications and evidence; no additional composite or causal model.",
      "FOMC decisions: official Federal Reserve meeting and monthly calendars; stored retrieval timestamp.",
      "FRED-sourced series and MacroLens v1 stored features (current-vintage).", "Macro Calendar: stored FRED release dates and official-source time metadata.", "PIT MCI: ALFRED vintages; date-level availability, not intraday."],
    links: [...new Set(["UNEMPLOY", ...domainSelection.flatMap((domain) => detailReadings(domain).flatMap(([, ids]) => ids.split(" / ")))])].map((id) => ({ label: id, url: data.reading_comparisons?.data?.find(r => r.series_id === id)?.source_url ?? (id.startsWith("ISM_") ? "https://www.ismworld.org/" : `https://fred.stlouisfed.org/series/${id}`) })),
    eventLinks: [...new Map(events.filter((event) => event.source_link).map((event) => [event.source_link!, { label: event.release_name, url: event.source_link! }])).values()] };
}
export type BriefModel = ReturnType<typeof briefModel>;
function pitReady(model: BriefModel): boolean { return model.mci.includes("Mode: point_in_time"); }
function prose(text: string): string { return text.replace(/\r?\n/g, " ").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
export function briefMarkdown(model: BriefModel, data: EconomyBriefResponse, generatedAt: string): string {
  const list = (items: string[]) => items.map((text) => `- ${prose(text)}`).join("\n");
  const availability=availabilityPresentation(data.source_checks,data.refresh,data.automatic_refresh_supported===false);
  const checkLine=availability?`${availability.label}${availability.at?` ${availabilityTime(availability.at)}`:""}`:"";
  const blocks = ["# MacroLens - Economy Brief", `Prepared: ${shortTimestamp(generatedAt)} (Europe/Warsaw)`, checkLine,
    "Current-vintage readings; earlier values may include revisions. Observation periods are shown with each value.",
    ...model.domains.flatMap((domain) => [`## ${domain.name}`, list([...(domain.key === "financial_conditions" ? [fedTargetReportLine(model.fedTarget)] : []), ...domain.compact.map(readingReportLine), ...domain.freshnessIssues.map(reading => `${reading.label}: Newer stored period ${reading.raw!.latest_stored_observation_date} has no available reading.`)])]),
    "## Key upcoming events", `Stored-calendar window: ${data.calendar_start_date} through ${data.calendar_end_date} (7 calendar days, including today).`,
    "Editorial priorities for MacroLens, not a forecast of market impact. Times shown in Europe/Warsaw.",
    model.upcoming.selected.length ? list(model.upcoming.selected.map(upcomingEventReport)) : model.upcoming.available ? "No key upcoming events in the stored 7-day window." : "Release calendar unavailable; upcoming coverage is unknown.",
    ...(model.upcoming.remaining.length ? ["### Other events this week", list(model.upcoming.remaining.map(upcomingEventReport))] : []),
    ...(model.upcoming.nextFomc ? ["## Next FOMC decision", upcomingEventReport(model.upcoming.nextFomc)] : []),
    model.policy.note, `[View market probabilities on CME FedWatch](${model.policy.fedwatchUrl})`,
    "## Sources and limitations", list(model.sources),
    "CME probabilities are not integrated. ISM PMI uses locally imported release tables; public display/export rights require verification. This is not a full PMI PIT history.",
    "No live news, causal attribution, forecasts or trading recommendations. Missing sections and periods are not imputed. Stored data may lag publication and revisions may alter the current-vintage comparisons.",
    "## Audit details", "### Data availability check", list(availabilityReportDetails(data)), "### Dates, scope and freshness", `Report generated: ${timestamp(generatedAt)}`, `Data assembled: ${timestamp(data.assembled_at)}`,
    `Current snapshot as-of: ${data.snapshot.data?.as_of_date ?? "Unavailable"}.`, scopeNote, dateNote,
    "Observation periods and classification input windows are shown below. Snapshot and calculation metadata are not publication dates. No uniform stale-data threshold is applied.",
    ...model.domains.flatMap((domain) => [`### ${domain.name} - readings and assessment basis`, `Snapshot as-of: ${domain.asOf}.`, list(domain.readings),
      domain.basis.length ? list(domain.basis) : "Classification inputs unavailable; no substitute assessment was generated.",
      domain.evidence.length ? list(domain.evidence) : "Evidence unavailable."]),
    "Seasonally adjusted annualized housing rates are not actual starts or permits within one month.",
    "### Comparison details", list(model.domains.flatMap((domain) => domain.compact.map((reading) => {
      const raw = reading.raw;
      if (!raw) return `${reading.label}: comparison history unavailable.`;
      const point = (value: typeof raw.current) => value ? `${formatNumber(value.value, 6)} ${raw.unit}, observation date ${value.observation_date}, feature as-of ${value.feature_as_of_date ?? "not applicable (raw observation)"}${value.document_published_at ? `; document published ${value.document_published_at}; retrieved ${value.retrieved_at}; RAW SHA-256 ${value.raw_hash}; document source ${value.source_url}. Publication date belongs to the document, not necessarily the first release of this observation` : ""}` : "Unavailable";
      return `${raw.label} (${raw.series_id}, ${raw.feature_name}): latest ${point(raw.current)}; previous ${point(raw.previous)}; three periods earlier ${point(raw.three_periods_ago)}. Expected previous period: ${raw.expected_previous_observation_date ?? "Unavailable"}; expected earlier period: ${raw.expected_three_periods_ago_date ?? "Unavailable"}. ${raw.change_type}: ${raw.change === null ? "Unavailable" : `${formatNumber(raw.change, 6)} ${raw.change_unit}`}. Latest stored observation period: ${raw.latest_stored_observation_date ?? "Unavailable"}.${raw.context_yoy ? ` YoY context: ${JSON.stringify(raw.context_yoy)}.` : ""}${raw.context_moving_average_4w ? ` Same-week 4W average: ${JSON.stringify(raw.context_moving_average_4w)} claims.` : ""}`;
    }))),
    "### Existing assessment evidence", model.synthesis, model.crossCurrents.length ? list(model.crossCurrents) : model.crossCurrentStatus,
    "### Full release details", calendarNote, eventImportanceNote, list(model.calendar),
    "### FOMC schedule provenance", model.policy.metadata, "Stored schedules may change. Refresh is separate from page loading.",
    ...(pitReady(model) ? ["### Supporting MCI", model.mci, mciNote] : []),
    "### Fed target range provenance", model.fedTarget.raw ? JSON.stringify(model.fedTarget.raw) : "Fed target range unavailable.",
    "### Source links",
    [...model.links, ...model.eventLinks, ...model.fedTarget.sources.map(source => ({ label: source.series_id, url: source.url })),
      { label: "Official Federal Reserve FOMC calendar", url: model.policy.sourceUrl },
      ...(model.policy.timeSourceUrl ? [{ label: "Official FOMC time source", url: model.policy.timeSourceUrl }] : [])]
      .filter((link, index, links) => links.findIndex((other) => other.url === link.url) === index)
      .map((link) => `- [${link.label.replace(/\]/g, "\\]")}](${link.url})`).join("\n"),
    "## Optional external AI instruction", aiInstruction];
  let report = blocks.filter(Boolean).join("\n\n") + "\n";
  for (const [from,to] of Object.entries({
    "Real GDP momentum is accelerating.":"Real GDP: quarterly annualized growth is above year-over-year growth.",
    "Real GDP momentum is decelerating.":"Real GDP: quarterly annualized growth is below year-over-year growth.",
    "Real GDP momentum is stable.":"Real GDP: quarterly annualized growth equals year-over-year growth.",
    "Initial claims momentum is improving.":"Initial claims: the 4-week average is below the 13-week average.",
    "Initial claims momentum is weakening.":"Initial claims: the 4-week average is above the 13-week average.",
    "Initial claims momentum is stable.":"Initial claims: the 4-week average equals the 13-week average.",
    "Continuing claims momentum is improving.":"Continuing claims: the 4-week average is below the 13-week average.",
    "Continuing claims momentum is weakening.":"Continuing claims: the 4-week average is above the 13-week average.",
    "Continuing claims momentum is stable.":"Continuing claims: the 4-week average equals the 13-week average.",
  })) report = report.split(from).join(to);
  return t(report);
}
