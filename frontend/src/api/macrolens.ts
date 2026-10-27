import { previousMonthEnd } from "../datePeriods";

export interface DatedComponent {
  observation_date: string;
  feature_as_of_date: string;
}

export interface LaborSnapshot {
  as_of_date: string;
  overall_momentum: string;
  payrolls: DatedComponent & {
    monthly_change: number;
    monthly_change_ma_3m: number;
    monthly_change_ma_6m: number;
    momentum: string;
  };
  unemployment: DatedComponent & {
    level: number;
    change_3m: number;
    momentum: string;
  };
  initial_claims: DatedComponent & {
    moving_average_4w: number;
    moving_average_13w: number;
    momentum: string;
  };
  continuing_claims: DatedComponent & {
    moving_average_4w: number;
    moving_average_13w: number;
    momentum: string;
  };
  job_openings: DatedComponent & {
    level: number;
    change_3m: number;
    yoy: number;
    direction: string;
  };
  labor_force_participation: DatedComponent & {
    level: number;
    change_3m: number;
    moving_average_3m: number;
    direction: string;
  };
  average_hourly_earnings: DatedComponent & {
    mom: number;
    yoy: number;
    annualized_3m: number;
  };
}

export interface InflationSnapshot {
  as_of_date: string;
  headline_cpi: DatedComponent & PriceMomentumComponent;
  core_cpi: DatedComponent & PriceMomentumComponent;
  headline_pce: DatedComponent & PriceMomentumComponent;
  core_pce: DatedComponent & PriceMomentumComponent;
  employment_cost_index: DatedComponent & {
    qoq: number;
    yoy: number;
  };
  average_hourly_earnings: DatedComponent & {
    mom: number;
    yoy: number;
    annualized_3m: number;
  };
}

export interface PriceMomentumComponent {
  mom: number;
  yoy: number;
  annualized_3m: number;
  momentum: string;
}

export interface GrowthSnapshot {
  as_of_date: string;
  real_gdp: DatedComponent & {
    qoq_annualized: number;
    yoy: number;
    momentum: string;
  };
  cfnai: DatedComponent & {
    level: number;
    moving_average_3m: number;
    position: string;
  };
  industrial_production: DatedComponent & PriceMomentumComponent;
  capacity_utilization: DatedComponent & {
    level: number;
    change_3m: number;
    moving_average_3m: number;
    direction: string;
  };
  durable_goods_orders: DatedComponent & {
    mom: number;
    yoy: number;
    moving_average_3m: number;
    latest_direction: string;
  };
}

export interface ConsumerSnapshot {
  as_of_date: string;
  retail_sales: DatedComponent & PriceMomentumComponent & {
    series_type: string;
  };
  real_consumption: DatedComponent & PriceMomentumComponent;
  real_disposable_income: DatedComponent & PriceMomentumComponent;
  saving_rate: DatedComponent & {
    level: number;
    change_3m: number;
    moving_average_3m: number;
    direction: string;
  };
}

export interface HousingSnapshot {
  as_of_date: string;
  housing_starts: DatedComponent & MonthlyHousingComponent;
  building_permits: DatedComponent & MonthlyHousingComponent;
  new_home_sales: DatedComponent & MonthlyHousingComponent;
  mortgage_rate: DatedComponent & {
    level: number;
    change_4w: number;
    change_13w: number;
    moving_average_4w: number;
    direction: string;
  };
}

export interface MonthlyHousingComponent {
  level: number;
  mom: number;
  yoy: number;
  moving_average_3m: number;
  direction: string;
}

export interface FinancialConditionsSnapshot {
  as_of_date: string;
  fed_funds_rate: DatedComponent & {
    level: number;
  };
  treasury_2y: DatedComponent & {
    level: number;
  };
  treasury_10y: DatedComponent & {
    level: number;
  };
  real_yield_10y: DatedComponent & {
    level: number;
  };
  yield_curve_2s10s: DatedComponent & {
    dgs2: number;
    dgs10: number;
    spread: number;
    shape: string;
  };
  nfci: DatedComponent & {
    level: number;
    change_4w: number;
    moving_average_4w: number;
    position: string;
    direction: string;
  };
}

