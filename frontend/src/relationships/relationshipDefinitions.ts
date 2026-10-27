import { featureLabel } from "../indicators/indicatorMetadata";
import type { RelationshipCatalogSource, RelationshipSource } from "../api/macrolens";

type SourceName = { series_id?: string; name: string; short_name: string | null; source_kind?: string };
export function relationshipSourceName(source: SourceName): string {
  if (source.series_id === "ISM_MANUFACTURING_PMI") return "ISM Manufacturing PMI";
  if (source.series_id === "ISM_SERVICES_PMI") return "ISM Services PMI";
  return source.short_name || source.name;
}
export function measureLabel(source: SourceName, feature?: string | null): string {
  return `${relationshipSourceName(source)} \u00b7 ${source.source_kind === "asset" ? "Price" : featureLabel(feature || "level")}`;
}
export function presetSource(id: string): RelationshipSource {
  const [seriesId, featureName] = id.split(":");
  return { seriesId, featureName: featureName === "raw" ? undefined : featureName };
}
export function measureKey(source?: RelationshipSource): string {
  return source ? `${source.seriesId}:${source.featureName === "level" ? "" : source.featureName ?? ""}` : "";
}
export function availablePresets(catalog: RelationshipCatalogSource[]) {
  const supports = (id: string) => { const measure = presetSource(id), source = catalog.find(row => row.series_id === measure.seriesId); return source && (!measure.featureName || source.features.includes(measure.featureName)); };
  return relationshipPresets.filter(preset => supports(preset.left) && supports(preset.right));
}

export const relationshipPresets = [
  { label: "CPI YoY vs Fed Funds Rate", left: "CPIAUCSL:yoy", right: "DFF:raw" },
  { label: "Unemployment Rate vs Initial Claims", left: "UNRATE:raw", right: "ICSA:moving_average_4w" },
  { label: "Housing Starts vs Mortgage Rate", left: "HOUST:raw", right: "MORTGAGE30US:raw" },
  { label: "Retail Sales YoY vs Real Consumption YoY", left: "RSAFS:yoy", right: "PCEC96:yoy" },
  { label: "2Y Treasury vs 10Y Treasury", left: "DGS2:raw", right: "DGS10:raw" },
] as const;
