import { afterEach, expect, test } from "vitest";
import { economicExplanation, fedExplanation, readingVariant } from "./economicExplanations";
import { domainSelection } from "./briefModel";
import { prepareReading } from "./readingComparisons";
import { prepareFedTarget } from "./fedTarget";
import { setLanguage, tText } from "../i18n/language";
import type { OverviewReadingComparison } from "../api/macrolens";
afterEach(()=>setLanguage("en"));
function reading(key:string,current=3,previous:number|null=2) {
 const raw={component:key,series_id:"TEST",feature_name:key==="payrolls"?"monthly_change":["unemployment","initial_claims","manufacturing_pmi","services_pmi","housing_starts","nfci","yield_curve_2s10s"].includes(key)?"level":"mom",frequency:"monthly",unit:key==="payrolls"?"thousands":key==="initial_claims"?"claims":["nfci","manufacturing_pmi","services_pmi"].includes(key)?"index":key==="housing_starts"?"thousands SAAR":"percent",
 current:{value:current,observation_date:"2024-02-01",feature_as_of_date:null},previous:previous===null?null:{value:previous,observation_date:"2024-01-01",feature_as_of_date:null},change:previous===null?null:current-previous,change_unit:key==="payrolls"?"thousands":key==="initial_claims"?"claims":["nfci","manufacturing_pmi","services_pmi"].includes(key)?"index points":key==="housing_starts"?"thousands SAAR":"percentage points"} as OverviewReadingComparison;
 return prepareReading(key,"TEST",raw);
}
test.each(domainSelection.flatMap(domain=>domain.readings.map(([key])=>key)))("%s has three conditional channels in EN/PL without boilerplate",key=>{
 for(const [c,p] of [[3,2],[2,3],[3,3]]){
 const text=economicExplanation(reading(key,c,p));
 for(const field of ["observation","economy","fed","markets"] as const){expect(text[field].length).toBeGreaterThan(10);setLanguage("pl");expect(tText(text[field])).not.toBe(text[field]);setLanguage("en");}
 expect(JSON.stringify(text)).not.toMatch(/not a market forecast|not consensus|correlation/);
 }
});
test("NFP +29 versus +133 is still job creation but slower hiring with opposing market channels",()=>{
 const r=reading("payrolls",29,133),x=economicExplanation(r);
 expect(readingVariant(r)).toBe("growingSlower");expect(x.observation).toContain("+29 k (Feb 2024)");expect(x.observation).toContain("+133 k (Jan 2024)");expect(x.observation).toContain("Employment increased");expect(x.observation).toContain("-104 thousand jobs");
 expect(x.economy).toContain("Slower hiring");expect(x.fed).toContain("inflation eases");expect(x.markets).toContain("Lower expected rates");expect(x.markets).toContain("weaker growth and profits");
});
test.each([
 [2,1,"growingFaster"],[1,2,"growingSlower"],[-1,2,"turnNegative"],[-1,-2,"declineEasing"],[-2,-1,"declineDeepening"],[1,-1,"turnPositive"],[0,1,"zero"],[0,-1,"zero"],[1,0,"fromZeroUp"],[-1,0,"fromZeroDown"],[1,1,"equal"],[-1,-1,"equal"],[0,0,"equal"],
] as const)("flow transition %s vs %s selects %s without changing source values",(c,p,variant)=>{
 for(const key of ["payrolls","real_gdp","headline_cpi","real_consumption","retail_sales","average_hourly_earnings"]){const r=reading(key,c,p);expect(readingVariant(r)).toBe(variant);expect(r.raw!.current!.value).toBe(c);expect(r.raw!.previous!.value).toBe(p);}
});
test("negative-but-improving growth and payrolls remain declines",()=>{
 const output=economicExplanation(reading("real_gdp",-1,-2));expect(output.observation).toContain("fell less sharply, but was still falling");expect(output.economy).toContain("still contracting");
 const jobs=economicExplanation(reading("payrolls",-10,-20));expect(jobs.economy).toContain("Job losses");expect(jobs.observation).not.toContain("Employment increased");
});
test("slower positive monthly inflation does not imply falling prices or lower YoY",()=>{
 const r=reading("headline_cpi",.2,.4);r.raw!.context_yoy={current:{value:4,observation_date:"2024-02-01",feature_as_of_date:null},previous:{value:3,observation_date:"2024-01-01",feature_as_of_date:null},three_periods_ago:null};
 const x=economicExplanation(r);expect(x.observation).toContain("Prices still rose, but more slowly");expect(x.economy).toContain("still rose, but more slowly");expect(x.observation).not.toContain("YoY");expect(x.fed).toContain("Sustained");
 const negative=economicExplanation(reading("core_pce",-.1,-.2));expect(negative.observation).toContain("not a price increase");expect(negative.fed).toContain("annual headline PCE");
});
test("CPI, core CPI, core PCE and PPI have distinct mechanisms",()=>{
 const texts=["headline_cpi","core_cpi","core_pce","producer_ppi"].map(key=>economicExplanation(reading(key)));
 expect(new Set(texts.map(t=>t.economy)).size).toBe(4);expect(texts[1].economy).toContain("Prices excluding food and energy");expect(texts[2].fed).toContain("2%");expect(texts[3].economy).toContain("Producer selling prices");expect(texts[3].economy).not.toContain("squeeze margins");
});
test("PMI falling above 50 remains expansion and rising below 50 remains contraction, never percentage growth",()=>{
 const above=economicExplanation(reading("manufacturing_pmi",54.5,54.6));expect(above.observation).toContain("54.50 index points");expect(above.observation).toContain("expansion");expect(above.observation).toContain("softened");expect(above.observation).not.toContain("%");
 const below=economicExplanation(reading("services_pmi",49,47));expect(below.observation).toContain("contraction");expect(below.observation).toContain("improved");expect(below.economy).toContain("Services still contracted");expect(below.markets).not.toMatch(/profits|earnings|price pressure/);
});
test("unemployment, claims and vacancies refer to their own labor measure",()=>{
 expect(economicExplanation(reading("unemployment",4.2,4.1)).observation).toContain("Unemployment was higher");expect(economicExplanation(reading("unemployment")).economy).toContain("participation");
 expect(economicExplanation(reading("initial_claims",210000,200000)).economy).toContain("job losses");expect(economicExplanation(reading("job_openings",7000,6000)).observation).toContain("not completed hires");
});
test("NFCI direction and historical level remain separate; spread does not identify a yield move",()=>{
 const nfci=economicExplanation(reading("nfci",-.49,-.51));expect(nfci.observation).toContain("tightened");expect(nfci.observation).toContain("looser than the historical average");
 const curve=economicExplanation(reading("yield_curve_2s10s",.3,.2));expect(curve.economy).toContain("does not identify which yield");expect(curve.markets).toContain("does not remove recession risk");
});
test("starts and permits, nominal sales, real income, GDP and wages retain their definitions",()=>{
 expect(economicExplanation(reading("housing_starts",1275,1309)).observation).toContain("-34 thousand (annualized)");expect(economicExplanation(reading("building_permits")).economy).toContain("does not guarantee construction");
 expect(economicExplanation(reading("retail_sales")).economy).toContain("includes price changes");expect(economicExplanation(reading("real_disposable_income")).economy).toContain("Income after tax and inflation");expect(economicExplanation(reading("real_gdp")).economy).toContain("annualized, not year-over-year");expect(economicExplanation(reading("average_hourly_earnings")).economy).toContain("Average hourly pay rose faster");
});
test("missing previous period and sub-display noise do not fabricate acceleration",()=>{
 const r=reading("payrolls",29,null),x=economicExplanation(r);expect(x.observation).toContain("+29 k");expect(x.observation).toContain("Previous period unavailable");expect(x.observation).not.toContain("slowed");
 const small=reading("headline_cpi",.300001,.3);expect(readingVariant(small)).toBe("approximatelyEqual");expect(economicExplanation(small).observation).toContain("Practically unchanged");expect(economicExplanation(small).observation).not.toContain("Difference:");
 const missing=reading("services_pmi");missing.raw!.current=null;expect(economicExplanation(missing).observation).toContain("unavailable");
});
test("Fed identifies effective range and last recorded decision without predicting the next one",()=>{
 expect(fedExplanation(prepareFedTarget(undefined)).observation).toContain("unavailable");
 const target={range:"3.00-4.00%",effective:"Jan 1, 2024",lastChange:"+25 bp",raw:{last_rate_change:{effective_date:"2023-12-15"}}} as ReturnType<typeof prepareFedTarget>;
 const text=fedExplanation(target);expect(text.observation).toContain("effective since Jan 1, 2024");expect(text.observation).toContain("Dec 15, 2023");expect(text.fed).toContain("not a new decision today");
});