export interface UsaEconomyNow {
  as_of_date: string;
  component_as_of_dates: {
    labor: string;
    inflation: string;
    growth: string;
    consumer: string;
    housing: string;
    financial_conditions: string;
  };
  labor: LaborSnapshot;
  inflation: InflationSnapshot;
  growth: GrowthSnapshot;
  consumer: ConsumerSnapshot;
  housing: HousingSnapshot;
  financial_conditions: FinancialConditionsSnapshot;
}

export interface MacroStateReading extends DatedComponent {
  key: string;
  label: string;
  value: number;
  unit: string;
  classification?: string;
}

export interface MacroStateDomain {
  name: string;
  as_of_date: string;
  readings: MacroStateReading[];
  classifications: Record<string, string>;
  evidence: string[];
}

export interface MacroStateResponse {
  as_of_date: string;
  component_as_of_dates: UsaEconomyNow["component_as_of_dates"];
  domains: Record<keyof UsaEconomyNow["component_as_of_dates"], MacroStateDomain>;
  cross_currents: Array<{
    domain: keyof UsaEconomyNow["component_as_of_dates"];
    summary: string;
    evidence: Array<{ label: string; classification: string }>;
  }>;
}

export type MciDomainKey = keyof UsaEconomyNow["component_as_of_dates"];

export interface MciComponent {
  key: string;
  label: string;
  series_id: string;
  features: string[];
  unit: string;
  orientation: "higher" | "lower" | "target_distance";
  rationale: string;
  weight: number;
  overall_weight: number;
  score: number | null;
  raw_value: number | null;
  domain_contribution: number | null;
  mci_contribution: number | null;
  status: "available" | "missing" | "insufficient_history" | "coverage_unverified";
  source_observation_date: string | null;
  effective_month: string | null;
  feature_as_of_date: string | null;
  inputs: Array<{ feature_name: string; value: number }>;
  carried_forward: boolean;
  reference_sample_size: number;
  reference_start_date: string | null;
  reference_end_date: string | null;
  vintage_dates_used?: string[];
  raw_observations_used?: Array<{ observation_date: string; vintage_date: string | null; value: number | null }>;
}

export interface MciDomain {
  name: string;
  score: number | null;
  weight: number;
  contribution: number | null;
  as_of_date: string | null;
  components: MciComponent[];
}

export type MciHistoryMode = "point_in_time" | "current_vintage";

export interface PitCoverage {
  first_valid_as_of_date: string | null;
  backfilled_through: string | null;
  missing_series: string[];
  series: Record<string, {
    first_vintage_date: string | null;
    first_observation_date: string | null;
    backfilled_through: string | null;
    stored_vintage_rows: number;
  }>;
}

export interface MciMethodology {
  methodology_version: "v1";
  history_type: MciHistoryMode;
  coverage?: PitCoverage;
  frequency: "monthly";
  as_of_date: string;
  domain_weights: Record<MciDomainKey, number>;
  normalization: {
    method: string;
    formula: string;
    lower_orientation: string;
    reference: string;
    minimum_monthly_samples: number;
    minimum_quarterly_samples: number;
    inflation_formula: string;
    inflation_reference_percent: number;
    inflation_zero_distance_pp: number;
  };
  alignment: { monthly_weekly: string; gdp: string; calendar: string };
  missing_data: string;
  current_selection: string;
  limitation: string;
}

export interface MciCurrentResponse extends MciMethodology {
  observation_date: string | null;
  latest_evaluated_month: string | null;
  mci: number | null;
  component_as_of_dates: Record<MciDomainKey, string | null>;
  domains: Record<MciDomainKey, MciDomain>;
}

export type MciHistoryObservation = {
  observation_date: string;
  mci: number | null;
} & Record<MciDomainKey, number | null>;

export interface MciHistoryResponse extends MciMethodology {
  start_date: string | null;
  end_date: string | null;
  observations: MciHistoryObservation[];
}

export interface HistoryObservation {
  observation_date: string;
  value: number | null;
  feature_as_of_date?: string;
}

export interface HistoryResponse {
  series_id: string;
  frequency?: string;
  history_type: "current_vintage";
  observations: HistoryObservation[];
}

