import { getLocale, getLanguage, t } from "../i18n/language";
import { formatCompactCount, formatNumber, formatObservationDate, formatSaarThousands, formatThousandsAsMillions } from "../format";
import type { ChartDefinition, ChartUnit } from "./chartDefinitions";

export function formatChartValue(value: number, unit: ChartUnit, compact = false): string {
  if (unit === "percent") return `${formatNumber(value, compact ? 1 : 2)}%`;
  if (unit === "spread") return `${formatNumber(value, 2)} ${getLanguage() === "pl" ? "pkt proc." : "pp"}`;
  if (unit === "index") return formatNumber(value, 2);
  if (unit === "thousands") return formatThousandsAsMillions(value);
  if (unit === "saar") return compact ? `${formatNumber(value / 1000, 1)}${getLanguage() === "pl" ? " mln" : "M"}` : formatSaarThousands(value);
  if (unit === "count") return compact ? formatCompactCount(value) : new Intl.NumberFormat(getLocale()).format(value);
  return `${formatNumber(value, compact ? 0 : 0)}${getLanguage() === "pl" ? " tys." : "K"}`;
}

export function formatChartDate(date: string, definition: ChartDefinition): string {
  return formatObservationDate(date, definition.frequency);
}
