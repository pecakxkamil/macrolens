import type { RelationshipIndicator, RelationshipKey } from "../api/macrolens";

export interface RelationshipAxis {
  id: string;
  orientation: "left" | "right";
  members: RelationshipKey[];
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
    const unit = compatibleUnit(indicator.unit);
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