export interface HistoryOptions {
  startDate?: string;
  endDate?: string;
  signal?: AbortSignal;
}

export type RelationshipKey = "left" | "right" | "third";

export interface RelationshipSource {
  seriesId: string;
  featureName?: string;
}

export interface RelationshipRequest extends HistoryOptions {
  left: RelationshipSource;
  right: RelationshipSource;
  third?: RelationshipSource;
}

export interface RelationshipIndicator {
  key: RelationshipKey;
  series_id: string;
  feature_name: string | null;
  name: string;
  short_name: string | null;
  frequency: string;
  unit: string;
  source_kind?: "macro" | "asset";
  source_url?: string;
  attribution?: string;
  excluded_observation_count?: number;
}

export interface RelationshipReading {
  observation_date: string;
  value: number;
  normalized_value: number | null;
}

export interface RelationshipObservation {
  period: string;
  left: RelationshipReading | null;
  right: RelationshipReading | null;
  third?: RelationshipReading | null;
}

export interface RelationshipComparison {
  left_key: RelationshipKey;
  right_key: RelationshipKey;
  overlapping_observation_count: number;
  correlation: number | null;
  first_pair_period?: string | null;
  last_pair_period?: string | null;
}

export interface RelationshipCatalogSource extends SeriesMetadata {
  source_kind: "macro" | "asset";
  features: string[];
  source_url?: string;
  attribution?: string;
}
export interface RelationshipCatalogResponse { sources: RelationshipCatalogSource[]; history_type: "current_vintage"; feature_policy: string }
export interface RelationshipResponse {
  indexing?: { available: boolean; reason: string | null };
  feature_policy?: string;
  history_type: "current_vintage";
  start_date: string | null;
  end_date: string | null;
  comparison_frequency: "daily" | "weekly" | "monthly" | "quarterly";
  alignment_methodology: string;
  normalization_base_period: string | null;
  indicators: RelationshipIndicator[];
  observations: RelationshipObservation[];
  overlapping_observation_count: number;
  correlation: number | null;
  comparisons: RelationshipComparison[];
}

export interface SeriesMetadata {
  series_id: string;
  name: string;
  short_name: string;
  category: string;
  frequency: string;
  unit: string;
  description?: string;
  source?: string; source_url?: string; attribution?: string;
}

export interface SeriesCatalogResponse {
  series: SeriesMetadata[];
}

export interface SeriesFeaturesResponse {
  series_id: string;
  methodology_version: string;
  features: string[];
}

export interface CalendarMeasure {
 series_id:string;label:string;feature_name:string;frequency:string;unit:string;definition?:string;
 reference_period:string|null;previous_period:string|null;previous_kind:"previous_period"|"previous_estimate"|"previous_decision";
 actual:number|null;previous:number|null;forecast:number|null;consensus_status:"not_integrated"|"available";
 previous_data_version?:"stored_date_vintage"|"current_vintage"|"official_release"|null;data_version:"stored_date_vintage"|"current_vintage"|"official_release"|null;revision_confirmed:boolean;binding_method:string|null;
 vintage_date:string|null;realtime_end:string|null;result_status:"available"|"scheduled"|"awaiting_data";mapping_status:string;source_url:string;
 actual_range?:[number,number]|null;previous_range?:[number,number]|null;
 effective_date?:string|null;previous_effective_date?:string|null;
 period_provenance?:{source_url:string;reference_period:string;binding_method:string;retrieved_at?:string;estimate_stage?:string;source_check?:{status:string;source_url:string;error_code?:string}|null}|null;
 actual_provenance?:Record<string,unknown>|null;previous_provenance?:Record<string,unknown>|null;
 result_provenance?:{source_url:string;release_date:string;reference_period:string;estimate_stage?:string;retrieved_at?:string}|null;
 publication_provenance?:{source_url:string;release_date:string;reference_period:string;estimate_stage?:string;retrieved_at?:string}|null;
 missing_reason?:{actual:string|null;previous:string|null};
 period_status_reason?:string|null;
}
export interface CalendarCheck {
 status:"complete"|"partial"|"error"|"not_recorded";checked_at:string|null;start_date:string;end_date:string;
 required_resources:string[];sources:Array<{resource:string;label:string;range_status:string;checked_at:string|null;error_code:string|null;scope_error?:string;missing_times?:string[];later_missing_times?:string[]}>;
}
export interface CalendarEvent {
  release_id: number | null;
  event_id?: string;
  description?:string;
  measures?:CalendarMeasure[];
  expects_numeric_result?:boolean;
  event_type?: "fomc_decision";
  meeting_start_date?: string;
  meeting_end_date?: string;
  retrieved_at?: string;
  time_source_url?: string | null;
  time_rule?:{source_url:string;source_timezone:string;valid_from:string;valid_through:string;time:string};
  release_name: string;
  release_date: string;
  release_time: string | null;
  source_timezone: string | null;
  release_datetime_utc: string | null;
  importance: "high" | "medium" | "low";
  source_link: string | null;
  date_precision: "date";
  series: SeriesMetadata[];
}

