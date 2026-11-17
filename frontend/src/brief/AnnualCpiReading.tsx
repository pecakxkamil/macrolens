import {useEffect,useState} from 'react';
import {fetchCalendarAgenda,type CalendarResponse} from '../api/macrolens';
import {formatNumber,formatObservationDate} from '../format';
import {warsawDate} from '../datePeriods';
import {et} from '../calendar/earningsPresentation';
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
 return <section className="overview-annual-cpi" aria-label={et('Annual CPI inflation','Roczna inflacja CPI')}>
  <div className="overview-annual-cpi-heading"><span>{et('Annual CPI inflation','Roczna inflacja CPI')}</span><span className="overview-annual-cpi-value">{reading?`${formatNumber(reading.value,1)}%`:'—'}</span></div>
  {reading?<>
   <p>{et('Latest available','Ostatni dostępny')} · <time dateTime={reading.period}>{formatObservationDate(reading.period,'monthly')}</time> · {et('YoY','r/r')} · NSA</p>
   {reading.missing?<p className="overview-annual-cpi-note">{formatObservationDate(reading.measure.reference_period!,'monthly')}: {et('YoY unavailable; missing comparison base','brak odczytu r/r; brak bazy porównawczej')} {formatObservationDate(reading.measure.cpi_missing_base_period!,'monthly')}.</p>:null}
   <a href={reading.measure.source_url} target="_blank" rel="noreferrer" title={reading.measure.cpi_rate_kind==='published_report_rate'?et('Published BLS rate.','Stopa opublikowana przez BLS.'):et('Stored BLS snapshot; rate derived from index levels, rounded to one decimal.','Zapisany snapshot BLS; stopa wyliczona z poziomów indeksu, zaokrąglona do jednego miejsca.')}>{et('Source: BLS','Źródło: BLS')}</a>
  </>:<p role="status">{!loaded?et('Loading annual reading…','Ładowanie odczytu rocznego…'):et('Verified annual CPI reading unavailable.','Zweryfikowany odczyt roczny CPI jest niedostępny.')}</p>}
 </section>;
}
