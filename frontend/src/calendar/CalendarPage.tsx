import {Fragment,useCallback,useEffect,useMemo,useState} from 'react';
import {fetchCalendarAgenda,requestOverviewRefresh,type CalendarEvent,type CalendarMeasure,type CalendarResponse} from '../api/macrolens';
import {useBackgroundRefresh} from '../brief/useOverviewRefresh';
import {availabilityTime,checkStatusLabel} from '../brief/sourceCheckPresentation';
import {eventInstant,eventImportanceStars} from '../brief/upcomingEvents';
import {formatObservationDate} from '../format';
import {tText,tLabel} from '../i18n/language';
import {formatAgendaDate,formatCalendarDate,formatPolandTime} from './calendarDates';
import {calendarComparison,comparableForecast} from './calendarComparisons';
import {ComparisonTooltip} from './ComparisonTooltip';
import {compactMeasureName,compactPeriod,compactMeasureValue,calendarReadingValue} from './calendarPresentation';
import {calendarCategories,countdownText,countdownDelay,filterEvents,groupAgenda,nextInstant,presetRange,rangeError,resultPending,type DatePreset} from './calendarAgenda';

const presets:Array<[DatePreset,string]>=[['yesterday','Yesterday'],['today','Today'],['tomorrow','Tomorrow'],['week','This week'],['nextWeek','Next week'],['custom','Date range']];
const identity=(e:CalendarEvent)=>e.event_id??`${e.release_id}:${e.release_date}`;
const safeLink=(url:string|null|undefined)=>url&&/^https?:\/\//.test(url)?url:null;
const versionLabel=(version:string|null)=>version==='stored_date_vintage'?'Stored date-level vintage':version==='current_vintage'?'Current-vintage value':version==='official_release'?'Official announcement':'Result unavailable';

