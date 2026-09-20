export interface MetricMetadata {
  label: string;
  description: string;
  methodology?: string;
}

export const metricMetadata = {
  laborOverall: {
    label: "Overall momentum",
    description: "Labor Market Momentum v1 combines Payrolls, Unemployment, and Initial Claims only.",
    methodology: "At least two improving components means Improving; at least two weakening means Weakening; otherwise Mixed.",
  },
  payrollMomentum: {
    label: "Payrolls momentum",
    description: "Compares the recent pace of monthly nonfarm payroll gains with its longer trend.",
    methodology: "The 3-month average payroll change is compared with the 6-month average: higher is Improving, lower is Weakening, and equal is Stable.",
  },
  unemploymentMomentum: {
    label: "Unemployment momentum",
    description: "Describes the direction of the unemployment rate over three observations.",
    methodology: "A negative 3-month change is Improving, a positive change is Weakening, and zero is Stable.",
  },
  initialClaimsMomentum: {
    label: "Initial claims momentum",
    description: "Compares short- and medium-term averages of initial jobless claims.",
    methodology: "A 4-week average below the 13-week average is Improving; above is Weakening; equal is Stable.",
  },
  headlineCpiYoy: {
    label: "Headline CPI YoY",
    description: "Twelve-month percentage change in the headline Consumer Price Index.",
  },
  headlineCpiMomentum: {
    label: "Headline CPI momentum",
    description: "Describes whether recent headline CPI inflation is accelerating or decelerating.",
    methodology: "Compares annualized 3-month inflation with YoY inflation; higher is Accelerating, lower is Decelerating, and equal is Stable.",
  },
  coreCpiYoy: {
    label: "Core CPI YoY",
    description: "Twelve-month percentage change in CPI excluding food and energy.",
  },
  coreCpiMomentum: {
    label: "Core CPI momentum",
    description: "Describes whether recent core CPI inflation is accelerating or decelerating.",
    methodology: "Compares annualized 3-month inflation with YoY inflation; higher is Accelerating, lower is Decelerating, and equal is Stable.",
  },
  corePceYoy: {
    label: "Core PCE YoY",
    description: "Twelve-month percentage change in the PCE price index excluding food and energy.",
  },
  corePceMomentum: {
    label: "Core PCE momentum",
    description: "Describes whether recent core PCE inflation is accelerating or decelerating.",
    methodology: "Compares annualized 3-month inflation with YoY inflation; higher is Accelerating, lower is Decelerating, and equal is Stable.",
  },
  realGdpQoq: {
    label: "Real GDP QoQ annualized",
    description: "Annualized percentage growth in real GDP from the previous quarter.",
    methodology: "Calculated as ((current / previous quarter)^4 - 1) × 100.",
  },
  realGdpMomentum: {
    label: "Real GDP momentum",
    description: "Compares recent annualized quarterly real GDP growth with annual growth.",
    methodology: "QoQ annualized above YoY is Accelerating, below is Decelerating, and equal is Stable.",
  },
  cfnaiPosition: {
    label: "CFNAI position",
    description: "The CFNAI 3-month average relative to its historical-trend reference of zero.",
    methodology: "Above zero is Above trend, below zero is Below trend, and zero is At trend. This is descriptive, not a recession classification.",
  },
  industrialMomentum: {
    label: "Industrial Production momentum",
    description: "Describes whether recent industrial-production growth is accelerating or decelerating.",
    methodology: "Compares annualized 3-month growth with YoY growth.",
  },
  capacityDirection: {
    label: "Capacity Utilization direction",
    description: "Direction of total capacity utilization over three observations.",
    methodology: "A positive 3-month change is Rising, a negative change is Falling, and zero is Stable.",
  },
  retailMomentum: {
    label: "Retail Sales momentum",
    description: "Momentum in nominal retail-sales growth; it is not a measure of real consumer strength.",
    methodology: "Compares annualized 3-month nominal growth with YoY nominal growth.",
  },
  retailYoy: {
    label: "Retail Sales YoY",
    description: "Twelve-month percentage change in nominal retail sales.",
  },
  consumptionMomentum: {
    label: "Real Consumption momentum",
    description: "Momentum in inflation-adjusted personal consumption growth.",
    methodology: "Compares annualized 3-month real growth with YoY real growth.",
  },
  consumptionYoy: {
    label: "Real Consumption YoY",
    description: "Twelve-month percentage change in real personal consumption expenditures.",
  },
  savingRate: {
    label: "Saving Rate",
    description: "Current personal saving rate as a percentage of disposable personal income.",
    methodology: "Direction uses the 3-month absolute change: positive is Rising, negative is Falling, and zero is Stable. No good/bad judgment is applied.",
  },
  housingStartsDirection: {
    label: "Housing Starts direction",
    description: "Latest direction of the published seasonally adjusted annual rate for housing starts.",
    methodology: "Direction is based on MoM percentage change: positive is Rising, negative is Falling, and zero is Stable.",
  },
  housingStartsYoy: {
    label: "Housing Starts YoY",
    description: "Twelve-month percentage change in the published housing-starts SAAR level.",
  },
  permitsDirection: {
    label: "Building Permits direction",
    description: "Latest direction of the published building-permits SAAR level.",
    methodology: "Direction is based on MoM percentage change: positive is Rising, negative is Falling, and zero is Stable.",
  },
  homeSalesDirection: {
    label: "New Home Sales direction",
    description: "Latest direction of the published new-home-sales SAAR level.",
    methodology: "Direction is based on MoM percentage change: positive is Rising, negative is Falling, and zero is Stable.",
  },
  mortgageRate: {
    label: "30Y Mortgage Rate",
    description: "Current average US 30-year fixed mortgage rate.",
  },
  mortgageDirection: {
    label: "Mortgage Rate direction",
    description: "Describes the mortgage rate's four-week direction without a good/bad judgment.",
    methodology: "The current rate minus the rate four weekly observations earlier is an absolute percentage-point change: positive is Rising, negative is Falling, and zero is Stable.",
  },
  fedFunds: {
    label: "Effective Fed Funds Rate",
    description: "Current effective federal funds rate; shown descriptively without policy inference.",
  },
  treasury2y: {
    label: "2Y Treasury",
    description: "Current 2-year US Treasury constant-maturity yield.",
  },
  treasury10y: {
    label: "10Y Treasury",
    description: "Current 10-year US Treasury constant-maturity yield.",
  },
  realYield10y: {
    label: "10Y Real Yield",
    description: "Current 10-year inflation-indexed US Treasury yield.",
  },
  curveSpread: {
    label: "2s10s spread",
    description: "The synchronized 10-year Treasury yield minus the 2-year Treasury yield, in percentage points.",
    methodology: "Inputs use the same observation date. No forward fill is used.",
  },
  curveShape: {
    label: "2s10s shape",
    description: "A purely mathematical description of the 2s10s spread, not a recession or trading signal.",
    methodology: "A spread above zero is Positive, below zero is Inverted, and zero is Flat.",
  },
  nfciLevel: {
    label: "NFCI level",
    description: "Chicago Fed National Financial Conditions Index level; zero represents its historical average.",
  },
  nfciPosition: {
    label: "NFCI position",
    description: "NFCI level relative to its historical-average reference of zero.",
    methodology: "Positive is Tighter than average, negative is Looser than average, and zero is Average.",
  },
  nfciDirection: {
    label: "NFCI direction",
    description: "Describes the four-week movement in financial conditions.",
    methodology: "A positive 4-week change is Tightening, a negative change is Easing, and zero is Stable. This is not a trading signal.",
  },
} satisfies Record<string, MetricMetadata>;

export type MetricKey = keyof typeof metricMetadata;
