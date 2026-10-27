import type { EconomyBriefResponse, OverviewRefreshState } from "../api/macrolens";
import { getLanguage } from "../i18n/language";

type Checks=EconomyBriefResponse["source_checks"];
export function availabilityTime(value:string) {
 return `${new Intl.DateTimeFormat(getLanguage()==="pl"?"pl-PL":"en-GB",{timeZone:"Europe/Warsaw",day:"numeric",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit"}).format(new Date(value))} (Europe/Warsaw)`;
}
export function overviewCheckResult(checks:Checks,refresh?:OverviewRefreshState):string {
 if(refresh?.status==="running")return "running";
 if(refresh?.status==="error"||refresh?.results.some(row=>row.status==="error"||row.status==="skipped")||checks?.sources.some(row=>(row.overview_status??row.status)==="error"))return "error";
 const scopedFedSuccess=checks?.status_scope==="overview"&&checks.fomc_schedule?.overview_status==="success";
 const unresolvedPartial=refresh?.results.some(row=>row.status==="partial"&&!(row.resource==="fed:calendar"&&scopedFedSuccess));
 if(checks?.status!=="complete"||unresolvedPartial||(refresh?.status==="partial"&&!scopedFedSuccess))return "partial";
 return "complete";
}
export function availabilityPresentation(checks:Checks,refresh?:OverviewRefreshState,unsupported=false) {
 const status=overviewCheckResult(checks,refresh);
 if(status==="running")return {label:"Checking availability of new data\u2026",at:null};
 if(unsupported||status==="error")return {label:"Unable to check some sources \u2014 stored data shown.",at:null};
 if(!checks?.checked_at||!Number.isFinite(Date.parse(checks.checked_at)))return null;
 return {label:status==="complete"?"Sources checked:":"Some sources checked:",at:checks.checked_at};
}
function completenessLabel(status:string):string {
 return status==="complete"?"Complete schedule":status==="partial"?"Incomplete schedule":"Schedule completeness unavailable";
}
export function fomcScheduleDetails(checks:Checks):string[] {
 const schedule=checks?.fomc_schedule;
 if(!schedule)return [];
 return ["Overview covers indicator inputs, the displayed calendar window and the separately displayed next FOMC decision.",
  `Full FOMC schedule check: ${checkStatusLabel(schedule.source_check_status)}. Future schedule completeness: ${completenessLabel(schedule.completeness_status)}.`,
  ...(schedule.displayed_missing_times.length?[`Displayed FOMC decision times unavailable: ${schedule.displayed_missing_times.join(", ")}.`]:[]),
  ...(schedule.future_missing_times.length?[`Later FOMC decision times unavailable: ${schedule.future_missing_times.join(", ")}. These dates are outside the current Overview scope.`]:[]),
  ...(schedule.fetch_error_dates.length?[`FOMC monthly calendar fetch errors: ${schedule.fetch_error_dates.join(", ")}.`]:[]),
  ...schedule.time_checks.map(row=>`${row.release_date}: ${row.fetch_status==="success"?"Calendar source fetched successfully":"Calendar source fetch failed"}; ${row.time_status==="confirmed"?"Decision time confirmed":"Decision time not confirmed"}${row.http_status?`; HTTP ${row.http_status}`:""}.`),
  "An unconfirmed time after a successful source check is distinct from a download or parsing failure. No decision time is inferred."];
}
export function availabilityReportDetails(data:EconomyBriefResponse):string[] {
 const points=[`Published data revision: ${data.data_revision??"not recorded"}.`,
  `Overview check result: ${checkStatusLabel(overviewCheckResult(data.source_checks,data.refresh))}.`,
  ...fomcScheduleDetails(data.source_checks),
  `Latest check attempt (full source scope): ${data.refresh?.attempted_at??"not recorded"}; Full refresh result: ${checkStatusLabel(data.refresh?.status??"not_recorded")}; Check completed at: ${data.refresh?.completed_at??"not recorded"}.`,
  "The check timestamp is the oldest latest successful check among covered Overview inputs. Observation periods, publication dates, retrieval times and calculation dates remain separate.",
  "FRED series metadata is checked before reloading changed current-vintage histories; calendar and ISM discovery checks have separate provider intervals. The interval does not guarantee immediate publication availability."];
 for(const source of data.source_checks?.sources??[])points.push(`${source.resource} (${source.provider}): ${source.status}; Overview: ${source.overview_status??source.status}; last attempt ${source.last_attempt_at??"not recorded"}; last successful check ${source.last_success_at??"not recorded"}; error ${source.error_code??"none"}.${source.scope.legacy_dates_only?" Stored meeting dates only; full decision-time checks are not confirmed.":""}`);
 for(const result of data.refresh?.results??[])if(result.status!=="success"&&result.status!=="cached")points.push(`${result.resource}: ${result.status}; ${result.error_code??"partial scope"}.${result.missing_times?.length?` Decision time unavailable: ${result.missing_times.join(", ")}.`:""}${result.manual_import_available?" Latest ISM publication was not verified; manual import remains available.":""}`);
 return points;
}

export function checkStatusLabel(status:string) {
 return ({running:"Check running",complete:"Complete check",partial:"Partial check",error:"Check failed",idle:"No check recorded",success:"Successful check",cached:"Cached check",not_recorded:"No check recorded"} as Record<string,string>)[status]??status;
}
