import type { SeriesMetadata } from "../api/macrolens";
import { formatCompactCount, formatNumber, formatSaarThousands, formatThousandsAsMillions } from "../format";

export const indicatorCategories = [
  { id: "all", label: "All" },
  { id: "labor", label: "Labor" },
  { id: "inflation", label: "Inflation" },
  { id: "growth", label: "Growth" },
  { id: "consumer", label: "Consumer" },
  { id: "housing", label: "Housing" },
  { id: "financial_conditions", label: "Financial Conditions" },
] as const;

const featureLabels: Record<string, string> = {
  level: "Level",
  yoy: "YoY",
  mom: "MoM",
  qoq: "QoQ",
  qoq_annualized: "QoQ annualized",
  annualized_3m: "Annualized 3M",
  change_3m: "3M change",
  change_6m: "6M change",
  change_4w: "4W change",
  change_13w: "13W change",
  monthly_change: "Monthly change",
  monthly_change_ma_3m: "Monthly change, 3M average",
  monthly_change_ma_6m: "Monthly change, 6M average",
  moving_average_3m: "3M average",
  moving_average_4w: "4W average",
  moving_average_13w: "13W average",
};

export function featureLabel(feature: string): string {
  return featureLabels[feature] ?? feature.replace(/_/g, " ");
}

export function categoryLabel(category: string): string {
  return indicatorCategories.find((item) => item.id === category)?.label ?? category.replace(/_/g, " ");
}

function isPercentageGrowth(feature: string | null): boolean {
  return feature !== null && ["yoy", "mom", "qoq", "qoq_annualized", "annualized_3m"].includes(feature);
}

function isAbsoluteChange(feature: string | null): boolean {
  return feature !== null && (feature.startsWith("change_") || feature.startsWith("monthly_change"));
}

export function selectedUnit(metadata: SeriesMetadata, feature: string | null): string {
  if (isPercentageGrowth(feature)) return "percent";
  if (isAbsoluteChange(feature) && metadata.unit === "percent") return "percentage points";
  if (isAbsoluteChange(feature) && metadata.unit === "index") return "index points";
  return metadata.unit;
}

export function formatIndicatorValue(value: number, metadata: SeriesMetadata, feature: string | null, compact = false): string {
  const unit = selectedUnit(metadata, feature);
  if (unit === "percent") return `${formatNumber(value, compact ? 1 : 2)}%`;
  if (unit === "percentage points") return `${formatNumber(value, 2)} pp`;
  if (unit === "index points") return `${formatNumber(value, 2)} points`;
  if (unit.includes("seasonally adjusted annual rate")) return compact ? `${formatNumber(value / 1000, 1)}M` : formatSaarThousands(value);
  if (unit.startsWith("thousands")) {
    return isAbsoluteChange(feature)
      ? `${formatNumber(value, compact ? 0 : 0)}K`
      : formatThousandsAsMillions(value);
  }
  if (unit === "number") return formatCompactCount(value);
  if (unit.includes("dollars per hour")) return `$${formatNumber(value, 2)}`;
  if (unit.startsWith("millions of dollars")) return `$${formatNumber(value / 1000, compact ? 0 : 1)}B`;
  if (unit.startsWith("billions of")) return `$${formatNumber(value / 1000, compact ? 0 : 1)}T`;
  return formatNumber(value, compact ? 1 : 2);
}
