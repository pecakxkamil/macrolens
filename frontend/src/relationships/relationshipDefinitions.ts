import type { RelationshipSource } from "../api/macrolens";

export interface RelationshipChoice extends RelationshipSource {
  id: string;
  label: string;
  domain: string;
}

export const relationshipChoices: RelationshipChoice[] = [
  { id: "UNRATE:raw", label: "Unemployment Rate", domain: "Labor", seriesId: "UNRATE" },
  { id: "PAYEMS:monthly_change", label: "Nonfarm Payrolls monthly change", domain: "Labor", seriesId: "PAYEMS", featureName: "monthly_change" },
  { id: "ICSA:moving_average_4w", label: "Initial Claims (4W average)", domain: "Labor", seriesId: "ICSA", featureName: "moving_average_4w" },
  { id: "JTSJOL:raw", label: "Job Openings", domain: "Labor", seriesId: "JTSJOL" },
  { id: "CPIAUCSL:yoy", label: "Headline CPI YoY", domain: "Inflation", seriesId: "CPIAUCSL", featureName: "yoy" },
  { id: "CPILFESL:yoy", label: "Core CPI YoY", domain: "Inflation", seriesId: "CPILFESL", featureName: "yoy" },
  { id: "PCEPILFE:yoy", label: "Core PCE YoY", domain: "Inflation", seriesId: "PCEPILFE", featureName: "yoy" },
  { id: "GDPC1:yoy", label: "Real GDP YoY", domain: "Growth", seriesId: "GDPC1", featureName: "yoy" },
  { id: "INDPRO:yoy", label: "Industrial Production YoY", domain: "Growth", seriesId: "INDPRO", featureName: "yoy" },
  { id: "CFNAI:moving_average_3m", label: "CFNAI (3M average)", domain: "Growth", seriesId: "CFNAI", featureName: "moving_average_3m" },
  { id: "RSAFS:yoy", label: "Retail Sales YoY", domain: "Consumer", seriesId: "RSAFS", featureName: "yoy" },
  { id: "PCEC96:yoy", label: "Real Consumption YoY", domain: "Consumer", seriesId: "PCEC96", featureName: "yoy" },
  { id: "PSAVERT:raw", label: "Saving Rate", domain: "Consumer", seriesId: "PSAVERT" },
  { id: "HOUST:raw", label: "Housing Starts", domain: "Housing", seriesId: "HOUST" },
  { id: "PERMIT:raw", label: "Building Permits", domain: "Housing", seriesId: "PERMIT" },
  { id: "MORTGAGE30US:raw", label: "30Y Mortgage Rate", domain: "Housing", seriesId: "MORTGAGE30US" },
  { id: "DFF:raw", label: "Fed Funds Rate", domain: "Financial Conditions", seriesId: "DFF" },
  { id: "DGS2:raw", label: "2Y Treasury", domain: "Financial Conditions", seriesId: "DGS2" },
  { id: "DGS10:raw", label: "10Y Treasury", domain: "Financial Conditions", seriesId: "DGS10" },
  { id: "DFII10:raw", label: "10Y Real Yield", domain: "Financial Conditions", seriesId: "DFII10" },
  { id: "NFCI:raw", label: "NFCI", domain: "Financial Conditions", seriesId: "NFCI" },
];

export const relationshipPresets = [
  { label: "CPI YoY vs Fed Funds Rate", left: "CPIAUCSL:yoy", right: "DFF:raw" },
  { label: "Unemployment Rate vs Initial Claims", left: "UNRATE:raw", right: "ICSA:moving_average_4w" },
  { label: "Housing Starts vs Mortgage Rate", left: "HOUST:raw", right: "MORTGAGE30US:raw" },
  { label: "Retail Sales YoY vs Real Consumption YoY", left: "RSAFS:yoy", right: "PCEC96:yoy" },
  { label: "2Y Treasury vs 10Y Treasury", left: "DGS2:raw", right: "DGS10:raw" },
] as const;

export function relationshipChoice(id: string): RelationshipChoice {
  const choice = relationshipChoices.find((item) => item.id === id);
  if (!choice) throw new Error(`Unknown relationship choice: ${id}`);
  return choice;
}