test("Polish observation retains complete translated facts and concise index units",()=>{
 setLanguage("pl");
 const jobs=tText(economicExplanation(reading("payrolls",29,133)).observation);
 expect(jobs).toContain("Zatrudnienie wzros\u0142o, ale miesi\u0119czny przyrost spowolni\u0142");
 expect(jobs).toContain("R\u00f3\u017cnica: -104 tys. miejsc pracy");
 expect(jobs).not.toMatch(/Employment|monthly|Difference/);
 const pmi=tText(economicExplanation(reading("manufacturing_pmi",54.5,54.6)).observation);
 expect(pmi).toContain("54,50 pkt indeksu");
 expect(pmi).toContain("Sygna\u0142 z badania os\u0142ab\u0142");
 expect(pmi).not.toContain("survey signal");
});

test.each([
 ["industrial_production",.66,.06,"still growing and its monthly growth rate increased"],
 ["industrial_production",.06,.66,"still growing, but its monthly growth rate slowed"],
 ["industrial_production",.2,-.2,"returned to growth"],
 ["industrial_production",-.2,.2,"fell after the previous monthly increase"],
] as const)("production wording selects the actual transition for %s %s vs %s",(key,c,p,phrase)=>{
 const output=economicExplanation(reading(key,c,p));expect(output.observation).toContain(phrase);expect(output.observation).not.toContain(" or ");
});