export interface CalendarResponse {
  automatic_refresh_supported?:boolean;data_revision?:string;refresh?:OverviewRefreshState;check?:CalendarCheck;max_range_days?:number;
  policy_calendar?: { status: string; retrieved_at: string | null; source_url: string };
  start_date: string;
  end_date: string;
  category: string | null;
  events: CalendarEvent[];
}

export interface ReleaseDetailResponse {
  release_id: number;
  release_name: string;
  source_link: string | null;
  press_release: boolean | null;
  date_precision: "date";
  series: SeriesMetadata[];
  recent_dates: string[];
}

export const dashboardHistoryRequests = {
  unemploymentRate: { seriesId: "UNRATE", featureName: "level" },
  unemploymentLevel: { seriesId: "UNEMPLOY" },
  payrollLevel: { seriesId: "PAYEMS" },
  initialClaimsLevel: { seriesId: "ICSA" },
  continuingClaimsLevel: { seriesId: "CCSA" },
  jobOpeningsLevel: { seriesId: "JTSJOL", featureName: "level" },
  participationLevel: { seriesId: "CIVPART", featureName: "level" },
  earningsYoy: { seriesId: "CES0500000003", featureName: "yoy" },
  headlineCpiYoy: { seriesId: "CPIAUCSL", featureName: "yoy" },
  coreCpiYoy: { seriesId: "CPILFESL", featureName: "yoy" },
  headlinePceYoy: { seriesId: "PCEPI", featureName: "yoy" },
  corePceYoy: { seriesId: "PCEPILFE", featureName: "yoy" },
  eciYoy: { seriesId: "ECIALLCIV", featureName: "yoy" },
  realGdpQoq: { seriesId: "GDPC1", featureName: "qoq_annualized" },
  realGdpYoy: { seriesId: "GDPC1", featureName: "yoy" },
  cfnaiLevel: { seriesId: "CFNAI", featureName: "level" },
  industrialYoy: { seriesId: "INDPRO", featureName: "yoy" },
  capacityLevel: { seriesId: "TCU", featureName: "level" },
  durableGoodsYoy: { seriesId: "DGORDER", featureName: "yoy" },
  retailYoy: { seriesId: "RSAFS", featureName: "yoy" },
  consumptionYoy: { seriesId: "PCEC96", featureName: "yoy" },
  disposableIncomeYoy: { seriesId: "DSPIC96", featureName: "yoy" },
  savingRate: { seriesId: "PSAVERT", featureName: "level" },
  housingStartsLevel: { seriesId: "HOUST", featureName: "level" },
  buildingPermitsLevel: { seriesId: "PERMIT", featureName: "level" },
  newHomeSalesLevel: { seriesId: "HSN1F", featureName: "level" },
  mortgageRate: { seriesId: "MORTGAGE30US", featureName: "level" },
  fedFunds: { seriesId: "DFF", featureName: "level" },
  treasury2y: { seriesId: "DGS2", featureName: "level" },
  treasury10y: { seriesId: "DGS10", featureName: "level" },
  realYield10y: { seriesId: "DFII10", featureName: "level" },
  nfciLevel: { seriesId: "NFCI", featureName: "level" },
} as const;

export type DashboardHistoryKey = keyof typeof dashboardHistoryRequests;
export type DashboardHistory = Partial<Record<DashboardHistoryKey, HistoryResponse>>;

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

