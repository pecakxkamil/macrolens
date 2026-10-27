import type { PreparedReading } from "./readingComparisons";
import { readingNumber, readingUnit } from "./readingComparisons";
import type { PreparedFedTarget } from "./fedTarget";
import { getLanguage, tText } from "../i18n/language";
import { formatObservationDate } from "../format";
import { explanationCopy, flowFacts, type ExplanationChannels } from "./economicExplanationCopy";

export interface EconomicExplanation extends ExplanationChannels { observation: string }
export type ReadingVariant = "missing"|"noPrevious"|"equal"|"approximatelyEqual"|"growingFaster"|"growingSlower"|"turnPositive"|"turnNegative"|"declineEasing"|"declineDeepening"|"zero"|"fromZeroUp"|"fromZeroDown"|"higher"|"lower";
const groups:Record<string,string>={payrolls:"payroll",unemployment:"unemployment",initial_claims:"claims",job_openings:"jolts",average_hourly_earnings:"wages",headline_cpi:"cpi",core_cpi:"coreCpi",core_pce:"corePce",producer_ppi:"ppi",real_gdp:"activity",industrial_production:"production",real_consumption:"consumption",real_disposable_income:"income",retail_sales:"retail",housing_starts:"starts",building_permits:"permits",mortgage_rate:"mortgage",manufacturing_pmi:"manufacturingPmi",services_pmi:"servicesPmi",nfci:"nfci",yield_curve_2s10s:"curve"};
const flows=new Set(["payrolls","average_hourly_earnings","headline_cpi","core_cpi","core_pce","producer_ppi","real_gdp","industrial_production","real_consumption","real_disposable_income","retail_sales"]);
const prices=new Set(["headline_cpi","core_cpi","core_pce","producer_ppi"]);