test("housing explicitly distinguishes annualized seasonally adjusted pace from actual monthly counts",()=>{
 const note=economicExplanation(reading("housing_starts",1221,1288));expect(note.economy).toContain("Seasonally adjusted annualized pace, not actual starts or permits within one month");
});


test.each([
 ["producer_ppi",.4,.2,"rose faster"],["producer_ppi",.2,.4,"still rose, but more slowly"],["producer_ppi",-.1,.2,"fell after"],["producer_ppi",-.1,-.2,"fell less sharply"],["producer_ppi",-.2,-.1,"fell more sharply"],["producer_ppi",.2,-.1,"rose after"],
 ["average_hourly_earnings",.4,.2,"rose faster"],["average_hourly_earnings",.13,.32,"still rose, but more slowly"],["average_hourly_earnings",-.1,.2,"fell after"],["average_hourly_earnings",-.1,-.2,"fell less sharply"],["average_hourly_earnings",-.2,-.1,"fell more sharply"],["average_hourly_earnings",.2,-.1,"returned to growth"],
 ["real_disposable_income",.4,.2,"grew faster"],["real_disposable_income",.2,.4,"still rose, but more slowly"],["real_disposable_income",-.03,.31,"fell after"],["real_disposable_income",-.1,-.2,"fell less sharply"],["real_disposable_income",-.2,-.1,"fell more sharply"],["real_disposable_income",.2,-.1,"returned to growth"],
 ["retail_sales",.4,.2,"grew faster"],["retail_sales",.77,1.29,"still rose, but more slowly"],["retail_sales",-.1,.2,"fell after"],["retail_sales",-.1,-.2,"fell less sharply"],["retail_sales",-.2,-.1,"fell more sharply"],["retail_sales",.2,-.1,"rose after"],
 ["real_consumption",.55,.05,"Consumers bought more"],["real_consumption",.2,.4,"Consumers still bought more"],["real_consumption",-.1,.2,"Consumers bought fewer"],["real_consumption",-.1,-.2,"spending eased"],["real_consumption",-.2,-.1,"fell more sharply"],["real_consumption",.2,-.1,"returned to growth"],
] as const)("%s %s vs %s selects measure-specific economy wording: %s",(key,current,previous,phrase)=>{
 const r=reading(key,current,previous),original=JSON.stringify(r),note=economicExplanation(r);
 expect(note.economy).toContain(phrase);expect(JSON.stringify(r)).toBe(original);
 expect(JSON.stringify(note)).not.toMatch(/real activity|accelerated or resumed|even if its decline slowed|surprise/);
 if(key==="producer_ppi")expect(JSON.stringify(note)).not.toMatch(/squeeze margins|input-cost pressure|producer costs fell/);
 if(key==="average_hourly_earnings"&&current>0)expect(JSON.stringify(note)).not.toMatch(/Lower costs|pay fell|total labor costs fell/);
 setLanguage("pl");for(const field of ["economy","fed","markets"] as const){expect(tText(note[field])).not.toBe(note[field]);expect(tText(note[field])).not.toMatch(/still rose|fell after|producer|income|Retail|Consumers|Average|decline|growth/);}
});