export async function fetchSeriesCatalog(signal?: AbortSignal): Promise<SeriesCatalogResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/series`, { signal });
  if (!response.ok) throw new Error("Unable to load indicator catalog.");
  return response.json();
}

export async function fetchSeriesFeatures(seriesId: string, signal?: AbortSignal): Promise<SeriesFeaturesResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/series/${encodeURIComponent(seriesId)}/features`, { signal });
  if (!response.ok) throw new Error(`Unable to load features for ${seriesId}.`);
  return response.json();
}

export async function fetchCalendar(
  startDate: string,
  endDate: string,
  category?: string,
  signal?: AbortSignal,
): Promise<CalendarResponse> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  if (category) params.set("category", category);
  const response = await fetch(`${API_BASE_URL}/api/v1/calendar?${params}`, { signal });
  if (!response.ok) throw new Error("Unable to load macro calendar.");
  return response.json();
}

export async function fetchReleaseDetail(releaseId: number, signal?: AbortSignal): Promise<ReleaseDetailResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/releases/${releaseId}`, { signal });
  if (!response.ok) throw new Error(`Unable to load release ${releaseId}.`);
  return response.json();
}

export async function fetchRelationshipSources(signal?: AbortSignal): Promise<RelationshipCatalogResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/relationships/sources`, { signal });
  if (!response.ok) throw new Error("Unable to load configured relationship sources.");
  return response.json();
}

export async function fetchRelationshipComparison(request: RelationshipRequest): Promise<RelationshipResponse> {
  const params = new URLSearchParams({ left_series: request.left.seriesId, right_series: request.right.seriesId });
  if (request.left.featureName) params.set("left_feature", request.left.featureName);
  if (request.right.featureName) params.set("right_feature", request.right.featureName);
  if (request.third) {
    params.set("third_series", request.third.seriesId);
    if (request.third.featureName) params.set("third_feature", request.third.featureName);
  }
  if (request.startDate) params.set("start_date", request.startDate);
  if (request.endDate) params.set("end_date", request.endDate);
  const response = await fetch(`${API_BASE_URL}/api/v1/relationships/compare?${params}`, { signal: request.signal });
  if (!response.ok) throw new Error("Unable to compare indicator histories.");
  return response.json();
}

function historyQuery({ startDate, endDate }: HistoryOptions): string {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  return params.size ? `?${params}` : "";
}

export function pitMciAuditUrl(asOfDate: string): string {
  return `${API_BASE_URL}/api/v1/economy/us/mci/point-in-time/${encodeURIComponent(asOfDate)}`;
}

export async function fetchMciCurrent(signal?: AbortSignal, mode: MciHistoryMode = "current_vintage"): Promise<MciCurrentResponse> {
  const suffix = mode === "point_in_time" ? "/point-in-time" : "";
  const response = await fetch(`${API_BASE_URL}/api/v1/economy/us/mci${suffix}`, { signal });
  if (!response.ok) throw new Error("Unable to load Macro Conditions Index.");
  return response.json();
}

export async function fetchMciHistory(options: HistoryOptions = {}, mode: MciHistoryMode = "current_vintage"): Promise<MciHistoryResponse> {
  const suffix = mode === "point_in_time" ? "/point-in-time" : "";
  const response = await fetch(`${API_BASE_URL}/api/v1/economy/us/mci${suffix}/history${historyQuery({ ...options, endDate: options.endDate ?? (mode === "point_in_time" ? previousMonthEnd(new Date()) : undefined) })}`, { signal: options.signal });
  if (!response.ok) throw new Error("Unable to load Macro Conditions Index history.");
  return response.json();
}

export async function fetchMacroState(signal?: AbortSignal): Promise<MacroStateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/economy/us/state`, { signal });
  if (!response.ok) throw new Error("Unable to load Macro State.");
  return response.json();
}

export async function fetchUsaEconomyNow(): Promise<UsaEconomyNow> {
  const response = await fetch(`${API_BASE_URL}/api/v1/economy/us`);

  if (!response.ok) {
    throw new Error("Unable to load MacroLens current snapshot.");
  }

  return response.json();
}

export async function fetchFeatureHistory(
  seriesId: string,
  featureName: string,
  options: HistoryOptions = {},
): Promise<HistoryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/series/${encodeURIComponent(seriesId)}/features/${encodeURIComponent(featureName)}/history${historyQuery(options)}`,
    { signal: options.signal },
  );

  if (!response.ok) {
    throw new Error(`Unable to load history for ${seriesId} ${featureName}.`);
  }

  return response.json();
}

