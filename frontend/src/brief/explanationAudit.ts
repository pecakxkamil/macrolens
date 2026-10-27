/** Local audit export using exactly the functions rendered by Overview. */
import type { EconomyBriefResponse } from "../api/macrolens";
import { briefModel, timestamp } from "./briefModel";
import { economicInterpretation, fedDecisionMarkers } from "./economicInterpretation";
import { economicExplanation, fedExplanation } from "./economicExplanations";
import { getLanguage, tText } from "../i18n/language";
import { availabilityPresentation, availabilityTime } from "./sourceCheckPresentation";

export function explanationAuditMarkdown(data:EconomyBriefResponse,generatedAt=new Date().toISOString()):string {
 const model=briefModel(data),status=availabilityPresentation(data.source_checks,data.refresh);
 const blocks=[`# MacroLens Overview explanation audit (${getLanguage().toUpperCase()})`,
  `Generated: ${timestamp(generatedAt)}`,`Data assembled: ${timestamp(data.assembled_at)}`,
  `Published data revision: ${data.data_revision??"not recorded"}.`,
  status?`${tText(status.label)}${status.at?` ${availabilityTime(status.at)}`:""}`:"Availability check not recorded.",
  "These are the existing deterministic Overview outputs for this saved dataset. Observation dates, publication dates, retrieval times and check times are distinct. Market comments are conditional, not trading signals."];
 for(const domain of model.domains)for(const reading of domain.compact){
  const raw=reading.raw,interpretation=economicInterpretation(reading),explanation=economicExplanation(reading);
  const point=(which:"current"|"previous")=>{
   const value=raw?.[which];
   return value?`${reading[which].display}; stored value ${value.value} ${raw!.unit}; observation period ${reading[which].period} [${value.observation_date}]; calculation as-of ${value.feature_as_of_date??"not applicable (raw observation)"}${value.document_published_at?`; document publication ${value.document_published_at}; retrieval ${value.retrieved_at}; source ${value.source_url}`:""}`:"Unavailable";
  };
  blocks.push(`## ${raw?.series_id??reading.key} — ${tText(reading.label)}`,
   `- Current: ${point("current")}\n- Previous: ${point("previous")}\n- Direction: ${reading.arrow} (${reading.comparison}).\n- Interpretation: ${interpretation?.symbol??"not assigned"}${interpretation?` (${interpretation.tone})`:""}.\n- Reason: ${interpretation?tText(interpretation.reason):"No interpretation assigned without an eligible comparison."}`,
   `Observation: ${tText(explanation.observation)}`,`### ${tText("Economy")}\n${tText(explanation.economy)}`,
   `### ${tText("Fed")}\n${tText(explanation.fed)}`,`### ${tText("Markets")}\n${tText(explanation.markets)}`);
 }
 const target=model.fedTarget,markers=fedDecisionMarkers(target),note=fedExplanation(target),prior=target.raw?.last_rate_change;
 blocks.push(`## DFEDTARL / DFEDTARU — ${tText("Fed target range")}`,
  `- Current: ${target.range}; observation through ${target.raw?.observation_date??"unavailable"}; effective since ${target.raw?.effective_date??"unavailable"}.\n- Prior range before the last stored rate change: ${prior?`${prior.previous_lower}–${prior.previous_upper}%`:"unavailable"}. This is not a new decision today.\n- Direction of last stored change: ${markers?.arrow??"unavailable"}.\n- Interpretation: ${markers?.interpretation.symbol??"not assigned"}.\n- Reason: ${markers?tText(markers.interpretation.reason):"Last recorded rate change unavailable."}`,
  `Observation: ${tText(note.observation)}`,`### ${tText("Economy")}\n${tText(note.economy)}`,`### ${tText("Fed")}\n${tText(note.fed)}`,`### ${tText("Markets")}\n${tText(note.markets)}`);
 return blocks.join("\n\n")+"\n";
}
