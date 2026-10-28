import type {CalendarMeasure} from '../api/macrolens';
import {getLanguage,getLocale,tText} from '../i18n/language';
import {measureValue} from './calendarAgenda';

// Labels follow the measure's existing transform, never the publication name.
const names:Record<string,string>={PAYEMS:'Nonfarm payrolls (NFP)',UNRATE:'Unemployment rate',UNEMPLOY:'Unemployed persons',CES0500000003:'Hourly earnings',CPIAUCSL:'CPI',CPILFESL:'Core CPI',PCEPI:'PCE',PCEPILFE:'Core PCE',DSPIC96:'Real disposable income',PCEC96:'Real consumption',PSAVERT:'Saving rate',HOUST:'Housing starts',PERMIT:'Building permits',GDPC1:'Real GDP',ICSA:'Initial jobless claims',CCSA:'Continuing jobless claims',RSAFS:'Nominal retail sales',RSFSXMV:'Retail Sales ex Autos',RETAIL_CONTROL:'Retail Sales Control Group',PPIFIS:'PPI Final Demand',PPIFES:'Core PPI excluding foods and energy',WPSFD49116:'PPI excluding foods, energy and trade services',INDPRO:'Industrial production',TCU:'Capacity utilization',JTSJOL:'JOLTS job openings',HSN1F:'New home sales',MORTGAGE30US:'30Y mortgage rate',CFNAI:'CFNAI',NFCI:'NFCI',ECIALLCIV:'Employment cost index',DGORDER:'Durable goods orders',DFF:'Effective Fed Funds Rate',DGS2:'2Y Treasury yield',DGS10:'10Y Treasury yield',DFII10:'10Y real yield'};
export function compactMeasureName(measure:CalendarMeasure){
 if(measure.feature_name==='target_range')return tText('Fed decision — interest rates');
 if(measure.series_id==='DGORDER'&&measure.feature_name==='mom'){
  const stage=measure.period_provenance?.estimate_stage;
  if(stage==='advance')return tText('Durable goods orders MoM — advance');
  if(stage==='full')return tText('Durable goods orders MoM — full M3');
 }
 if(measure.series_id==='GDPC1'&&measure.feature_name==='qoq_annualized')return tText('Real GDP QoQ, annualized');
 const inflationNames:Record<string,string>={CPIAUCSL:'CPI MoM',CPILFESL:'Core CPI MoM',PCEPI:'PCE inflation MoM',PCEPILFE:'Core PCE MoM'};
 if(measure.feature_name==='mom'&&inflationNames[measure.series_id])return tText(inflationNames[measure.series_id]);
 if(measure.series_id==='PAYEMS'&&measure.feature_name==='monthly_change')return tText('Nonfarm payrolls change (NFP)');
 const base=names[measure.series_id];if(!base)return tText(measure.label);
 const suffix=({mom:'MoM',yoy:'YoY',qoq:'QoQ',qoq_annualized:'QoQ'} as Record<string,string>)[measure.feature_name];
 return `${tText(base)}${suffix?` ${tText(suffix)}`:''}`;
}
export function compactPeriod(measure:CalendarMeasure,publicationDate:string){
 if(measure.feature_name==='target_range')return '';
 const period=measure.reference_period;if(!period)return '';
 const day=new Date(period+'T00:00:00Z');if(!Number.isFinite(day.getTime()))return '';
 const otherYear=period.slice(0,4)!==publicationDate.slice(0,4);
 if(measure.frequency==='quarterly')return `${getLanguage()==='pl'?'kw.':'Q'}${Math.floor(day.getUTCMonth()/3)+1}${otherYear?' '+day.getUTCFullYear():''}`;
 return new Intl.DateTimeFormat(getLocale(),{month:'short',...(measure.frequency!=='monthly'?{day:'numeric' as const}:{}),...(otherYear?{year:'numeric' as const}:{}),timeZone:'UTC'}).format(day);
}
export function compactMeasureValue(value:number|null,unit:string){
 if(value===null||!Number.isFinite(value))return '\u2014';
 if(unit==='percent')return measureValue(value,unit);
 let number=value,suffix='';
 if(['thousand openings','thousands of openings'].includes(unit)&&Math.abs(value)>=1000){number=value/1000;suffix=getLanguage()==='pl'?'mln':'m';}
 else if(['thousand jobs','thousand homes/year (SAAR)','thousand openings','thousands','thousands SAAR','thousands of openings'].includes(unit))suffix=getLanguage()==='pl'?'tys.':'k';
 else if(['index','index points'].includes(unit))suffix=getLanguage()==='pl'?'pkt':'pt';
 const formatted=new Intl.NumberFormat(getLocale(),{maximumFractionDigits:unit==='claims'?0:2}).format(number);
 return `${formatted}${suffix?'\u00a0'+suffix:''}`;
}

export function calendarReadingValue(measure:CalendarMeasure,kind:'actual'|'previous'){
 if(['CFNAI','NFCI'].includes(measure.series_id)&&['index','index points'].includes(measure.unit)&&measure[kind]!==null&&Number.isFinite(measure[kind])){
  const value=Number(measure[kind]!.toFixed(2));
  return new Intl.NumberFormat(getLocale(),{minimumFractionDigits:2,maximumFractionDigits:2}).format(Object.is(value,-0)?0:value)+'\u00a0'+(getLanguage()==='pl'?'pkt':'pt');
 }
 const range=kind==='actual'?measure.actual_range:measure.previous_range;
 if(range&&range.every(Number.isFinite))return `${compactMeasureValue(range[0],'percent').replace('%','')}–${compactMeasureValue(range[1],'percent')}`;
 return compactMeasureValue(measure[kind],measure.unit);
}