export async function fetchSeriesHistory(seriesId: string, options: HistoryOptions = {}): Promise<HistoryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/series/${encodeURIComponent(seriesId)}/history${historyQuery(options)}`,
    { signal: options.signal },
  );

  if (!response.ok) {
    throw new Error(`Unable to load observation history for ${seriesId}.`);
  }

  return response.json();
}

export async function fetchYieldCurveHistory(options: HistoryOptions = {}): Promise<HistoryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/analytics/yield-curve/2s10s/history${historyQuery(options)}`,
    { signal: options.signal },
  );
  if (!response.ok) throw new Error("Unable to load 2s10s yield curve history.");
  return response.json();
}

export async function fetchDashboardHistory(): Promise<DashboardHistory> {
  const entries = Object.entries(dashboardHistoryRequests) as Array<
    [DashboardHistoryKey, { readonly seriesId: string; readonly featureName?: string }]
  >;
  const results = await Promise.allSettled(
    entries.map(([, request]) =>
      request.featureName
        ? fetchFeatureHistory(request.seriesId, request.featureName)
        : fetchSeriesHistory(request.seriesId),
    ),
  );

  return entries.reduce<DashboardHistory>((history, [key], index) => {
    const result = results[index];
    if (result.status === "fulfilled" && Array.isArray(result.value.observations)) {
      history[key] = result.value;
    }
    return history;
  }, {});
}


export type MarketAssetId = "NASDAQCOM" | "CBBTCUSD";
export type MarketDisplayMode = "indexed" | "actual";
export interface MarketComparisonRow {
  as_of_date: string;
  mci: number | null;
  mci_change: number | null;
  [key: string]: number | string | null;
}
export interface MarketSeries {
  series_id: string; name: string; unit: string; source: string;
  source_organization?: string; source_url?: string; attribution?: string;
  price_convention?: string; asset_class?: string;
  first_observation: string | null; last_observation: string | null;
}
export interface MarketRelation {
  correlation: number | null; overlapping_observations: number;
  variable_definitions: { macro: string; market: string };
}
export interface MarketComparisonResponse {
  methodology_version: "v1"; macro_history_type: MciHistoryMode;
  market_history_type: string; frequency: "monthly"; alignment: string;
  mode: MarketDisplayMode; status: "ready" | "insufficient_overlap";
  base_date: string | null; base_values: Partial<Record<MarketAssetId, number>>;
  available_overlap_start: string | null; available_overlap_end: string | null;
  message: string | null; rows: MarketComparisonRow[]; series: MarketSeries[];
  statistics: Array<{ asset_id: MarketAssetId; mci: MarketRelation; mci_change: MarketRelation }>;
  minimum_correlation_observations: number; limitations: string;
}
export async function fetchMarketComparison(options: HistoryOptions & {
  assets: MarketAssetId[]; macroHistoryType: MciHistoryMode; mode: MarketDisplayMode;
}): Promise<MarketComparisonResponse> {
  const params = new URLSearchParams({ assets: options.assets.join(","),
    macro_history_type: options.macroHistoryType, mode: options.mode });
  if (options.startDate) params.set("start_date", options.startDate);
  // PIT research uses completed months; omit the unused partial month so the
  // existing history cache can serve the same monthly observations.
  const endDate = options.endDate ?? (options.macroHistoryType === "point_in_time" ? previousMonthEnd(new Date()) : undefined);
  if (endDate) params.set("end_date", endDate);
  const response = await fetch(`${API_BASE_URL}/api/v1/market-comparison?${params}`, { signal: options.signal });
  if (!response.ok) throw new Error("Unable to load market comparison.");
  return response.json();
}