// Compare what the table displays before choosing sign-sensitive wording.
// No classification, trend estimate or consensus comparison is calculated here.
export function readingVariant(reading:PreparedReading):ReadingVariant {
 const raw=reading.raw;
 if(!raw?.current || !Number.isFinite(raw.current.value))return "missing";
 if(!raw.previous || !Number.isFinite(raw.previous.value))return "noPrevious";
 const current=raw.current.value,previous=raw.previous.value;
 if(reading.current.screenValue===reading.previous.screenValue)return current===previous?"equal":"approximatelyEqual";
 const precision=["claims","persons","thousands SAAR"].includes(raw.unit)?0:reading.key==="unemployment"?1:2;
 const c=Number(current.toFixed(precision)),p=Number(previous.toFixed(precision));
 if(!flows.has(reading.key))return c>p?"higher":"lower";
 const rounded=readingNumber(c,raw.unit,reading.key==="unemployment"?1:undefined);
 if(c===0 || /^[-+]?0([.,]0+)?$/.test(rounded))return "zero";
 if(p===0)return c>0?"fromZeroUp":"fromZeroDown";
 if(c>0&&p<0)return "turnPositive";
 if(c<0&&p>0)return "turnNegative";
 if(c>0)return c>p?"growingFaster":"growingSlower";
 return c>p?"declineEasing":"declineDeepening";
}
export function flowFact(reading:PreparedReading,variant:ReadingVariant):string {
 if(flowFacts[reading.key]?.[variant])return flowFacts[reading.key][variant];
 if(variant==="approximatelyEqual")return "Practically unchanged at displayed precision.";
 const c=reading.raw!.current!.value;
 if(variant==="equal")return c>0?"The positive pace was unchanged.":c<0?"The negative pace was unchanged.":"No change in either period.";
 if(variant==="zero")return c===0?"No change in the measured level during this period.":"The measured level was practically unchanged at displayed precision.";
 if(reading.key==="industrial_production")return ({growingFaster:"Production is still growing and its monthly growth rate increased.",growingSlower:"Production is still growing, but its monthly growth rate slowed.",turnPositive:"Production returned to growth after the previous monthly decline.",turnNegative:"Production fell after the previous monthly increase.",declineEasing:"The monthly production decline eased, but production is still falling.",declineDeepening:"The monthly production decline deepened.",fromZeroUp:"Production grew after an unchanged month.",fromZeroDown:"Production fell after an unchanged month."} as Record<string,string>)[variant]??"Previous period unavailable.";
 if(reading.key==="payrolls"&&variant==="growingSlower")return "Employment increased, but the monthly gain slowed.";
 if(prices.has(reading.key))return ({growingFaster:"Prices still rose, more quickly than before.",growingSlower:"Prices still rose, but more slowly.",turnPositive:"Prices rose after the previous decline.",turnNegative:"Prices fell after the previous increase.",declineEasing:"Prices fell less sharply; this is not a price increase.",declineDeepening:"The price decline deepened.",fromZeroUp:"Prices rose after an unchanged reading.",fromZeroDown:"Prices fell after an unchanged reading."} as Record<string,string>)[variant]??"Previous period unavailable.";
 return ({growingFaster:"Still growth, faster than before.",growingSlower:"Still growth, but slower than before.",turnPositive:"Growth after the previous decline.",turnNegative:"A decline after the previous increase.",declineEasing:"The decline became smaller; this is not growth.",declineDeepening:"The decline deepened.",fromZeroUp:"Growth after an unchanged reading.",fromZeroDown:"A decline after an unchanged reading."} as Record<string,string>)[variant]??"Previous period unavailable.";
}
function levelFact(reading:PreparedReading,variant:ReadingVariant):string {
 const c=reading.raw!.current!.value;
 const same=variant==="equal"?"The level was unchanged.":variant==="approximatelyEqual"?"Practically unchanged at displayed precision.":"";
 if(["manufacturing_pmi","services_pmi"].includes(reading.key)){
  const position=c>50?"Above 50: the sector survey still indicates expansion.":c<50?"Below 50: the sector survey still indicates contraction.":"At 50: no sector change indicated.";
  return `${position} ${same || (variant==="higher"?"The survey signal improved.":"The survey signal softened.")}`;
 }
 if(reading.key==="nfci")return `${same || (variant==="higher"?"Financial conditions tightened.":"Financial conditions eased.")} ${c<0?"Still looser than the historical average.":c>0?"Still tighter than the historical average.":"At the historical average."}`;
 const direction:Record<string,[string,string]>={unemployment:["Unemployment was higher.","Unemployment was lower."],initial_claims:["More new benefit claims.","Fewer new benefit claims."],job_openings:["More unfilled positions, not completed hires.","Fewer unfilled positions, not completed hires."],housing_starts:["More construction starts at an annualized pace.","Fewer construction starts at an annualized pace."],building_permits:["More building permits at an annualized pace.","Fewer building permits at an annualized pace."],mortgage_rate:["Mortgage financing became more expensive.","Mortgage financing became cheaper."],yield_curve_2s10s:["The 10Y minus 2Y spread widened.","The 10Y minus 2Y spread narrowed."]};
 return same || direction[reading.key]?.[variant==="higher"?0:1] || "Previous period unavailable.";
}
function pointText(reading:PreparedReading,which:"current"|"previous"):string {
 const point=reading[which], value=reading.raw?.[which]?.value;
 const signed=flows.has(reading.key)&&value!==undefined&&value>0?"+":"";
 const unit=reading.raw?.unit==="index"?(getLanguage()==="pl"?" pkt indeksu":" index points"):"";
 return `${signed}${point.display}${unit} (${point.period})`;
}
function observation(reading:PreparedReading,variant:ReadingVariant):string {
 if(variant==="missing")return `${reading.label}: current reading unavailable.`;
 if(variant==="noPrevious"){
  const value=reading.raw!.current!.value;
  const fact=flows.has(reading.key)?value>0?"The measured level increased.":value<0?"The measured level declined.":"The measured level was unchanged.":"";
  return `${reading.label}: ${pointText(reading,"current")} — ${fact ? tText(fact).replace(/\.$/, "") + "; " : ""}Previous period unavailable; no comparison inferred.`;
 }
 const fact=flows.has(reading.key)?flowFact(reading,variant):levelFact(reading,variant);
 const raw=reading.raw!;
 let difference="";
 if(!["equal","approximatelyEqual"].includes(variant)&&raw.change!==null&&Number.isFinite(raw.change)){
  const precision=["claims","persons","thousands","thousands SAAR","thousands of openings"].includes(raw.unit)?0:2;
  const delta=Number(raw.change.toFixed(precision));
  if(delta!==0)difference=`; Difference: ${delta>0?"+":""}${readingNumber(delta,"",precision)} ${raw.change_unit==="percentage points"?"percentage points":raw.change_unit==="index points"?(getLanguage()==="pl"?"pkt indeksu":"index points"):raw.change_unit==="thousands SAAR"?"thousand (annualized)":readingUnit(raw.change_unit)}`;
 }
 return `${reading.label}: ${pointText(reading,"current")} vs ${pointText(reading,"previous")} — ${tText(fact).replace(/\.\s+/g, "; ").replace(/\.$/, "")}${difference}.`;
}
const neutral:ExplanationChannels={economy:"This comparison adds no directional change at displayed precision; the current level and wider context still matter.",fed:"Inflation and broader labor and activity data are needed to assess the policy case.",markets:"Other news can still change expected rates and profits; this comparison alone adds no clear new impulse."};
const negativeJobs:ExplanationChannels={economy:"Job losses can weaken household income and consumption, even when the decline becomes smaller.",fed:"Sustained job losses may strengthen easing arguments if inflation permits.",markets:"Lower expected rates may help valuations, while weaker demand and profits may weigh on equities."};
const negativeActivity:ExplanationChannels={economy:"The measured level contracted; a smaller decline is improvement, not expansion. Demand and revenues may weaken.",fed:"Persistent contraction could support easing if inflation is moderating.",markets:"Lower expected rates may support valuations, while contraction and weaker earnings may work against equities."};
const negativePrices:ExplanationChannels={economy:"Consumer prices fell, increasing purchasing power for unchanged nominal incomes.",fed:"Persistent demand-driven price declines may support easing if spending is weakening.",markets:"Lower inflation and rate expectations may reduce bond yields and support equity valuations."};
export function economicExplanation(reading:PreparedReading):EconomicExplanation {
 const variant=readingVariant(reading),group=groups[reading.key],entry=explanationCopy[group];
 let channels=neutral;
 if(variant==="missing")channels={economy:"Current data are unavailable; economic implications cannot be assessed.",fed:"No policy argument is inferred from missing data.",markets:"No market implication is inferred from missing data."};
 else if(variant==="noPrevious")channels={economy:"The current reading is available, but its change cannot be assessed without the previous period.",fed:"The level alone does not establish the next policy decision.",markets:"Growth and discount-rate channels depend on the wider context."};
 else if(entry&&!["equal","approximatelyEqual","zero"].includes(variant)){
  const raw=reading.raw!,c=raw.current!.value,p=raw.previous!.value;
  channels=c>p?entry.up:entry.down;
  if(flows.has(reading.key)&&c<0)channels=entry.negative??(prices.has(reading.key)?negativePrices:reading.key==="payrolls"?negativeJobs:negativeActivity);
  channels={...channels,...entry.variants?.[variant]};
 }
 if(["housing_starts","building_permits"].includes(reading.key))channels={...channels,economy:`Seasonally adjusted annualized pace, not actual starts or permits within one month. ${channels.economy}`};
 // Sector and transformation qualifications remain specific, even for unchanged data.
 if(variant==="missing")return {observation:observation(reading,variant),...channels};
 if(group==="manufacturingPmi"||group==="servicesPmi"){
  const c=Number(reading.raw!.current!.value.toFixed(2)),previous=reading.raw!.previous;
  if(previous){
   const p=Number(previous.value.toFixed(2)),same=["equal","approximatelyEqual"].includes(variant);
   const position=c===50?"atThreshold":c>50?(same?"expandingUnchanged":p<=50?"expansionResumed":c>p?"expandingFaster":"expandingSlower"):(same?"contractingUnchanged":p>=50?"contractionStarted":c>p?"contractingEasing":"contractingDeepening");
   channels={...channels,...entry.variants![position]};
  }
 }
 if(reading.key==="real_gdp")channels={...channels,economy:`Quarterly growth is annualized, not year-over-year. ${channels.economy}`};
 if(reading.key==="industrial_production")channels={...channels,economy:`This measures industry, not the whole economy. ${channels.economy}`};
 if(reading.key==="core_pce"&&["equal","approximatelyEqual","zero","noPrevious"].includes(variant))channels={...channels,fed:"The Fed tracks core PCE for underlying pressure; its 2% goal concerns annual headline PCE, not this monthly core rate."};
 if(reading.key==="core_pce"&&!channels.fed.includes("2%"))channels={...channels,fed:`${channels.fed} Its 2% goal concerns annual headline PCE.`};
 if(reading.key==="core_cpi"&&reading.raw?.current&&reading.raw.current.value<0)channels={...channels,economy:"Prices excluding food and energy fell, easing that part of household spending costs."};
 if(group==="curve")channels={...channels,markets:entry.up.markets};
 return {observation:observation(reading,variant),...channels};
}
export function fedExplanation(target:PreparedFedTarget):EconomicExplanation {
 const change=target.raw?.last_rate_change;
 const last=change?` Last recorded rate change: ${target.lastChange} (${formatObservationDate(change.effective_date,"daily")}).`:" Last rate change unavailable.";
 const valid=target.range!=="\u2014"&&change&&[change.lower_change_bps,change.upper_change_bps,change.previous_lower,change.previous_upper].every(Number.isFinite);
 const up=valid&&change!.lower_change_bps>=0&&change!.upper_change_bps>=0&&(change!.lower_change_bps>0||change!.upper_change_bps>0);
 const down=valid&&change!.lower_change_bps<=0&&change!.upper_change_bps<=0&&(change!.lower_change_bps<0||change!.upper_change_bps<0);
 return {observation:target.range==="\u2014"?"Fed target range unavailable.":`Fed target range: ${target.range}, effective since ${target.effective}.${last}`,
 economy:up?"The last rate increase raised short-term funding costs and works to restrain borrowing and spending.":down?"The last rate cut lowered short-term funding costs and can support borrowing and spending.":"The stored target range describes overnight policy rates; the direction of its last change is unavailable.",
 fed:change?`Last recorded decision effective since: ${formatObservationDate(change.effective_date,"daily")}; this is not a new decision today. The next move depends mainly on inflation and employment.`:"Last rate change unavailable; the next decision depends on inflation and employment.",
 markets:up?"A higher expected rate path raises financing costs and can weigh on equity valuations; prior market pricing matters.":down?"A lower expected rate path can ease financing costs and support equity valuations; prior market pricing matters.":"Market pricing depends on the expected future policy-rate path."};
}
