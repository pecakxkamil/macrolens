import type { PreparedReading } from "./readingComparisons";
import { readingNumber } from "./readingComparisons";

export type ReadingVariant = "missing"|"noPrevious"|"equal"|"approximatelyEqual"|"growingFaster"|"growingSlower"|"turnPositive"|"turnNegative"|"declineEasing"|"declineDeepening"|"zero"|"fromZeroUp"|"fromZeroDown"|"higher"|"lower";
export const flows=new Set(["payrolls","average_hourly_earnings","headline_cpi","core_cpi","core_pce","producer_ppi","real_gdp","industrial_production","real_consumption","real_disposable_income","retail_sales"]);
export const prices=new Set(["headline_cpi","core_cpi","core_pce","producer_ppi"]);

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

export const flowFacts: Record<string,Record<string,string>> = {
  "average_hourly_earnings": {
    "growingFaster": "Average hourly pay still rose, and its growth rate increased.",
    "growingSlower": "Average hourly pay still rose, but its growth rate slowed.",
    "turnPositive": "Average hourly pay rose after the previous decline.",
    "turnNegative": "Average hourly pay fell after the previous increase.",
    "declineEasing": "Average hourly pay fell less sharply, but was still falling.",
    "declineDeepening": "Average hourly pay fell more sharply.",
    "fromZeroUp": "Average hourly pay rose after an unchanged period.",
    "fromZeroDown": "Average hourly pay fell after an unchanged period.",
    "zero": "Average hourly pay was unchanged at displayed precision."
  },
  "real_consumption": {
    "growingFaster": "Real consumer spending still rose, and its growth rate increased.",
    "growingSlower": "Real consumer spending still rose, but its growth rate slowed.",
    "turnPositive": "Real consumer spending rose after the previous decline.",
    "turnNegative": "Real consumer spending fell after the previous increase.",
    "declineEasing": "Real consumer spending fell less sharply, but was still falling.",
    "declineDeepening": "Real consumer spending fell more sharply.",
    "fromZeroUp": "Real consumer spending rose after an unchanged period.",
    "fromZeroDown": "Real consumer spending fell after an unchanged period.",
    "zero": "Real consumer spending was unchanged at displayed precision."
  },
  "real_disposable_income": {
    "growingFaster": "Real after-tax income still rose, and its growth rate increased.",
    "growingSlower": "Real after-tax income still rose, but its growth rate slowed.",
    "turnPositive": "Real after-tax income rose after the previous decline.",
    "turnNegative": "Real after-tax income fell after the previous increase.",
    "declineEasing": "Real after-tax income fell less sharply, but was still falling.",
    "declineDeepening": "Real after-tax income fell more sharply.",
    "fromZeroUp": "Real after-tax income rose after an unchanged period.",
    "fromZeroDown": "Real after-tax income fell after an unchanged period.",
    "zero": "Real after-tax income was unchanged at displayed precision."
  },
  "retail_sales": {
    "growingFaster": "Nominal retail sales still rose, and its growth rate increased.",
    "growingSlower": "Nominal retail sales still rose, but its growth rate slowed.",
    "turnPositive": "Nominal retail sales rose after the previous decline.",
    "turnNegative": "Nominal retail sales fell after the previous increase.",
    "declineEasing": "Nominal retail sales fell less sharply, but was still falling.",
    "declineDeepening": "Nominal retail sales fell more sharply.",
    "fromZeroUp": "Nominal retail sales rose after an unchanged period.",
    "fromZeroDown": "Nominal retail sales fell after an unchanged period.",
    "zero": "Nominal retail sales was unchanged at displayed precision."
  },
  "real_gdp": {
    "growingFaster": "Real GDP still rose, and its growth rate increased.",
    "growingSlower": "Real GDP still rose, but its growth rate slowed.",
    "turnPositive": "Real GDP rose after the previous decline.",
    "turnNegative": "Real GDP fell after the previous increase.",
    "declineEasing": "Real GDP fell less sharply, but was still falling.",
    "declineDeepening": "Real GDP fell more sharply.",
    "fromZeroUp": "Real GDP rose after an unchanged period.",
    "fromZeroDown": "Real GDP fell after an unchanged period.",
    "zero": "Real GDP was unchanged at displayed precision."
  },
  "payrolls": {
    "growingFaster": "Employment still rose, and its growth rate increased.",
    "growingSlower": "Employment increased, but the monthly gain slowed.",
    "turnPositive": "Employment rose after the previous decline.",
    "turnNegative": "Employment fell after the previous increase.",
    "declineEasing": "Employment fell less sharply, but was still falling.",
    "declineDeepening": "Employment fell more sharply.",
    "fromZeroUp": "Employment rose after an unchanged period.",
    "fromZeroDown": "Employment fell after an unchanged period.",
    "zero": "Employment was unchanged at displayed precision."
  }
};
