import type { RelationshipKey, RelationshipResponse } from "../api/macrolens";

export type RelationshipChartRow = { period: string } & Record<string, string | number | null>;

export function relationshipChartRows(response: RelationshipResponse): RelationshipChartRow[] {
  return response.observations.map((observation) => {
    const row: RelationshipChartRow = { period: observation.period };
    for (const indicator of response.indicators) {
      const key: RelationshipKey = indicator.key;
      const reading = observation[key];
      row[key] = reading?.value ?? null;
      row[`${key}_index`] = reading?.normalized_value ?? null;
    }
    return row;
  });
}
