export type ChartDomain = "labor" | "inflation" | "growth" | "consumer" | "housing" | "financial";
export type ChartUnit = "percent" | "thousands" | "count" | "saar" | "index" | "spread" | "payrollChange";

export interface ChartSeries {
  id: string;
  label: string;
  color: string;
  seriesId?: string;
  featureName?: string;
  derived?: "2s10s";
}

export interface ChartDefinition {
  id: string;
  domain: ChartDomain;
  title: string;
  description: string;
  unit: ChartUnit;
  frequency: "monthly" | "quarterly" | "weekly" | "daily";
  series: ChartSeries[];
  referenceLine?: number;
}

export const chartDomains: Array<{ id: ChartDomain; label: string }> = [
  { id: "labor", label: "Labor" },
  { id: "inflation", label: "Inflation" },
  { id: "growth", label: "Growth" },
  { id: "consumer", label: "Consumer" },
  { id: "housing", label: "Housing" },
  { id: "financial", label: "Financial Conditions" },
];

const blue = "#83a9d5";
const amber = "#d9af75";
const violet = "#b6a2d8";

export const chartDefinitions: ChartDefinition[] = [
  { id: "unemployment-rate", domain: "labor", title: "Unemployment Rate", description: "Share of the labor force unemployed, seasonally adjusted.", unit: "percent", frequency: "monthly", series: [{ id: "rate", label: "Unemployment rate", color: blue, seriesId: "UNRATE", featureName: "level" }] },
  { id: "unemployment-level", domain: "labor", title: "Unemployment Level", description: "Number of unemployed people; source values are in thousands.", unit: "thousands", frequency: "monthly", series: [{ id: "level", label: "Unemployed people", color: violet, seriesId: "UNEMPLOY" }] },
  { id: "payrolls", domain: "labor", title: "Payrolls: Monthly Change", description: "Monthly change in total nonfarm payroll employment, in thousands of jobs.", unit: "payrollChange", frequency: "monthly", series: [{ id: "change", label: "Monthly payroll change", color: blue, seriesId: "PAYEMS", featureName: "monthly_change" }] },
  { id: "initial-claims", domain: "labor", title: "Initial Jobless Claims", description: "Four-week moving average of weekly initial claims for unemployment insurance.", unit: "count", frequency: "weekly", series: [{ id: "claims", label: "4-week average", color: amber, seriesId: "ICSA", featureName: "moving_average_4w" }] },
  { id: "cpi-yoy", domain: "inflation", title: "CPI Inflation YoY", description: "Headline and core consumer price inflation over the prior 12 months.", unit: "percent", frequency: "monthly", series: [{ id: "headline", label: "Headline CPI YoY", color: blue, seriesId: "CPIAUCSL", featureName: "yoy" }, { id: "core", label: "Core CPI YoY", color: amber, seriesId: "CPILFESL", featureName: "yoy" }] },
  { id: "pce-yoy", domain: "inflation", title: "PCE Inflation YoY", description: "Headline and core personal consumption expenditure price inflation over the prior 12 months.", unit: "percent", frequency: "monthly", series: [{ id: "headline", label: "Headline PCE YoY", color: blue, seriesId: "PCEPI", featureName: "yoy" }, { id: "core", label: "Core PCE YoY", color: amber, seriesId: "PCEPILFE", featureName: "yoy" }] },
  { id: "cpi-momentum", domain: "inflation", title: "Headline CPI Momentum", description: "Three-month annualized headline CPI growth alongside twelve-month CPI growth; both are existing computed features.", unit: "percent", frequency: "monthly", series: [{ id: "annualized", label: "3M annualized", color: violet, seriesId: "CPIAUCSL", featureName: "annualized_3m" }, { id: "yoy", label: "YoY", color: blue, seriesId: "CPIAUCSL", featureName: "yoy" }] },
  { id: "gdp-growth", domain: "growth", title: "Real GDP Growth", description: "Quarter-over-quarter annualized and year-over-year growth in real GDP.", unit: "percent", frequency: "quarterly", series: [{ id: "qoq", label: "QoQ annualized", color: blue, seriesId: "GDPC1", featureName: "qoq_annualized" }, { id: "yoy", label: "YoY", color: amber, seriesId: "GDPC1", featureName: "yoy" }] },
  { id: "cfnai", domain: "growth", title: "CFNAI: Three-Month Average", description: "Chicago Fed National Activity Index three-month average; zero represents trend growth.", unit: "index", frequency: "monthly", referenceLine: 0, series: [{ id: "cfnai", label: "3M average", color: violet, seriesId: "CFNAI", featureName: "moving_average_3m" }] },
  { id: "industrial-production", domain: "growth", title: "Industrial Production YoY", description: "Year-over-year growth in the industrial production index.", unit: "percent", frequency: "monthly", series: [{ id: "industrial", label: "Industrial production YoY", color: blue, seriesId: "INDPRO", featureName: "yoy" }] },
  { id: "capacity-utilization", domain: "growth", title: "Capacity Utilization", description: "Share of industrial productive capacity in use.", unit: "percent", frequency: "monthly", series: [{ id: "capacity", label: "Capacity utilization", color: amber, seriesId: "TCU", featureName: "level" }] },
  { id: "retail-sales", domain: "consumer", title: "Retail Sales YoY (Nominal)", description: "Year-over-year growth in nominal retail and food services sales; not adjusted for inflation.", unit: "percent", frequency: "monthly", series: [{ id: "retail", label: "Nominal retail sales YoY", color: blue, seriesId: "RSAFS", featureName: "yoy" }] },
  { id: "real-consumer", domain: "consumer", title: "Real Consumption and Income YoY", description: "Year-over-year growth in inflation-adjusted consumption and disposable personal income.", unit: "percent", frequency: "monthly", series: [{ id: "consumption", label: "Real consumption YoY", color: blue, seriesId: "PCEC96", featureName: "yoy" }, { id: "income", label: "Real disposable income YoY", color: amber, seriesId: "DSPIC96", featureName: "yoy" }] },
  { id: "saving-rate", domain: "consumer", title: "Personal Saving Rate", description: "Personal saving as a percentage of disposable personal income.", unit: "percent", frequency: "monthly", series: [{ id: "saving", label: "Saving rate", color: violet, seriesId: "PSAVERT", featureName: "level" }] },
  { id: "housing-starts", domain: "housing", title: "Housing Starts and Permits", description: "New housing starts and building permits, thousands of units at seasonally adjusted annual rates.", unit: "saar", frequency: "monthly", series: [{ id: "starts", label: "Housing starts", color: blue, seriesId: "HOUST", featureName: "level" }, { id: "permits", label: "Building permits", color: amber, seriesId: "PERMIT", featureName: "level" }] },
  { id: "home-sales", domain: "housing", title: "New Home Sales", description: "New single-family home sales, thousands of units at a seasonally adjusted annual rate.", unit: "saar", frequency: "monthly", series: [{ id: "sales", label: "New home sales", color: violet, seriesId: "HSN1F", featureName: "level" }] },
  { id: "mortgage-rate", domain: "housing", title: "30Y Mortgage Rate", description: "Average weekly rate on a 30-year fixed mortgage.", unit: "percent", frequency: "weekly", series: [{ id: "mortgage", label: "30Y mortgage rate", color: blue, seriesId: "MORTGAGE30US", featureName: "level" }] },
  { id: "treasury-yields", domain: "financial", title: "Treasury Yields", description: "Daily 2-year and 10-year nominal Treasury constant maturity yields.", unit: "percent", frequency: "daily", series: [{ id: "two", label: "2Y Treasury", color: blue, seriesId: "DGS2", featureName: "level" }, { id: "ten", label: "10Y Treasury", color: amber, seriesId: "DGS10", featureName: "level" }] },
  { id: "fed-funds", domain: "financial", title: "Effective Fed Funds Rate", description: "Daily effective federal funds rate.", unit: "percent", frequency: "daily", series: [{ id: "funds", label: "Effective fed funds", color: blue, seriesId: "DFF", featureName: "level" }] },
  { id: "real-yield", domain: "financial", title: "10Y Real Yield", description: "Daily yield on 10-year inflation-indexed Treasury securities.", unit: "percent", frequency: "daily", series: [{ id: "real", label: "10Y real yield", color: violet, seriesId: "DFII10", featureName: "level" }] },
  { id: "nfci", domain: "financial", title: "National Financial Conditions Index", description: "Chicago Fed NFCI; zero is its historical average.", unit: "index", frequency: "weekly", referenceLine: 0, series: [{ id: "nfci", label: "NFCI", color: amber, seriesId: "NFCI", featureName: "level" }] },
  { id: "yield-curve", domain: "financial", title: "2s10s Yield Curve Spread", description: "10-year Treasury yield minus the 2-year yield on matching observation dates, in percentage points.", unit: "spread", frequency: "daily", referenceLine: 0, series: [{ id: "spread", label: "10Y minus 2Y", color: blue, derived: "2s10s" }] },
];
