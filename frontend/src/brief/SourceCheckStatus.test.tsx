import { cleanup, render } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { SourceCheckStatus } from "./SourceCheckStatus";
import { availabilityReportDetails, overviewCheckResult } from "./sourceCheckPresentation";
import { setLanguage } from "../i18n/language";
import type { EconomyBriefResponse } from "../api/macrolens";

type Checks = NonNullable<EconomyBriefResponse["source_checks"]>;
function metadata(): Checks {
  return {status:"partial",checked_at:"2026-10-23T10:30:00Z",checked_count:1,required_count:2,sources:[
    {resource:"fred:UNRATE",label:"UNRATE",provider:"FRED",status:"partial",last_attempt_at:"2026-10-23T11:30:00Z",last_success_at:"2026-10-23T10:30:00Z",coverage_checked_at:"2026-10-23T10:30:00Z",error_code:null,scope:{}},
    {resource:"ism:ISM_MANUFACTURING_PMI",label:"ISM Manufacturing PMI",provider:"ISM via PR Newswire",status:"not_recorded",last_attempt_at:null,last_success_at:null,coverage_checked_at:null,error_code:null,scope:{}},
  ]};
}
afterEach(()=>{cleanup();setLanguage("en");vi.unstubAllGlobals();});

test.each(["en","pl"] as const)("partial check keeps its Warsaw timestamp without an info popup in %s", language=>{
  setLanguage(language);const fetch=vi.fn();vi.stubGlobal("fetch",fetch);
  render(<SourceCheckStatus checks={metadata()}/>);
  const status=document.querySelector(".overview-source-check")!;
  expect(status).toHaveTextContent(language==="pl"?"Sprawdzono cz\u0119\u015b\u0107 \u017ar\u00f3de\u0142":"Some sources checked");
  expect(status.querySelector("time")).toHaveTextContent("12:30 (Europe/Warsaw)");
  expect(status.querySelector("time")).toHaveAttribute("dateTime","2026-10-23T10:30:00Z");
  expect(status.querySelector("button")).toBeNull();
  expect(status.querySelector('[role="tooltip"]')).toBeNull();
  expect(fetch).not.toHaveBeenCalled();
});

test.each(["en","pl"] as const)("complete checks use their own metadata, not the clock, in %s", language=>{
 setLanguage(language);const checks=metadata();checks.status="complete";checks.checked_count=2;
 checks.sources=checks.sources.map(source=>({...source,status:"success",last_success_at:checks.checked_at}));
 render(<SourceCheckStatus checks={checks}/>);
 const line=document.querySelector(".overview-source-check")!;
 expect(line).toHaveTextContent(language==="pl"?"\u0179r\u00f3d\u0142a sprawdzono:":"Sources checked:");
 expect(line.querySelector("time")).toHaveTextContent("12:30 (Europe/Warsaw)");
});

test.each([undefined,{...metadata(),checked_at:null,status:"not_recorded" as const},{...metadata(),checked_at:"invalid"}])("missing or invalid check date hides the row",checks=>{
 const {container}=render(<SourceCheckStatus checks={checks}/>);expect(container).toBeEmptyDOMElement();
});

test("Warsaw DST formatting uses the timestamp's actual timezone offset",()=>{
 const checks=metadata();checks.checked_at="2026-10-28T10:30:00Z";
 render(<SourceCheckStatus checks={checks}/>);
 expect(document.querySelector(".overview-source-check time")).toHaveTextContent("11:30 (Europe/Warsaw)");
});

test.each(["en","pl"] as const)("errors never claim complete coverage and details retain missing source scope in %s",language=>{
 setLanguage(language);const checks=metadata();checks.status="complete";
 render(<SourceCheckStatus checks={checks} refresh={{status:"partial",results:[{resource:"ism:services",status:"error",error_code:"latest_publication_not_verified",manual_import_available:true}]}}/>);
 const status=document.querySelector('[role="status"]')!;
 expect(status).toHaveTextContent(language==="pl"?"Nie uda\u0142o si\u0119 sprawdzi\u0107 cz\u0119\u015bci \u017ar\u00f3de\u0142":"Unable to check some sources");
 expect(document.querySelector("details")).not.toHaveAttribute("open");expect(document.querySelector("details")).toHaveTextContent("ism:services");
});

