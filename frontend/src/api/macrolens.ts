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
}

export interface InflationSnapshot {
  as_of_date: string;
  headline_cpi: DatedComponent & PriceMomentumComponent;
  core_cpi: DatedComponent & PriceMomentumComponent;
  core_pce: DatedComponent & PriceMomentumComponent;
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
}

export interface ConsumerSnapshot {
  as_of_date: string;
  retail_sales: DatedComponent & PriceMomentumComponent & {
    series_type: string;
  };
  real_consumption: DatedComponent & PriceMomentumComponent;
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

export const dashboardHistoryRequests = {
  headlineCpiYoy: ["CPIAUCSL", "yoy"],
  coreCpiYoy: ["CPILFESL", "yoy"],
  corePceYoy: ["PCEPILFE", "yoy"],
  realGdpQoq: ["GDPC1", "qoq_annualized"],
  retailYoy: ["RSAFS", "yoy"],
  consumptionYoy: ["PCEC96", "yoy"],
  savingRate: ["PSAVERT", "level"],
  housingStartsYoy: ["HOUST", "yoy"],
  mortgageRate: ["MORTGAGE30US", "level"],
  fedFunds: ["DFF", "level"],
  treasury2y: ["DGS2", "level"],
  treasury10y: ["DGS10", "level"],
  realYield10y: ["DFII10", "level"],
  nfciLevel: ["NFCI", "level"],
} as const;

export type DashboardHistoryKey = keyof typeof dashboardHistoryRequests;
export type DashboardHistory = Partial<Record<DashboardHistoryKey, HistoryResponse>>;

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

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
): Promise<HistoryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/series/${encodeURIComponent(seriesId)}/features/${encodeURIComponent(featureName)}/history`,
  );

  if (!response.ok) {
    throw new Error(`Unable to load history for ${seriesId} ${featureName}.`);
  }

  return response.json();
}

export async function fetchDashboardHistory(): Promise<DashboardHistory> {
  const entries = Object.entries(dashboardHistoryRequests) as Array<
    [DashboardHistoryKey, readonly [string, string]]
  >;
  const results = await Promise.allSettled(
    entries.map(([, [seriesId, featureName]]) =>
      fetchFeatureHistory(seriesId, featureName),
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
