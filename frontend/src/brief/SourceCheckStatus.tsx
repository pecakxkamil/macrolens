import type { EconomyBriefResponse, OverviewRefreshState } from "../api/macrolens";
import { tText } from "../i18n/language";
import { availabilityPresentation, availabilityTime } from "./sourceCheckPresentation";

type Checks=EconomyBriefResponse["source_checks"];
export function SourceCheckStatus({checks,refresh,unsupported=false}:{checks?:Checks;refresh?:OverviewRefreshState;unsupported?:boolean}) {
 const summary=availabilityPresentation(checks,refresh,unsupported);
 if(!summary)return null;
 return <div className="overview-source-check">
  <span role="status" aria-live="polite">{tText(summary.label)}{summary.at?<> <time dateTime={summary.at}>{availabilityTime(summary.at)}</time></>:null}</span>
 </div>;
}
