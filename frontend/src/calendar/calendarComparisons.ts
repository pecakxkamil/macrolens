import type {CalendarMeasure} from '../api/macrolens';
import {getLanguage,getLocale} from '../i18n/language';
import {compactMeasureName} from './calendarPresentation';

type ComparisonKind='forecast'|'previous';
export type Comparison={text:string;explanation:string;tone:'favorable'|'unfavorable'|'neutral'};
// Economic interpretation only. Every unlisted series/transform stays neutral.
export const comparisonRules:Record<string,'higher'|'lower'>={
 'PAYEMS:monthly_change':'higher',
 'UNRATE:raw':'lower',
 'ICSA:raw':'lower',
 'CCSA:raw':'lower',
};
const finite=(n:number|null)=>n!==null&&Number.isFinite(n);
function confirmedMeasure(m:CalendarMeasure){
 const date=m.reference_period?new Date(m.reference_period+'T00:00:00Z'):null;
 if(m.mapping_status!=='confirmed'||!date||!Number.isFinite(date.getTime())||date.toISOString().slice(0,10)!==m.reference_period)return false;
 if(['mom','yoy','qoq','qoq_annualized'].includes(m.feature_name)&&m.unit!=='percent')return false;
 if(m.series_id==='PAYEMS'&&m.feature_name==='monthly_change'&&!['thousand jobs','thousands'].includes(m.unit))return false;
 if(['ICSA','CCSA'].includes(m.series_id)&&m.feature_name==='raw'&&m.unit!=='claims')return false;
 return true;
}
function priorPeriod(m:CalendarMeasure){
 if(!m.reference_period)return null;
 const date=new Date(m.reference_period+'T00:00:00Z');
 if(!Number.isFinite(date.getTime()))return null;
 if(m.frequency==='monthly')date.setUTCMonth(date.getUTCMonth()-1);
 else if(m.frequency==='quarterly')date.setUTCMonth(date.getUTCMonth()-3);
 else if(m.frequency==='weekly')date.setUTCDate(date.getUTCDate()-7);
 else if(m.frequency==='daily')date.setUTCDate(date.getUTCDate()-1);
 else return null;
 return date.toISOString().slice(0,10);
}
export function comparableForecast(m:CalendarMeasure){
 // Consensus is a field of this publication's measure, sharing its unit,
 // transform and reference period. No fallback from previous/model values.
 return m.consensus_status==='available'&&confirmedMeasure(m)&&finite(m.forecast);
}
export function calendarComparison(m:CalendarMeasure,kind:ComparisonKind):Comparison|null{
 if(kind==='previous'&&m.comparison_status==='mixed_sources')return null;
 if(!confirmedMeasure(m)||!finite(m.actual))return null;
 const base=kind==='forecast'?m.forecast:m.previous;
 if(!finite(base))return null;
 if(kind==='forecast'&&!comparableForecast(m))return null;
 if(m.feature_name==='target_range'&&(!m.actual_range||!m.previous_range||Math.abs((m.actual_range[1]-m.previous_range[1])-(m.actual_range[0]-m.previous_range[0]))>1e-9))return null;
 if(kind==='previous'&&!(m.previous_kind==='previous_decision'?m.feature_name==='target_range'&&!!m.previous_period:m.previous_kind==='previous_estimate'
  ?m.series_id==='GDPC1'&&m.previous_period===m.reference_period
  :m.previous_kind==='previous_period'&&m.previous_period===priorPeriod(m)))return null;
 const delta=m.actual!-base!,pl=getLanguage()==='pl';
 if(!Number.isFinite(delta))return null;
 const digits=m.unit==='claims'?0:m.unit==='USD bn'?3:2;
 const rounded=Number(delta.toFixed(digits));
 const amount=new Intl.NumberFormat(getLocale(),{minimumFractionDigits:['CFNAI','NFCI'].includes(m.series_id)?2:0,maximumFractionDigits:digits}).format(Math.abs(rounded));
 const unit=m.unit==='percent'?(pl?'pkt proc.':'pp')
  :['index','index points'].includes(m.unit)?(pl?'pkt indeksu':'index pts')
  :m.unit==='claims'?(pl?'wniosków':'claims')
  :m.unit==='thousand jobs'?(pl?'tys. miejsc pracy':'k jobs')
  :['thousands','thousands SAAR','thousand homes/year (SAAR)','thousand openings','thousands of openings'].includes(m.unit)?(pl?'tys.':'k')
  :m.unit==='hours'?(pl?'godz.':'hours'):m.unit==='USD bn'?(pl?'mld USD':'USD bn'):m.unit;
 const absolute=`${amount}${unit?'\u00a0'+unit:''}`;
 const shortUnit=m.unit==='thousand jobs'?(pl?'tys.':'k'):['index','index points'].includes(m.unit)?(pl?'pkt':'pt'):unit;
 const text=`${rounded>0?'+':rounded<0?'−':''}${amount}${shortUnit?'\u00a0'+shortUnit:''}`;
 const rule=comparisonRules[`${m.series_id}:${m.feature_name}`];
 const contradictory=m.series_id==='PAYEMS'&&m.actual!<0&&delta>0;
 const tone=rounded===0||!rule||contradictory?'neutral':(delta>0)===(rule==='higher')?'favorable':'unfavorable';
 const reference=kind==='forecast'?(pl?'konsensusu':'consensus'):m.previous_kind==='previous_estimate'?(pl?'poprzedniego szacunku tego samego kwartału':'the previous estimate of the same quarter'):m.previous_kind==='previous_decision'?(pl?'poprzedniej decyzji':'the previous decision'):(pl?'poprzedniego okresu':'the previous period');
 let explanation=rounded===0?(pl?`Bez różnicy względem ${reference} przy prezentowanej precyzji.`:`No difference from ${reference} at displayed precision.`)
  :pl?`${compactMeasureName(m)}: o ${absolute} ${delta>0?'więcej':'mniej'} względem ${reference}.`:`${compactMeasureName(m)}: ${absolute} ${delta>0?'higher':'lower'} than ${reference}.`;
 if(m.series_id==='PAYEMS'&&m.feature_name==='monthly_change'&&rounded!==0){
  explanation=pl?`${m.actual!>0?'Przyrost zatrudnienia':'Zmiana zatrudnienia'} o ${absolute} ${m.actual!>0?(delta>0?'większy':'mniejszy'):(delta>0?'większa':'mniejsza')} niż ${kind==='forecast'?'zakładał konsensus':'w poprzednim miesiącu'}.`:`${m.actual!>0?'The job gain':'Employment change'} was ${absolute} ${delta>0?'larger':'smaller'} than ${kind==='forecast'?'consensus expected':'in the previous month'}.`;
  if(m.actual!<=0)explanation+=m.actual!<0?(pl?' Zatrudnienie nadal spadało.':' Employment still fell.'):(pl?' Zatrudnienie bez zmian.':' Employment was unchanged.');
 }
 if(m.series_id==='UNRATE'&&m.feature_name==='raw'&&rounded!==0)explanation=pl?`Stopa bezrobocia o ${absolute} ${delta>0?'wyższa':'niższa'} ${kind==='forecast'?'od prognozy':'niż w poprzednim okresie'}.`:`The unemployment rate was ${absolute} ${delta>0?'higher':'lower'} than ${kind==='forecast'?'forecast':'in the previous period'}.`;
 if(['ICSA','CCSA'].includes(m.series_id)&&m.feature_name==='raw'&&rounded!==0)explanation=pl?`O ${absolute} ${delta>0?'więcej':'mniej'} niż ${kind==='forecast'?'zakładał konsensus':'w poprzednim tygodniu'}.`:`${amount} ${delta>0?'more':'fewer'} claims than ${kind==='forecast'?'consensus expected':'in the previous week'}.`;
 if(kind==='previous'&&m.previous_kind==='previous_estimate'&&m.revision_confirmed)explanation+=pl?' Potwierdzona rewizja.':' Confirmed revision.';
 if(kind==='previous'&&m.series_id==='DGORDER'&&m.period_provenance?.estimate_stage==='full')explanation+=pl?' Pełny raport M3 dla tego samego miesiąca; porównanie dotyczy poprzedniego miesiąca, nie wstępnego szacunku.':' Full M3 report for the same month; this compares the previous month, not the advance estimate.';
 if(m.data_version==='current_vintage'||(kind==='previous'&&m.previous_data_version==='current_vintage'))explanation+=pl?' Dane mogą zawierać późniejsze rewizje.':' Values may include later revisions.';
 return {text,explanation,tone};
}
