import { InfoTooltip } from "../components/InfoTooltip";
import type { Interpretation } from "./economicInterpretation";
export function InterpretationMarker({ label, interpretation }: { label: string; interpretation: Interpretation | null }) {
  return interpretation ? <span className={`overview-interpretation overview-interpretation--${interpretation.tone}`}>
    <InfoTooltip bounded trigger={interpretation.symbol} label={`${label}: ${interpretation.label}`} description={interpretation.reason} />
  </span> : null;
}