export interface LeadLagPair {
  anchor_date: string; return_date: string; mci_change: number; asset_return: number;
  asset_id: MarketAssetId; asset_name: string;
  price_observation_date: string; previous_price_observation_date: string;
}
export interface LeadLagResult {
  lag: number; correlation: number | null; n: number;
  first_anchor_date: string | null; last_anchor_date: string | null;
  missing_anchor_count: number; pairs: LeadLagPair[];
  rolling: Array<{ anchor_date: string; valid_pairs: number; correlation: number | null }>;
}
export interface LeadLagResponse {
  macro_history_type: MciHistoryMode; lag_convention: string; rolling_window: number;
  maximum_price_age_days: number; anchor_count: number;
  assets: Array<{ asset_id: MarketAssetId; name: string; lags: LeadLagResult[]; missing_price_dates: string[] }>;
  coverage: { first_anchor_date: string | null; last_anchor_date: string | null; missing_mci_change_dates: string[] };
  boundary_policy: string; rolling_policy: string; limitations: string;
}
export async function fetchLeadLag(options: HistoryOptions & {
  asset: MarketAssetId; macroHistoryType: MciHistoryMode; rollingWindow: number;
}): Promise<LeadLagResponse> {
  const params = new URLSearchParams({ assets: options.asset, macro_history_type: options.macroHistoryType,
    rolling_window: String(options.rollingWindow) });
  if (options.startDate) params.set("start_date", options.startDate);
  // PIT research uses completed months; omit the unused partial month so the
  // existing history cache can serve the same monthly observations.
  const endDate = options.endDate ?? (options.macroHistoryType === "point_in_time" ? previousMonthEnd(new Date()) : undefined);
  if (endDate) params.set("end_date", endDate);
  const response = await fetch(`${API_BASE_URL}/api/v1/market-comparison/lead-lag?${params}`, { signal: options.signal });
  if (!response.ok) throw new Error("Unable to load lead/lag analysis.");
  return response.json();
}


