import { InfoTooltip } from "../components/InfoTooltip";
import { tText } from "../i18n/language";
import type { EconomicExplanation } from "./economicExplanations";

export function EconomicExplanationTooltip({label,explanation}: {label:string;explanation:EconomicExplanation}) {
  const parts=[["Economy",explanation.economy],["Fed",explanation.fed],["Markets",explanation.markets]];
  return <InfoTooltip label={label} trigger="i" bounded description={[explanation.observation,...parts.map(([,text])=>text)].join(" ")}
    content={<span className="economic-explanation-content"><span className="economic-explanation-observation">{tText(explanation.observation)}</span>
      <span role="list">{parts.map(([title,text])=><span role="listitem" key={title}><b>{tText(title)}:</b> {tText(text)}</span>)}</span>
    </span>} />;
}