test.each(["manufacturing_pmi","services_pmi"])("%s distinguishes expansion, contraction, threshold, transitions and unchanged readings",key=>{
 const sector=key==="manufacturing_pmi"?"Manufacturing":"Services";
 for(const [c,p,phrase] of [[54.5,54.6,"continued to expand"],[55,54,"stronger survey signal"],[49,47,"still contracted"],[47,49,"stronger contraction signal"],[50,49,"indicating no change"],[51,49,"renewed sector expansion"],[49,51,"shift into sector contraction"],[54,54,"unchanged expansion signal"],[49,49,"unchanged contraction signal"]] as const){
  const x=economicExplanation(reading(key,c,p));expect(x.economy).toContain(phrase);expect(x.economy.toLowerCase()).toContain(sector.toLowerCase());
  expect(x.markets).not.toMatch(/earnings|profits|prices/);setLanguage("pl");for(const field of ["economy","fed","markets"] as const)expect(tText(x[field])).not.toBe(x[field]);setLanguage("en");
 }
});

test.each(["headline_cpi","core_cpi"])("%s direction-specific reason preserves mixed interpretation without inferring YoY",key=>{
 const up=economicExplanation(reading(key,.65,.40)),down=economicExplanation(reading(key,.2,.4));
 expect(up.economy).toMatch(/Faster|faster/);expect(up.markets).toContain("bond yields");expect(down.economy).toContain("still rose, but more slowly");expect(up.observation).not.toContain("YoY");
});

test("Fed channels use only the last confirmed decision direction and retain its date",()=>{
 for(const [bps,phrase,market] of [[25,"last rate increase","higher expected rate path"],[-25,"last rate cut","lower expected rate path"]] as const){
  const target={range:"3.75-4.00%",effective:"Sep 17, 2026",lastChange:`${bps} bp`,raw:{last_rate_change:{effective_date:"2026-09-17",lower_change_bps:bps,upper_change_bps:bps,previous_lower:3.5,previous_upper:3.75}}} as ReturnType<typeof prepareFedTarget>;
  const note=fedExplanation(target);expect(note.economy).toContain(phrase);expect(note.markets).toContain(market);expect(note.fed).toContain("Sep 17, 2026");expect(note.fed).toContain("not a new decision today");
  expect(note.economy).not.toContain(bps>0?"rate cut":"rate increase");setLanguage("pl");expect(tText(note.fed)).not.toMatch(/Last recorded|not a new|next move/);setLanguage("en");
 }
 const unknown=fedExplanation(prepareFedTarget(undefined));expect(unknown.economy).not.toMatch(/last rate increase|last rate cut/);
});