export interface BriefSection<T> { status: "ready" | "unavailable"; data: T | null; error: string | null }
export interface BriefComparison {
  series_id: string; feature_name: string; label: string; frequency: string; unit: string;
  change_unit: string; change_type: string; change: number | null;
  expected_previous_observation_date: string | null; latest_stored_observation_date: string | null;
  current: { value: number; observation_date: string; feature_as_of_date: string | null; document_published_at?: string; source_url?: string; retrieved_at?: string; raw_hash?: string } | null;
  previous: { value: number; observation_date: string; feature_as_of_date: string | null; document_published_at?: string; source_url?: string; retrieved_at?: string; raw_hash?: string } | null;
}
export interface OverviewReadingComparison extends BriefComparison {
  domain: MciDomainKey; component: string; source_url?: string; attribution?: string;
  three_periods_ago: BriefComparison["current"];
  expected_three_periods_ago_date: string | null;
  context_moving_average_4w?: BriefComparison["current"];
  context_yoy?: { current: BriefComparison["current"]; previous: BriefComparison["current"]; three_periods_ago: BriefComparison["current"] } | null;
}
export interface BriefClassificationBasis {
  component: string; field: string; label: string; classification: string; rule: string; short: string;
  observation_date: string | null; feature_as_of_date: string | null;
  inputs: Array<{ feature_name: string; label: string; value: number; unit: string }>;
  component_classifications?: Record<string, string>;
}
export interface FedTargetRange {
  availability: "available" | "unavailable"; lower: number | null; upper: number | null;
  observation_date: string | null; effective_date: string | null; retrieved_at: string | null;
  last_rate_change: { effective_date: string; lower_change_bps: number; upper_change_bps: number; change_bps: number | null; previous_lower: number; previous_upper: number } | null;
  sources: Array<{ series_id: string; url: string; observation_date: string | null; retrieved_at: string | null }>;
}
export interface OverviewRefreshState {
  status: "idle" | "running" | "complete" | "partial" | "error";
  job_id?: string | null;
  publication_id?: string | null;
  attempted_at?: string | null;
  completed_at?: string | null;
  next_check_at?: string | null;
  results: Array<{resource:string;status:string;error_code?:string;outcome?:string;manual_import_available?:boolean;missing_times?:string[]}>;
}
export interface FomcTimeCheck { release_date:string;fetch_status:"success"|"error";http_status:number|null;time_status:"confirmed"|"unconfirmed" }
export interface EconomyBriefResponse {
  data_revision?: string;
  automatic_refresh_supported?: boolean;
  refresh?: OverviewRefreshState;
  source_checks?: {
    status_scope?: "overview";
    full_scope_status?: "complete" | "partial" | "not_recorded";
    fomc_schedule?: {source_check_status:string;completeness_status:string;overview_status:string;overview_dates:string[];displayed_missing_times:string[];future_missing_times:string[];fetch_error_dates:string[];time_checks:FomcTimeCheck[]};
    status: "complete" | "partial" | "not_recorded";
    checked_at: string | null;
    checked_count: number;
    metadata_status?: "available" | "unavailable";
    required_count: number;
    sources: Array<{
      resource: string; provider: string; label: string;
      status: "success" | "partial" | "error" | "running" | "not_recorded";
      last_attempt_at: string | null; last_success_at: string | null; last_finished_at?:string|null;
      overview_status?:string; overview_checked_at?:string|null; overview_error_code?:string|null;
      coverage_checked_at: string | null;
      successful_scope?: {start_date?: string;end_date?: string} | null;
      error_code: string | null;
      scope: {start_date?: string;end_date?: string;legacy_dates_only?: boolean;dates?:string[];missing_times?:string[];time_checks?:FomcTimeCheck[]};
    }>;
  };
  fed_target?: BriefSection<FedTargetRange>;
  reading_comparisons?: BriefSection<OverviewReadingComparison[]>;
  policy?: BriefSection<{ schedule_status: string; retrieved_at: string | null; source_url: string;
    next_decision: CalendarEvent | null; market_probabilities: { status: "not_integrated"; source_url: string } }>;
  classification_basis?: Partial<Record<MciDomainKey, BriefClassificationBasis[]>>;
  assembled_at: string; timezone: string; history_type: "current_vintage";
  snapshot: BriefSection<UsaEconomyNow>; state: BriefSection<MacroStateResponse>;
  changes: BriefSection<BriefComparison[]>; calendar: BriefSection<CalendarResponse>;
  calendar_start_date: string; calendar_end_date: string;
}
export async function fetchEconomyBrief(signal?: AbortSignal): Promise<EconomyBriefResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/economy/us/brief`, { signal });
  if (!response.ok) throw new Error("Economy Brief is unavailable.");
  return response.json();
}


export async function requestOverviewRefresh(signal?:AbortSignal,range?:{startDate:string;endDate:string}):Promise<OverviewRefreshState> {
  const query=range?`?${new URLSearchParams({calendar_start_date:range.startDate,calendar_end_date:range.endDate})}`:"";
  const response=await fetch(`${API_BASE_URL}/api/v1/economy/us/brief/refresh${query}`,{method:"POST",signal});
  if(!response.ok)throw new Error("Availability check unavailable.");
  return response.json();
}
export async function fetchOverviewRefresh(signal?:AbortSignal):Promise<OverviewRefreshState> {
  const response=await fetch(`${API_BASE_URL}/api/v1/economy/us/brief/refresh`,{signal});
  if(!response.ok)throw new Error("Availability check status unavailable.");
  return response.json();
}
export async function fetchBriefHistory(revision:string,key:string,options:HistoryOptions):Promise<HistoryResponse> {
  const params=new URLSearchParams({revision,key});
  if(options.startDate)params.set("start_date",options.startDate);
  if(options.endDate)params.set("end_date",options.endDate);
  const response=await fetch(`${API_BASE_URL}/api/v1/economy/us/brief/history?${params}`,{signal:options.signal});
  if(!response.ok)throw new Error("Published chart unavailable; reload Overview if its snapshot has expired.");
  return response.json();
}

export async function fetchCalendarAgenda(startDate:string,endDate:string,signal?:AbortSignal):Promise<CalendarResponse> {
 const params=new URLSearchParams({start_date:startDate,end_date:endDate,include_readings:"true"});
 const response=await fetch(`${API_BASE_URL}/api/v1/calendar?${params}`,{signal});
 if(!response.ok)throw new Error("Unable to load calendar.");
 return response.json();
}
