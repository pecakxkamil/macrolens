import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ReadingChartDialog, fedPreview, readingPreview } from "./ReadingChartDialog";
import { prepareReading, readingReportLine } from "./readingComparisons";
import { readingHoverText } from "./readingHoverText";
import type { OverviewReadingComparison } from "../api/macrolens";
import { setLanguage, tText } from "../i18n/language";

vi.mock("../charts/TimeSeriesChart",()=>({TimeSeriesChart:({definition,rows}: {definition:{title:string};rows:unknown[]})=><div role="img" aria-label={definition.title}>{rows.length} points</div>}));
beforeEach(()=>{
  Object.defineProperty(HTMLDialogElement.prototype,"showModal",{configurable:true,value:vi.fn(function(this:HTMLDialogElement){this.setAttribute("open","");})});
  Object.defineProperty(HTMLDialogElement.prototype,"close",{configurable:true,value:vi.fn(function(this:HTMLDialogElement){this.removeAttribute("open");})});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();setLanguage("en");});
function reading(key="headline_cpi", series="CPIAUCSL", feature="mom",unit="percent") {
  const raw:OverviewReadingComparison={component:key,series_id:series,feature_name:feature,domain:"inflation",label:key,frequency:"monthly",unit,change_unit:unit==="percent"?"percentage points":unit,
    current:{value:.2474391583996,observation_date:"2024-08-01",feature_as_of_date:"2024-09-01"},previous:{value:.126183936169,observation_date:"2024-07-01",feature_as_of_date:"2024-09-01"},
    three_periods_ago:null,expected_previous_observation_date:"2024-07-01",expected_three_periods_ago_date:null,latest_stored_observation_date:"2024-08-01",change:.1212552222306,change_type:"Difference"};
  return prepareReading(key,series,raw);
}
function mockHistory(status="ready") {
  const fetch=vi.fn(async(_input: string | URL)=>({ok:status!=="error",json:async()=>({observations:status==="empty"?[]:[{observation_date:"2024-08-01",value:2}]})}));vi.stubGlobal("fetch",fetch);return fetch;
}

test.each([
  ["headline_cpi","CPIAUCSL","mom","/series/CPIAUCSL/features/mom/history"],
  ["initial_claims","ICSA","raw","/series/ICSA/history"],
  ["real_gdp","GDPC1","qoq_annualized","/series/GDPC1/features/qoq_annualized/history"],
  ["manufacturing_pmi","ISM_MANUFACTURING_PMI","raw","/series/ISM_MANUFACTURING_PMI/history"],
  ["yield_curve_2s10s","DGS2 / DGS10","spread","/analytics/yield-curve/2s10s/history"],
])("preview for %s requests exactly the displayed measure",async(key,series,feature,path)=>{
  const fetch=mockHistory();const prepared=reading(key,series,feature);
  render(<ReadingChartDialog chart={readingPreview(prepared)} title={prepared.label} onClose={()=>{}} />);
  expect(await screen.findByRole("img",{name:prepared.label})).toHaveTextContent("1 points");
  expect(String(fetch.mock.calls[0][0])).toContain(path);
  expect(screen.getByRole("dialog",{name:prepared.label})).toBeInTheDocument();
  fireEvent.click(within(screen.getByRole("group",{name:"Chart time range"})).getByRole("button",{name:"5Y"}));
  await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(2));
});

test("Fed preview requests both bounds without fabricating a midpoint",async()=>{
 const fetch=mockHistory();render(<ReadingChartDialog chart={fedPreview} title="Fed target range" onClose={()=>{}} />);
 await screen.findByRole("img");expect(fetch).toHaveBeenCalledTimes(2);
 expect(String(fetch.mock.calls[0][0])).toContain("DFEDTARL/history");expect(String(fetch.mock.calls[1][0])).toContain("DFEDTARU/history");
});

test("closing, native Escape, backdrop and focus restoration do not navigate",async()=>{
  mockHistory();const close=vi.fn();const trigger=document.createElement("button");document.body.appendChild(trigger);trigger.focus();
  const hash=location.hash;const {unmount}=render(<ReadingChartDialog chart={readingPreview(reading())} title="CPI" onClose={close} />);
  fireEvent.click(screen.getByRole("button",{name:"Close chart"}));expect(close).toHaveBeenCalledTimes(1);
  fireEvent(screen.getByRole("dialog"),new Event("cancel",{bubbles:true,cancelable:true}));expect(close).toHaveBeenCalledTimes(2);
  fireEvent.click(screen.getByRole("dialog"));expect(close).toHaveBeenCalledTimes(3);
  unmount();expect(trigger).toHaveFocus();expect(location.hash).toBe(hash);expect(document.body.style.overflow).not.toBe("hidden");trigger.remove();
});

test.each(["error","empty"])("preview handles %s history",async status=>{
 mockHistory(status);render(<ReadingChartDialog chart={readingPreview(reading())} title="CPI" onClose={()=>{}} />);
 if(status==="error") {expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load");fireEvent.click(screen.getByRole("button",{name:"Retry"}));}
 else expect(await screen.findByText("No history available for this range.")).toBeInTheDocument();
});

test("hover rounds screen numbers while report keeps exact differences",()=>{
 const item=reading();expect(readingHoverText(item)).toContain("+0.12 percentage points");expect(readingHoverText(item)).not.toContain(".121255");expect(readingReportLine(item)).toContain("+0.121255222231 percentage points");
 item.raw!.change=.0001;expect(readingHoverText(item)).toContain("Change smaller than 0.01 percentage points");
});

test("housing hover describes fewer starts with annualized thousands in EN/PL",()=>{
 const source=reading("housing_starts","HOUST","level","thousands SAAR").raw!;
 source.current!.value=1275;source.previous!.value=1309;source.change=-34;
 const item=prepareReading("housing_starts","HOUST",source);
 expect(readingHoverText(item)).toContain("Fewer housing starts");expect(readingHoverText(item)).toContain("-34 thousand (annualized)");
 setLanguage("pl");expect(tText(readingHoverText(item))).toContain("Ni\u017csze tempo rozpocz\u0119tych bud\u00f3w");expect(tText(readingHoverText(item))).toContain("-34 tys.");
});


test("closing a pending preview aborts only its history request",()=>{
 let signal:AbortSignal|undefined;
 vi.stubGlobal("fetch",vi.fn((_url:string,options:{signal:AbortSignal})=>{signal=options.signal;return new Promise(()=>{});}));
 const {unmount}=render(<ReadingChartDialog chart={readingPreview(reading())} title="CPI" onClose={()=>{}} />);
 expect(screen.getByRole("status")).toHaveTextContent("Loading indicator history");
 expect(signal?.aborted).toBe(false);unmount();expect(signal?.aborted).toBe(true);
});

test("preview stays on the published generation and reloads when the generation changes",async()=>{
 const fetch=mockHistory();const props={chart:readingPreview(reading()),title:"CPI",onClose:()=>{}};
 const {rerender}=render(<ReadingChartDialog {...props} publicationId="saved"/>);await screen.findByRole("img");
 expect(String(fetch.mock.calls[0][0])).toContain("/brief/history?");expect(String(fetch.mock.calls[0][0])).toContain("revision=saved");
 rerender(<ReadingChartDialog {...props} publicationId="updated"/>);await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(2));expect(String(fetch.mock.calls[1][0])).toContain("revision=updated");
});
