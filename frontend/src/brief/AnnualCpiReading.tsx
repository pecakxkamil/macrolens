import {IndicatorName} from "./IndicatorName";
import {useEffect,useState} from 'react';
import {fetchCalendarAgenda,type CalendarResponse} from '../api/macrolens';
import {formatNumber,formatObservationDate} from '../format';
import {warsawDate} from '../datePeriods';
import {et} from '../calendar/earningsPresentation';
import {InfoTooltip} from '../components/InfoTooltip';
import {MacroTrend} from '../calendar/MacroTrend';
import {InterpretationMarker} from './InterpretationMarker';
import {usdInflationInterpretation} from './usdInterpretation';
import './annualCpiReading.css';

const month=(value:string|null|undefined):value is string=>typeof value==='string'&&/^\d{4}-(0[1-9]|1[0-2])-01$/.test(value);
const finite=(value:unknown):value is number=>typeof value==='number'&&Number.isFinite(value);

export function annualCpiReading(data:CalendarResponse,now:Date){
 const today=warsawDate(now);
 const candidates=(data&&Array.isArray(data.events)?data.events:[])
  .filter(event=>event.release_date<today||(event.release_date===today&&event.release_datetime_utc!==null&&Date.parse(event.release_datetime_utc)<=now.getTime()))
  .flatMap(event=>event.measures??[])
  .filter(m=>m.series_id==='CPIAUCSL'&&m.feature_name==='yoy'&&m.mapping_status==='confirmed'&&m.selected_source==='bls:cpi'&&m.cpi_contract_id==='bls:cpi:CUUR0000SA0:yoy:NSA'&&m.seasonal_adjustment==='NSA'&&['derived_index_rate','published_report_rate'].includes(m.cpi_rate_kind??'')&&month(m.reference_period))
  .sort((a,b)=>b.reference_period!.localeCompare(a.reference_period!));
 const measure=candidates[0];if(!measure)return null;
 if(measure.result_status==='available'&&finite(measure.actual))return {measure,value:measure.actual,period:measure.reference_period!,missing:false};
 if(measure.result_status==='publisher_unavailable'&&measure.missing_reason?.actual==='publisher_base_unavailable'&&measure.cpi_missing_proof?.missing_confirmed===true&&month(measure.cpi_missing_base_period)&&measure.cpi_missing_base_period===`${Number(measure.reference_period!.slice(0,4))-1}${measure.reference_period!.slice(4)}`&&measure.previous_kind==='previous_period'&&month(measure.previous_period)&&measure.previous_period<measure.reference_period!&&finite(measure.previous)&&measure.comparison_status==='same_cpi_capture')
  return {measure,value:measure.previous,period:measure.previous_period,missing:true};
 return null;
}

