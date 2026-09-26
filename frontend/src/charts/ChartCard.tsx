import type { HistoryResponse } from "../api/macrolens";
import { combineChartData, requestKey, type HistoryResult } from "./chartData";
import type { ChartDefinition } from "./chartDefinitions";
import { TimeSeriesChart } from "./TimeSeriesChart";

export function ChartCard({ definition, results }: { definition: ChartDefinition; results: Record<string, HistoryResult> }) {
  const sources = definition.series.map((series) => results[requestKey(series)]);
  const loading = sources.some((source) => !source || source.status === "loading");
  const failed = sources.some((source) => source?.status === "error");
  const histories: Record<string, HistoryResponse> = {};
  if (!loading && !failed) {
    definition.series.forEach((series, index) => {
      const result = sources[index];
      if (result.status === "ready") histories[requestKey(series)] = result.data;
    });
  }
  const rows = combineChartData(definition, histories);
  const hasValues = rows.some((row) => definition.series.some((series) => typeof row[series.id] === "number"));

  return (
    <article className="chart-card" aria-labelledby={`${definition.id}-title`}>
      <h2 id={`${definition.id}-title`}>{definition.title}</h2>
      <p className="chart-card__description">{definition.description}</p>
      {loading ? <p className="chart-state" role="status">Loading history...</p>
        : failed ? <p className="chart-state chart-state--error" role="alert">Unable to load chart history. Try another range or refresh the page.</p>
        : !hasValues ? <p className="chart-state">No history available for this range.</p>
        : <TimeSeriesChart key={definition.id} definition={definition} rows={rows} />}
    </article>
  );
}
