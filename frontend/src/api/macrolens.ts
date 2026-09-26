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

export interface SeriesMetadata {
  series_id: string;
  name: string;
  short_name: string;
  category: string;
  frequency: string;
  unit: string;
}

export interface SeriesCatalogResponse {
  series: SeriesMetadata[];
}

export interface SeriesFeaturesResponse {
  series_id: string;
  methodology_version: string;
  features: string[];
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

function historyQuery({ startDate, endDate }: HistoryOptions): string {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  return params.size ? `?${params}` : "";
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
