import type { EconomyBriefResponse, OverviewRefreshState } from "../api/macrolens";
import { tText } from "../i18n/language";
import { availabilityPresentation, availabilityTime, checkStatusLabel, overviewCheckResult, fomcScheduleDetails } from "./sourceCheckPresentation";

type Checks=EconomyBriefResponse["source_checks"];
export function SourceCheckStatus({checks,refresh,unsupported=false}:{checks?:Checks;refresh?:OverviewRefreshState;unsupported?:boolean}) {
 const summary=availabilityPresentation(checks,refresh,unsupported);
 if(!summary)return null;
 const failures=refresh?.results.filter(result=>(result.status==="error"||result.status==="skipped"||result.status==="partial")&&!(result.resource==="fed:calendar"&&result.status==="partial"&&checks?.fomc_schedule?.overview_status==="success"))??[];
 return <div className="overview-source-check">
  <span role="status" aria-live="polite">{tText(summary.label)}{summary.at?<> <time dateTime={summary.at}>{availabilityTime(summary.at)}</time></>:null}</span>
  <details className="overview-check-details"><summary>{tText("Check details")}</summary>
   <p>{tText("Availability checks confirm provider requests, not a data-quality audit or the publication date of every reading.")}</p>
   <p>{tText("The displayed time is the oldest latest successful check among the covered inputs. Observation periods, publication dates and retrieval times are separate.")}</p>
   <p>{tText("Last attempt")}: {refresh?.attempted_at?availabilityTime(refresh.attempted_at):tText("Not recorded")}. {tText("Overview check result")}: {tText(checkStatusLabel(overviewCheckResult(checks,refresh)))}.</p>
   <p>{tText("Checked inputs")}: {checks?.checked_count??0} / {checks?.required_count??0}.</p>
   <ul>{checks?.sources.map(source=><li key={source.resource}>{tText(source.label)} ({source.provider}): {tText(checkStatusLabel(source.overview_status??source.status))}. {tText("Last successful check")}: {source.last_success_at?availabilityTime(source.last_success_at):tText("Not recorded")}{(source.overview_error_code??(source.overview_status==="success"?null:source.error_code))?` (${source.overview_error_code??source.error_code})`:""}.</li>)}</ul>
   {fomcScheduleDetails(checks).map((line,index)=><p key={index}>{tText(line)}</p>)}
   {failures.length?<p>{tText("Unverified sources")}: {failures.map(result=>`${result.resource} (${result.error_code??(result.missing_times?.length?`${tText("Decision time unavailable")}: ${result.missing_times.join(", ")}`:result.status)})`).join(", ")}.</p>:null}
   {failures.some(result=>result.manual_import_available)?<p>{tText("Latest ISM publication was not verified; manual import remains available.")}</p>:null}
   <p>{tText("FRED checks normally have a 15-minute minimum interval; calendar and ISM checks normally have a 6-hour minimum. These intervals do not guarantee immediate publication availability.")}</p>
  </details>
 </div>;
}