function scopedMetadata(displayedMissing=false,fetchFailed=false):Checks {
 const checks=metadata();checks.status=displayedMissing||fetchFailed?"partial":"complete";checks.status_scope="overview";checks.full_scope_status="partial";checks.checked_count=2;
 checks.sources=checks.sources.map(source=>({...source,status:"success",last_success_at:checks.checked_at}));
 checks.sources[0]={...checks.sources[0],resource:"fed:calendar",label:"FOMC schedule",provider:"Federal Reserve",status:"partial",overview_status:fetchFailed?"error":displayedMissing?"partial":"success",error_code:"decision_times_unavailable",scope:{dates:["2026-10-28","2027-01-27"],missing_times:displayedMissing?["2026-10-28","2027-01-27"]:["2027-01-27"]}};
 checks.fomc_schedule={source_check_status:fetchFailed?"error":"success",completeness_status:"partial",overview_status:checks.sources[0].overview_status!,overview_dates:["2026-10-28"],displayed_missing_times:displayedMissing?["2026-10-28"]:[],future_missing_times:["2027-01-27"],fetch_error_dates:fetchFailed?["2026-10-28"]:[],time_checks:[]};
 return checks;
}
const partialJob={status:"partial" as const,results:[{resource:"fed:calendar",status:"partial",missing_times:["2027-01-27"]}]};

test.each(["en","pl"] as const)("distant incomplete FOMC schedule stays in details and report without lowering Overview in %s",language=>{
 setLanguage(language);const checks=scopedMetadata();render(<SourceCheckStatus checks={checks} refresh={partialJob}/>);
 expect(document.querySelector('[role="status"]')).toHaveTextContent(language==="pl"?"\u0179r\u00f3d\u0142a sprawdzono:":"Sources checked:");
 const details=document.querySelector('details')!;
 expect(details).toHaveTextContent("2027-01-27");expect(details).toHaveTextContent(language==="pl"?"Kompletno\u015b\u0107 przysz\u0142ego harmonogramu":"Future schedule completeness");
 expect(details).toHaveTextContent(language==="pl"?"Harmonogram niepe\u0142ny":"Incomplete schedule");
 expect(details).not.toHaveTextContent(language==="pl"?"Niezweryfikowane \u017ar\u00f3d\u0142a":"Unverified sources");
 const report=availabilityReportDetails({source_checks:checks,refresh:partialJob} as EconomyBriefResponse).join('\n');
 expect(report).toContain("Overview check result: Complete check");expect(report).toContain("Future schedule completeness: Incomplete schedule");expect(report).toContain("2027-01-27");expect(report).toContain("Full refresh result: Partial check");
});

test.each(["en","pl"] as const)("unconfirmed displayed FOMC decision keeps the current scope partial in %s",language=>{
 setLanguage(language);render(<SourceCheckStatus checks={scopedMetadata(true)} refresh={partialJob}/>);
 expect(document.querySelector('[role="status"]')).toHaveTextContent(language==="pl"?"Sprawdzono cz\u0119\u015b\u0107 \u017ar\u00f3de\u0142:":"Some sources checked:");
 expect(document.querySelector('details')).toHaveTextContent("2026-10-28");
});

test.each(["en","pl"] as const)("displayed source fetch failure is an error rather than an unpublished time in %s",language=>{
 setLanguage(language);render(<SourceCheckStatus checks={scopedMetadata(true,true)} refresh={partialJob}/>);
 expect(document.querySelector('[role="status"]')).toHaveTextContent(language==="pl"?"Nie uda\u0142o si\u0119 sprawdzi\u0107 cz\u0119\u015bci \u017ar\u00f3de\u0142":"Unable to check some sources");
});

test("an unrelated partial or failed source cannot be hidden by the FOMC scope distinction",()=>{
 const checks=scopedMetadata();
 expect(overviewCheckResult(checks,{status:"partial",results:[{resource:"ism:services",status:"partial"}]})).toBe("partial");
 checks.sources[1].status="error";expect(overviewCheckResult(checks,partialJob)).toBe("error");
});
