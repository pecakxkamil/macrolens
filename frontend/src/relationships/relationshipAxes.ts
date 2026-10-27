import type { RelationshipIndicator, RelationshipKey } from "../api/macrolens";

export interface RelationshipAxis {
  id: string;
  orientation: "left" | "right";
  members: RelationshipKey[];
}

// These two diffusion indices use the same ISM PMI point scale; other indices
// still need their own bases and must not be grouped by the generic unit alone.
export function isIsmPmiLevel(indicator: RelationshipIndicator): boolean {
  return ["ISM_MANUFACTURING_PMI", "ISM_SERVICES_PMI"].includes(indicator.series_id)
    && [null, undefined, "level"].includes(indicator.feature_name)
    && indicator.unit.trim().toLowerCase() === "index";
}

export function isIsmPmiPair(indicators: RelationshipIndicator[]): boolean {
  return indicators.length === 2 && indicators.every(isIsmPmiLevel)
    && new Set(indicators.map(item => item.series_id)).size === 2;
}

function compatibleUnit(unit: string): string | null {
  const normalized = unit.trim().toLowerCase().replace(/\s+/g, " ");
  if (["percent", "percentage", "pct", "%"].includes(normalized)) return "percent";
  // "Index" does not identify a common base or scale across different indices.
  if (!normalized || normalized === "index") return null;
  return normalized;
}

export function relationshipAxisPlan(
  indicators: RelationshipIndicator[],
  mode: "actual" | "indexed",
): { axes: RelationshipAxis[]; axisFor: Record<RelationshipKey, string> } {
  const axisFor: Record<RelationshipKey, string> = { left: "", right: "", third: "" };
  if (mode === "indexed") {
    for (const indicator of indicators) axisFor[indicator.key] = "index";
    return { axes: [{ id: "index", orientation: "left", members: indicators.map((item) => item.key) }], axisFor };
  }

  const axes: RelationshipAxis[] = [];
  const byUnit = new Map<string, RelationshipAxis>();
  for (const indicator of indicators) {
    const unit = isIsmPmiLevel(indicator) ? "ism-pmi-index-points" : compatibleUnit(indicator.unit);
    let axis = unit === null ? undefined : byUnit.get(unit);
    if (!axis) {
      axis = { id: `axis-${axes.length}`, orientation: axes.length === 0 ? "left" : "right", members: [] };
      axes.push(axis);
      if (unit !== null) byUnit.set(unit, axis);
    }
    axis.members.push(indicator.key);
    axisFor[indicator.key] = axis.id;
  }
  return { axes, axisFor };
}

export function shortUnit(unit: string): string {
  if (["percent", "percentage", "pct", "%"].includes(unit.toLowerCase())) return "%";
  if (unit === "percentage points") return "pp";
  if (unit === "index points") return "points";
  if (unit.startsWith("billions of")) return "bn USD";
  if (unit.startsWith("thousands")) return unit.includes("annual rate") ? "thousands SAAR" : "thousands";
  return unit;
}

// Derive bounds from every member of this axis, using the displayed scale.
export function relationshipAxisDomain(rows: Record<string, unknown>[], members: RelationshipKey[], mode: "actual" | "indexed"): [number, number] {
  let min = Infinity, max = -Infinity;
  for (const row of rows) for (const member of members) {
    const value = row[mode === "indexed" ? `${member}_index` : member];
    if (typeof value === "number" && Number.isFinite(value)) { min = Math.min(min, value); max = Math.max(max, value); }
  }
  if (!Number.isFinite(min)) return [0, 1];
  const padding = (max - min) * 0.05 || Math.max(Math.abs(min) * 0.05, 0.01);
  return [min - padding, max + padding];
}
