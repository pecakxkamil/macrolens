import { fetchFeatureHistory, fetchSeriesHistory, fetchYieldCurveHistory, type HistoryOptions, type HistoryResponse } from "../api/macrolens";
import type { ChartDefinition, ChartSeries } from "./chartDefinitions";

export function requestKey(series: ChartSeries): string {
  return series.derived ?? `${series.seriesId}:${series.featureName ?? "raw"}`;
}

export function fetchChartHistory(series: ChartSeries, options: HistoryOptions): Promise<HistoryResponse> {
  if (series.derived === "2s10s") return fetchYieldCurveHistory(options);
  if (!series.seriesId) throw new Error("Chart series has no history source.");
  return series.featureName
    ? fetchFeatureHistory(series.seriesId, series.featureName, options)
    : fetchSeriesHistory(series.seriesId, options);
}

export type HistoryResult =
  | { status: "loading" }
  | { status: "ready"; data: HistoryResponse }
  | { status: "error" };

export type ChartRow = { observation_date: string; [seriesId: string]: string | number | null };

export function combineChartData(definition: ChartDefinition, histories: Record<string, HistoryResponse>): ChartRow[] {
  const rows = new Map<string, ChartRow>();
  for (const series of definition.series) {
    const history = histories[requestKey(series)];
    for (const observation of history?.observations ?? []) {
      const date = observation.observation_date;
      const row = rows.get(date) ?? { observation_date: date };
      row[series.id] = typeof observation.value === "number" && Number.isFinite(observation.value)
        ? observation.value
        : null;
      rows.set(date, row);
    }
  }
  return [...rows.values()].sort((a, b) => a.observation_date.localeCompare(b.observation_date))
    .map((row) => {
      for (const series of definition.series) row[series.id] ??= null;
      return row;
    });
}

export function rangeStartDate(years: number, today = new Date()): string {
  const date = new Date(Date.UTC(today.getUTCFullYear() - years, today.getUTCMonth(), today.getUTCDate()));
  return date.toISOString().slice(0, 10);
}