function CalendarCheckStatus({data,refresh}:{data:CalendarResponse;refresh:CalendarResponse['refresh']}){
 const check=data.check,failures=refresh?.results.filter(row=>(row.status==='error'||row.status==='skipped')&&(row.resource==='overview'||check?.required_resources.includes(row.resource)))??[];
 const failed=refresh?.status==='error'||check?.status==='error'||failures.length>0;
 const label=refresh?.status==='running'?'Checking availability of new data…':failed?'Unable to check some sources — stored data shown.':check?.status==='complete'?'Sources checked:':check?.checked_at?'Some sources checked:':'Selected range not yet verified.';
 return <div className="calendar-check"><span role="status" aria-live="polite">{tText(label)} {refresh?.status!=='running'&&!failed&&check?.checked_at?<time dateTime={check.checked_at}>{availabilityTime(check.checked_at)}</time>:null}</span></div>;
}
function fallbackMeasures(event:CalendarEvent):CalendarMeasure[]{return event.series.map(s=>({series_id:s.series_id,label:s.short_name||s.name,feature_name:'raw',frequency:s.frequency,unit:s.unit||'',reference_period:null,previous_period:null,previous_kind:'previous_period',actual:null,previous:null,forecast:null,consensus_status:'not_integrated',data_version:null,revision_confirmed:false,binding_method:null,vintage_date:null,realtime_end:null,result_status:'awaiting_data',mapping_status:'reference_period_unconfirmed',source_url:`https://fred.stlouisfed.org/series/${s.series_id}`}));}
function calendarMissingReason(reason:string){return ({retail_component_missing:'A required retail component or month is missing.',retail_component_invalid:'A retail component is not a finite nonnegative sales level.',retail_component_vintage_mismatch:'Retail components do not share one stored FRED current-vintage snapshot; versions are not mixed.',retail_denominator_invalid:'The retail aggregate must have a positive finite level and denominator.',ism_report_not_confirmed:'No validated ISM document matches this report month; an older report is not a new result.',revised_permits_provider_pending:'Census has published the revised permits, but a matching result has not yet been confirmed in FRED.',publication_stage_unconfirmed:'The revised publication stage has not been confirmed; the stored value is not assigned to it.',publisher_result_not_confirmed:'The stored snapshot predates this publication; a new result has not been confirmed.',claims_weeks_not_confirmed:'No official report or schedule confirms the separate claims weeks for this publication.',release_mapping_not_supported:'This publication has no supported series and transformation mapping.',publisher_schedule_no_matching_period:'No unambiguous matching period was found in the stored publisher schedules.',not_yet_published:'This confirmed period has not yet been published.',reference_period_unconfirmed:'No publisher evidence confirms the reference period for this event.',observation_missing:'No stored observation is available for the required period.',transformation_dependency_missing:'A required prior observation for this transformation is missing.',official_decision_not_available:'No official decision statement is stored for this meeting.',official_prior_decision_not_available:'No preceding official decision statement is stored.'} as Record<string,string>)[reason]??reason;}
function EventDetails({event,measure,now,check,id,onClose}:{event:CalendarEvent;measure?:CalendarMeasure;now:Date;check:CalendarResponse['check'];id:string;onClose:()=>void}){
 const ism=event.event_type==='ism_report';
 const fed=event.event_type?.startsWith('fomc_');
 const relevant=check?.sources.filter(s=>s.resource===(ism?'ism:calendar':fed?'fed:calendar':'fred:calendar')||s.resource===`${ism?'ism':'fred'}:${measure?.series_id}`);
 const ismSource=relevant?.find(s=>s.resource===`ism:${measure?.series_id}`);
 const ismSchedule=relevant?.find(s=>s.resource==='ism:calendar');
 return <tr className="agenda-detail" onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();onClose();}}}><td colSpan={8}><div id={id}>
 <strong>{tText(event.release_name)}</strong><p>{tText(event.event_type==='fomc_decision'?'Official Federal Reserve policy decision; final day of the scheduled meeting.':event.description??'One publication may contain several separately measured indicators.')}</p>
 <p>{tText('Publication day')}: {formatCalendarDate(event.release_date)} · {eventInstant(event)!==null?formatPolandTime(event.release_datetime_utc).replace(/ PL$/,''):tText('Time unconfirmed')}{eventInstant(event)===null?` · ${tText('No confirmed publication time is stored; no midnight time is inferred.')}`:''}</p>
 {safeLink(event.source_link)?<a href={event.source_link!} target="_blank" rel="noreferrer">{tText('Publication source')}</a>:null}
 {event.schedule_provenance?.confirmation_type==='one_time_official_review'?<p>{tText('This schedule was confirmed by a one-time review of the official publisher page; automatic access remains unavailable.')}</p>:null}
 {event.schedule_status==='conflict'?<p>{tText('Official schedule evidence conflicts; the date shown comes from FRED and no official time or period is assigned.')}</p>:null}
 {safeLink(event.time_source_url)?<p><a href={event.time_source_url!} target="_blank" rel="noreferrer">{tText('Publication time source')}</a>{event.time_rule?` · ${event.time_rule.time} ${event.time_rule.source_timezone} · ${event.time_rule.valid_from} – ${event.time_rule.valid_through}`:''}</p>:null}
 {fed&&event.expects_numeric_result===false?<>
 <p>{tText('Linked FOMC meeting')}: {event.meeting_start_date} – {event.meeting_end_date}</p>
 <p>{tText('Schedule confirmation')}: {tText(event.date_status==='confirmed'?'Confirmed':'Not confirmed')} · {tText('Publisher timezone')}: {event.source_timezone??'America/New_York'}</p>
 {safeLink(event.date_source_url)?<p><a href={event.date_source_url!} target="_blank" rel="noreferrer">{tText('Publication date source')}</a></p>:null}
 <p>{safeLink(event.document_url)?<a href={event.document_url!} target="_blank" rel="noreferrer">{tText('Official event document')}</a>:tText('No official document is linked yet. Document availability does not determine whether the event took place.')}</p>
 {event.schedule_provenance?<p>{tText('Retrieved')}: {availabilityTime(event.schedule_provenance.retrieved_at)} · {tText('Document hash')}: {event.schedule_provenance.raw_hash}</p>:null}
 </>:null}
 <ul>{relevant?.map(source=><li key={source.resource}>{tText(source.label)}: {tText(checkStatusLabel(source.range_status))}{source.checked_at?` · ${availabilityTime(source.checked_at)}`:''}</li>)}</ul>
 {measure?<div className="agenda-measure-detail"><strong>{tText(measure.label)}</strong>{measure.definition?<p>{tText(measure.definition)}</p>:null}
 <p>{measure.series_id} · {tText('Measure')}: {measure.feature_name} · {tText(measure.unit)}. {tText('Observation period')}: {measure.reference_period?formatObservationDate(measure.reference_period,measure.frequency):tText('Reference period unconfirmed')}.</p>
 <p>{tText('Actual')}: {calendarReadingValue(measure,'actual')} · {tText('Previous')}: {calendarReadingValue(measure,'previous')}</p>
 {!measure.missing_reason&&(measure.actual===null||measure.previous===null)?<p>{tText(measure.reference_period?'No finite stored value is available for the required period and transformation.':'The publication date does not confirm the observation period; actual and previous readings are not guessed.')}{resultPending(event,measure,now)?` ${tText('Awaiting data')}.`:''}</p>:null}
 <p>{tText(versionLabel(measure.data_version))}{measure.revision_confirmed?` · ${tText('Confirmed revision')}`:''}. {tText(measure.data_version==='stored_date_vintage'?'ALFRED establishes date-level availability, not the exact value at the scheduled publication time.':measure.data_version==='current_vintage'?'This stored value may contain later revisions; it is not an actual-at-release value.':measure.data_version==='official_release'?'Result confirmed by the official publisher.':'No value is assigned without a confirmed period and a stored observation.')}</p>
 {measure.vintage_date?<p>{tText('Vintage date')}: {measure.vintage_date}{measure.realtime_end?` · ${measure.realtime_end}`:''}.</p>:null}
 <p>{tText(ism&&measure.actual!==null?'Previous is the preceding month as reported in this document.':measure.previous_kind==='previous_decision'?'Previous is the target range announced before this meeting.':measure.previous_kind==='previous_estimate'?'Previous compares the earlier stored estimate of the same quarter.':'Previous refers to the preceding calendar period for the same measure.')}{measure.previous_period?` ${formatObservationDate(measure.previous_period,measure.frequency)}.`:''}{measure.previous_data_version?` ${tText('Previous')}: ${tText(versionLabel(measure.previous_data_version))}.`:''}</p>
 <a href={measure.source_url} target="_blank" rel="noreferrer">{tText('Source')}</a>{' · '}{measure.series_id!=='RETAIL_CONTROL'?<a href={`#/explore/indicators/${encodeURIComponent(measure.series_id.split('/')[0])}`}>{tText('View indicator')}</a>:null}
 {measure.calculation_provenance?<div><p>{tText('Control Group calculation uses a common current-vintage snapshot, not historical first prints.')}</p>{Object.entries(measure.calculation_provenance).map(([kind,proof])=>proof?<div key={kind}><strong>{tText(kind==='actual'?'Actual':'Previous')}</strong><p>{proof.formula}</p>{[proof.current,proof.previous].map((part,index)=>part?<div key={index}><p>{part.observation_period} · {tText('Vintage date')}: {part.vintage_date} · {part.level} {tText('millions of dollars')}</p><ul>{Object.entries(part.components).map(([sid,value])=><li key={sid}><a href={part.source_urls[sid]} target="_blank" rel="noreferrer">{sid}</a>: {value}</li>)}</ul></div>:null)}</div>:null)}</div>:null}
 {measure.period_provenance?<p>{tText('Period evidence')}: <a href={safeLink(measure.period_provenance.source_url)??undefined} target="_blank" rel="noreferrer">{tText(measure.period_provenance.binding_method)}</a>{measure.period_provenance.estimate_stage?` \u00b7 ${measure.period_provenance.estimate_stage}`:''}{measure.period_provenance.retrieved_at?` \u00b7 ${availabilityTime(measure.period_provenance.retrieved_at)}`:''}</p>:null}
 {measure.missing_reason?<p>{(['actual','previous'] as const).filter(kind=>measure.missing_reason?.[kind]).map(kind=><span key={kind}>{tText(kind==='actual'?'Actual':'Previous')}: {tText(calendarMissingReason(measure.missing_reason![kind]!))} </span>)}</p>:null}
 {measure.period_status_reason?<p>{tText(calendarMissingReason(measure.period_status_reason))}</p>:null}
 {measure.period_provenance?.source_check?.status==='error'?<p>{tText('This publisher schedule could not be checked automatically; saved evidence retains its original retrieval date.')}</p>:null}
 {measure.result_provenance?<p><a href={safeLink(measure.result_provenance.source_url)??undefined} target="_blank" rel="noreferrer">{tText('Confirmed publication result')}</a> · {measure.result_provenance.release_date}</p>:null}
 {measure.publication_provenance&&!measure.result_provenance?<p><a href={safeLink(measure.publication_provenance.source_url)??undefined} target="_blank" rel="noreferrer">{tText('Confirmed publisher release')}</a> · {measure.publication_provenance.release_date}</p>:null}
 {measure.series_id==='PERMIT'&&measure.period_provenance?.estimate_stage==='revised_permits'?<p>{tText('This is a revision of the same month. Previous remains the preceding month, not the earlier estimate of this month.')}</p>:null}
 {measure.series_id==='DGORDER'&&measure.period_provenance?.estimate_stage==='full'?<p>{tText('The full M3 report updates the same reference month. Previous is the previous month, not the advance estimate.')}</p>:null}
 {ism?<><p>{tText('ISM document versions are not a complete first-release history. A report timestamp does not date all months in its history table.')}</p>
 {ismSource?<p>{tText('Latest report discovery')}: {tText(ismSource.scope?.latest_publication_discovered?'Confirmed':'Not confirmed')} · {tText('Result document downloaded')}: {tText(ismSource.scope?.result_downloaded===undefined?'No check recorded':ismSource.scope.result_downloaded?'Confirmed':'Not confirmed')}{(ismSource.scope?.report_month||ismSource.scope?.discovered_report_month)?` \u00b7 ${formatObservationDate((ismSource.scope.report_month||ismSource.scope.discovered_report_month)!,'monthly')}`:''}</p>:null}
 {ismSchedule?.scope?.annual_schedule_status==='error'?<p>{tText('The automatic annual ISM calendar check failed; saved confirmed dates and explicit report announcements are retained.')}</p>:null}
 {measure.previous_before_report?<p>{tText('Earlier document value for the previous month')}: {compactMeasureValue(measure.previous_before_report.value,measure.unit)}. {measure.previous_revision_confirmed?tText('Previous was revised in this report.'):tText('The earlier document agrees with this report.')}</p>:null}
 {measure.attribution?<p>{tText(measure.attribution)}</p>:null}</>:null}
 {measure.effective_date?<p>{tText('Decision effective date')}: {formatCalendarDate(measure.effective_date)}</p>:null}
 {measure.previous_effective_date?<p>{tText('Previous decision effective date')}: {formatCalendarDate(measure.previous_effective_date)}</p>:null}
 {(['actual','previous'] as const).map(kind=>{const proof=kind==='actual'?measure.actual_provenance:measure.previous_provenance;return proof?<p key={kind}>{tText(kind==='actual'?'Actual source':'Previous source')}: <a href={safeLink(String(proof.source_url??''))??undefined} target="_blank" rel="noreferrer">{tText(String(proof.version??'Official announcement'))}</a>{proof.vintage_date?` \u00b7 ${tText('Vintage date')}: ${proof.vintage_date}`:''}{proof.as_of?` \u00b7 ${tText('As of')}: ${proof.as_of}`:''}{proof.document_published_at?` \u00b7 ${tText('Document publication time')}: ${availabilityTime(String(proof.document_published_at))}`:''}{proof.retrieved_at?` \u00b7 ${tText('Retrieved')}: ${availabilityTime(String(proof.retrieved_at))}`:''}{proof.raw_hash?` \u00b7 ${tText('Document hash')}: ${proof.raw_hash}`:''}</p>:null;})}
 <p>{tText(comparableForecast(measure)?'Forecast is the consensus for this publication, period and measure.':'No integrated consensus source')}.</p></div>:<p>{tText(event.expects_numeric_result===false?'Actual, Previous, Forecast and numerical comparisons do not apply to this event.':'No numerical result')}</p>}
 </div></td></tr>;
}
function AgendaRow({event,measure,now,next,showCountdown,expanded,toggle,check,rowId}:{event:CalendarEvent;measure?:CalendarMeasure;now:Date;next:number;showCountdown:boolean;expanded:boolean;toggle:()=>void;check:CalendarResponse['check'];rowId:string}){
 const stars=eventImportanceStars(event),instant=eventInstant(event),remaining=showCountdown?countdownText(next,now):null;
 const name=measure?compactMeasureName(measure):tText(event.release_name),period=measure?compactPeriod(measure,event.release_date):'';
 const forecast=measure&&comparableForecast(measure)?measure.forecast:null;
 const vsForecast=measure?calendarComparison(measure,'forecast'):null,vsPrevious=measure?calendarComparison(measure,'previous'):null;
 const buttonId=`agenda-button-${rowId}`,detailId=`agenda-detail-${rowId}`;
 const close=()=>{toggle();document.getElementById(buttonId)?.focus({preventScroll:true});};
 return <Fragment><tr className="agenda-entry" onClick={e=>{if(!(e.target as HTMLElement).closest('button,a'))toggle();}} onKeyDown={e=>{if(e.key==='Escape'&&expanded){e.stopPropagation();close();}}}>
 <td className="agenda-time">{instant!==null?formatPolandTime(event.release_datetime_utc).replace(/ PL$/,''):'\u2014'}</td>
 <th scope="row"><button type="button" id={buttonId} className="agenda-measure-name" aria-expanded={expanded} aria-controls={expanded?detailId:undefined} onClick={toggle}>{name}{period?` (${period})`:''}</button>{remaining?<small>{remaining}</small>:null}</th>
 <td className="agenda-stars"><span role="img" aria-label={tLabel(stars===null?'Importance unavailable':`Importance ${stars} of 3`)}>{stars===null?'\u2014':'\u2605'.repeat(stars)}</span></td>
 <td className="agenda-number agenda-secondary" data-label={tLabel('Forecast')}>{measure?compactMeasureValue(forecast,measure.unit):'\u2014'}</td>
 <td className="agenda-difference" data-label={tLabel('vs forecast')}>{vsForecast?<ComparisonTooltip comparison={vsForecast}/>:event.expects_numeric_result===false?'—':null}</td>
 <td className="agenda-number agenda-actual" data-label={tLabel('Actual')}>{measure?calendarReadingValue(measure,'actual'):'\u2014'}</td>
 <td className="agenda-difference" data-label={tLabel('vs previous')}>{vsPrevious?<ComparisonTooltip comparison={vsPrevious}/>:event.expects_numeric_result===false?'—':null}</td>
 <td className="agenda-number agenda-secondary" data-label={tLabel('Previous')}>{measure?calendarReadingValue(measure,'previous'):'\u2014'}</td></tr>
 {expanded?<EventDetails event={event} measure={measure} now={now} check={check} id={detailId} onClose={close}/>:null}</Fragment>;
}
export function CalendarPage(){
 const [now,setNow]=useState(()=>new Date());
 const [preset,setPreset]=useState<DatePreset>('week'),[range,setRange]=useState(()=>presetRange('week'));
 const [custom,setCustom]=useState(range),[validation,setValidation]=useState<string|null>(null),[showFilters,setShowFilters]=useState(false);
 const [stars,setStars]=useState(()=>new Set([2,3])),[unknown,setUnknown]=useState(false),[categories,setCategories]=useState(()=>new Set<string>());
 const [data,setData]=useState<CalendarResponse>(),[error,setError]=useState(false),[retry,setRetry]=useState(0),[selected,setSelected]=useState<string>();
 const receive=useCallback((value:CalendarResponse)=>setData(value),[]);
 const operations=useMemo(()=>({request:(signal:AbortSignal)=>requestOverviewRefresh(signal,range),load:async(signal:AbortSignal)=>{const value=await fetchCalendarAgenda(range.startDate,range.endDate,signal);if(value.check?.sources.some(s=>s.scope_error==='selected_range_not_checked'))await requestOverviewRefresh(signal,range);return value;}}),[range]);
 const refresh=useBackgroundRefresh(data?.start_date===range.startDate&&data?.end_date===range.endDate?data:undefined,receive,operations);
 useEffect(()=>{const abort=new AbortController();setData(undefined);setError(false);fetchCalendarAgenda(range.startDate,range.endDate,abort.signal).then(value=>{if(!abort.signal.aborted)setData(value);}).catch(()=>{if(!abort.signal.aborted)setError(true);});return()=>abort.abort();},[range,retry]);
 const events=useMemo(()=>data?filterEvents(data.events,stars,unknown,categories):[],[data,stars,unknown,categories]),groups=groupAgenda(events),next=nextInstant(events,now);
 useEffect(()=>{
  let timer:ReturnType<typeof setTimeout>|undefined;
  const update=()=>{
   if(timer)clearTimeout(timer);
   if(document.visibilityState==='hidden')return;
   const current=new Date();setNow(current);
   const delay=countdownDelay(nextInstant(events,current),current);
   if(delay!==null)timer=setTimeout(update,Math.min(delay,2147483647));
  };
  update();window.addEventListener('focus',update);document.addEventListener('visibilitychange',update);
  return()=>{if(timer)clearTimeout(timer);window.removeEventListener('focus',update);document.removeEventListener('visibilitychange',update);};
 },[events]);
 const choose=(value:DatePreset)=>{setPreset(value);setSelected(undefined);setValidation(null);if(value==='custom')setCustom(range);else setRange(presetRange(value));};
 const toggleStar=(star:number)=>setStars(old=>{const next=new Set(old);next.has(star)?next.delete(star):next.add(star);return next;});
 return <main className="calendar-page calendar-agenda"><header className="calendar-header"><h1>{tText('Calendar')}</h1><p className="calendar-time-note">{tText('USA')} · {tText('Times shown in Poland local time (Europe/Warsaw).')}</p></header>
 <div className="agenda-date-presets" role="group" aria-label={tLabel('Calendar date range')}>{presets.map(([value,label])=><button key={value} type="button" aria-pressed={preset===value} onClick={()=>choose(value)}>{tText(label)}</button>)}</div>
 {preset==='custom'?<form className="agenda-range-form" onSubmit={e=>{e.preventDefault();const error=rangeError(custom.startDate,custom.endDate);setValidation(error);if(!error){setRange(custom);setSelected(undefined);}}}>
 <label>{tText('Start date')}<input type="date" value={custom.startDate} onChange={e=>setCustom({...custom,startDate:e.target.value})} required/></label><label>{tText('End date')}<input type="date" value={custom.endDate} onChange={e=>setCustom({...custom,endDate:e.target.value})} required/></label><button type="submit">{tText('Apply range')}</button>{validation?<p role="alert">{tText(validation)}</p>:null}</form>:null}
 <div className="agenda-toolbar"><span>{formatCalendarDate(range.startDate)} – {formatCalendarDate(range.endDate)}</span><label><input type="checkbox" checked={stars.size===1&&stars.has(3)&&!unknown} onChange={e=>{setStars(new Set(e.target.checked?[3]:[2,3]));setUnknown(false);}}/>{tText('Only')} ★★★</label><button type="button" aria-expanded={showFilters} onClick={()=>setShowFilters(v=>!v)}>{tText('Filters')}</button><button type="button" onClick={()=>{setStars(new Set([1,2,3]));setUnknown(true);setCategories(new Set());}}>{tText('Clear filters')}</button></div>
 {showFilters?<div className="agenda-filters"><fieldset><legend>{tText('Importance')}</legend>{[1,2,3].map(star=><label key={star}><input type="checkbox" checked={stars.has(star)} onChange={()=>toggleStar(star)}/>{'★'.repeat(star)}</label>)}<label><input type="checkbox" checked={unknown} onChange={e=>setUnknown(e.target.checked)}/>{tText('Importance unavailable')}</label></fieldset><fieldset><legend>{tText('Categories')}</legend>{calendarCategories.map(c=><label key={c.id}><input type="checkbox" checked={categories.has(c.id)} onChange={()=>setCategories(old=>{const next=new Set(old);next.has(c.id)?next.delete(c.id):next.add(c.id);return next;})}/>{tText(c.label)}</label>)}</fieldset></div>:null}
 {data?<CalendarCheckStatus data={data} refresh={refresh??data.refresh}/>:null}
 {!data&&!error?<p role="status">{tText('Loading calendar...')}</p>:null}{error?<div role="alert"><p>{tText('Unable to load calendar.')}</p><button onClick={()=>setRetry(n=>n+1)}>{tText('Retry')}</button></div>:null}
 {data&&!groups.length?<p className="calendar-state">{tText(data.events.length?'No events match the selected filters.':'No stored events in this date range.')}</p>:null}
 {groups.length?<table className="agenda-table"><caption className="visually-hidden">{tText('Calendar')} · {formatCalendarDate(range.startDate)} – {formatCalendarDate(range.endDate)}</caption>
 <colgroup>{[8,34,8,11,8.5,11,8.5,11].map((w,i)=><col key={i} style={{width:`${w}%`}}/>)}</colgroup>
 <thead><tr>{['Time','Event','Importance','Forecast','vs forecast','Actual','vs previous','Previous'].map(label=><th scope="col" key={label} className={label.startsWith('vs ')?'agenda-difference-heading':undefined}>{tText(label)}</th>)}</tr></thead>
 {groups.map(group=><tbody key={group.date} aria-label={formatAgendaDate(group.date)}><tr className="agenda-day-heading"><th colSpan={8}><h2>{formatAgendaDate(group.date)}</h2></th></tr>
 {group.events.flatMap(event=>{
  const measures=event.expects_numeric_result===false?[]:event.measures??fallbackMeasures(event);
  return (measures.length?measures:[undefined]).map((measure,index)=>{
   const key=`${identity(event)}:${measure?`${measure.series_id}:${measure.feature_name}`:'event'}`;
   const firstNext=events.find(e=>eventInstant(e)===next);
   return <AgendaRow key={key} event={event} measure={measure} now={now} next={next} showCountdown={index===0&&firstNext!==undefined&&identity(firstNext)===identity(event)} expanded={selected===key} toggle={()=>setSelected(v=>v===key?undefined:key)} check={data?.check} rowId={encodeURIComponent(key)}/>;
  });
 })}</tbody>)}</table>:null}
 <p className="agenda-comparison-legend">{tText("Difference color: typical interpretation for the economic area, not market direction.")}</p>
 <p className="agenda-attribution">{tText('Sources')}: <a href="https://fred.stlouisfed.org/">FRED / ALFRED</a>, <a href="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm">{tText('Federal Reserve')}</a>{data?.events.some(event=>event.event_type==='ism_report')?<>, <a href="https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/">ISM</a></>:null}. {tText('Stars express MacroLens editorial importance, not market direction or an Investing.com rating.')}</p></main>;
}