export function AnnualCpiReading({revision,now}:{revision:string;now:Date}){
 const [showTrend,setShowTrend]=useState(false);
 const through=warsawDate(now),key=revision+'|'+through;
 const [state,setState]=useState<{key:string;data?:CalendarResponse;error?:boolean}>();
 useEffect(()=>{
  const abort=new AbortController();const start=new Date(through+'T00:00:00Z');start.setUTCDate(start.getUTCDate()-90);
  fetchCalendarAgenda(start.toISOString().slice(0,10),through,abort.signal)
   .then(data=>{if(!abort.signal.aborted)setState({key,data});})
   .catch(()=>{if(!abort.signal.aborted)setState({key,error:true});});
  return()=>abort.abort();
 },[key]);
 const loaded=state?.key===key,reading=loaded&&state.data?annualCpiReading(state.data,now):null;
 const title=et('CPI YoY','Inflacja CPI r/r');
 const previousDate=reading?new Date(reading.period+'T00:00:00Z'):null;
 previousDate?.setUTCMonth(previousDate.getUTCMonth()-1);
 const previousPeriod=previousDate?.toISOString().slice(0,10);
 const history=previousPeriod?reading?.measure.cpi_history?.[previousPeriod]:undefined;
 const previous=reading&&!reading.missing&&reading.measure.previous_period===previousPeriod&&reading.measure.previous_kind==='previous_period'&&reading.measure.comparison_status==='same_cpi_capture'&&finite(reading.measure.previous)
  ?reading.measure.previous:typeof history==='string'&&history.trim()!==''&&Number.isFinite(Number(history))?Number(history):null;
 const difference=reading&&previous!==null?reading.value-previous:null;
 const interpretation=reading&&previous!==null?usdInflationInterpretation(reading.value,previous):null;
 const note=reading?`${et('Annual CPI, not seasonally adjusted. Source: BLS.','Roczna inflacja CPI, bez wyrównania sezonowego. Źródło: BLS.')} ${reading.missing?`${formatObservationDate(reading.measure.reference_period!,'monthly')}: ${et('YoY unavailable; missing comparison base','brak odczytu r/r; brak bazy porównawczej')} ${formatObservationDate(reading.measure.cpi_missing_base_period!,'monthly')}. ${et('Latest available reading shown.','Pokazano ostatni dostępny odczyt.')}`:''} ${reading.measure.cpi_rate_kind==='published_report_rate'?et('Published BLS rate.','Stopa opublikowana przez BLS.'):et('Derived from index levels, rounded to one decimal; history may include revisions.','Wyliczona z poziomów indeksu, zaokrąglona do jednego miejsca; historia może zawierać rewizje.')}`
  :!loaded?et('Loading annual reading…','Ładowanie odczytu rocznego…'):et('Verified annual CPI reading unavailable.','Zweryfikowany odczyt roczny CPI jest niedostępny.');
 return <>
  <tr className="overview-reading-row overview-annual-cpi" aria-label={title}>
   <th scope="row"><div className="overview-reading-heading"><span className="overview-reading-label"><IndicatorName href="#/explore/indicators/CPIAUCSL" label={title} period={reading?<time dateTime={reading.period}>{formatObservationDate(reading.period,'monthly')}</time>:<span role="status" className="visually-hidden">{note}</span>}><span className="overview-reading-actions">
    {reading&&Object.keys(reading.measure.cpi_history??{}).length>0?<button type="button" className="overview-chart-button" aria-label={et('View chart: CPI YoY','Pokaż wykres: Inflacja CPI r/r')} aria-expanded={showTrend} onClick={()=>setShowTrend(value=>!value)}><svg aria-hidden="true" width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v14h14M5 12l4-4 3 2 4-6"/></svg></button>:null}
    <span className="overview-explanation"><InfoTooltip label={title} description={note} trigger="i" bounded content={<><span>{note}</span>{reading?<a href={reading.measure.source_url} target="_blank" rel="noreferrer"> BLS</a>:null}</>}/></span>
   </span></IndicatorName></span></div></th>
   <td className="overview-value--latest"><div className="overview-value"><div className="overview-reading-number"><span className="overview-reading-primary"><strong><span className="overview-number">{reading?formatNumber(reading.value,1):'—'}</span>{reading?<small className="overview-inline-unit">%</small>:null}</strong><span className="overview-reading-markers"><span className={`overview-change overview-change--${difference===null||difference===0?'neutral':difference>0?'positive':'negative'}`}><InfoTooltip label={title+' '+et('change','zmiana')} description={note} trigger={difference===null||difference===0?'—':difference>0?'↑':'↓'} closable bounded/></span><InterpretationMarker label={title} interpretation={interpretation}/></span></span></div></div></td>
   <td className="overview-value--earlier"><strong>{previous!==null?<><span className="overview-number">{formatNumber(previous,1)}</span><small className="overview-inline-unit">%</small></>:'—'}</strong>{previous!==null?<time dateTime={previousPeriod}>{formatObservationDate(previousPeriod!,'monthly')}</time>:null}</td>
  </tr>
  {showTrend&&reading?<tr className="overview-annual-cpi-trend"><td colSpan={3}><MacroTrend measure={{...reading.measure,reference_period:reading.period,actual:reading.value}}/></td></tr>:null}
 </>;
}
