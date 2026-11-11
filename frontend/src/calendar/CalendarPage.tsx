import {ForecastValue} from './ForecastValue';
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
import {MacroEventCard} from './MacroEventCard';
import {MissingValue,macroMissingReason} from './MissingValue';
import {EarningsCalendar} from './EarningsCalendar';
import {UnifiedEarningsValues} from './UnifiedEarningsValues';
import {useEarningsCalendar} from './useEarningsCalendar';
import './unifiedCalendar.css';
import {unifiedGroups,earningsImportance,type TimelineEvent} from './unifiedCalendar';
import type {EarningsItem} from './earningsTypes';
import {companyDisplayName} from './earningsCompanyNames';
import {et} from './earningsPresentation';
import {compactMeasureName,compactPeriod,compactMeasureValue,calendarReadingValue} from './calendarPresentation';
import {calendarCategories,countdownText,countdownDelay,filterEvents,groupAgenda,nextInstant,presetRange,rangeError,type DatePreset} from './calendarAgenda';

const presetGroups:Array<Array<[DatePreset,string]>>=[[['yesterday','Yesterday'],['today','Today'],['tomorrow','Tomorrow']],[['previousWeek','Previous week'],['week','This week'],['nextWeek','Next week']],[['custom','Date range']]];
const identity=(e:CalendarEvent)=>e.event_id??`${e.release_id}:${e.release_date}`;
const safeLink=(url:string|null|undefined)=>url&&/^https?:\/\//.test(url)?url:null;

function CalendarCheckStatus({data,refresh}:{data:CalendarResponse;refresh:CalendarResponse['refresh']}){
 const check=data.check,failures=refresh?.results.filter(row=>(row.status==='error'||row.status==='skipped')&&(row.resource==='overview'||check?.required_resources.includes(row.resource)))??[];
 const failed=refresh?.status==='error'||check?.status==='error'||failures.length>0;
 const label=refresh?.status==='running'?'Checking availability of new data…':failed?'Unable to check some sources — stored data shown.':check?.status==='complete'?'Sources checked:':check?.checked_at?'Some sources checked:':'Selected range not yet verified.';
 return <div className="calendar-check"><span role="status" aria-live="polite">{tText(label)} {refresh?.status!=='running'&&!failed&&check?.checked_at?<time dateTime={check.checked_at}>{availabilityTime(check.checked_at)}</time>:null}</span></div>;
}
function fallbackMeasures(event:CalendarEvent):CalendarMeasure[]{return event.series.map(s=>({series_id:s.series_id,label:s.short_name||s.name,feature_name:'raw',frequency:s.frequency,unit:s.unit||'',reference_period:null,previous_period:null,previous_kind:'previous_period',actual:null,previous:null,forecast:null,consensus_status:'not_integrated',data_version:null,revision_confirmed:false,binding_method:null,vintage_date:null,realtime_end:null,result_status:'awaiting_data',mapping_status:'reference_period_unconfirmed',source_url:`https://fred.stlouisfed.org/series/${s.series_id}`}));}
function EventDetails({event,measure,now,check,refresh,revision,id,onClose,columns=8}:{columns?:number;event:CalendarEvent;measure?:CalendarMeasure;now:Date;check:CalendarResponse['check'];refresh?:CalendarResponse['refresh'];revision?:string;id:string;onClose:()=>void}){
 const ism=event.event_type==='ism_report';
 const fed=event.event_type?.startsWith('fomc_');
 const michigan=event.event_type?.startsWith('michigan_'),adp=event.event_type==='adp_monthly',empire=event.event_type==='empire_state';
 const trade=event.event_type==='ft900';
 const relevant=check?.sources.filter(s=>s.resource===(trade?'census:ft900':empire?'nyfed:empire-state':adp?'adp:calendar':michigan?'michigan:calendar':ism?'ism:calendar':fed?'fed:calendar':'fred:calendar')||s.resource===`${ism?'ism':'fred'}:${measure?.series_id}`);
 return <tr className="agenda-detail" onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();onClose();}}}><td colSpan={columns}><div id={id}><MacroEventCard event={event} measure={measure}><div className="agenda-technical-content">
 <strong>{tText(event.release_name)}</strong><p>{tText(event.event_type==='fomc_decision'?'Official Federal Reserve policy decision; final day of the scheduled meeting.':event.description??'One publication may contain several separately measured indicators.')}</p>
 <p>{tText('Publication day')}: {formatCalendarDate(event.release_date)} · {eventInstant(event)!==null?formatPolandTime(event.release_datetime_utc).replace(/ PL$/,''):tText('Time unconfirmed')}{eventInstant(event)===null?` · ${tText('No confirmed publication time is stored; no midnight time is inferred.')}`:''}</p>
 {safeLink(event.source_link)?<a href={event.source_link!} target="_blank" rel="noreferrer">{tText('Publication source')}</a>:null}
 {trade&&event.usage_rights?<>
 <p>{tText('FT900 covers total goods and services on a seasonally adjusted balance of payments basis. Advance goods is a different release. Negative balances are deficits.')}</p>
 <p>{tText('The schedule, full FT900 report and Exhibit 1 availability are separate. The scheduled time does not prove that a new result is available.')}</p>
 <p>{tText('Report document')}: {tText(event.document_status==='available'?'Available':'Not confirmed')} · {safeLink(event.document_url)?<a href={event.document_url!} target="_blank" rel="noreferrer">{tText('Official event document')}</a>:null}</p>
 <p>{tText('Source check')}: {relevant?.[0]?tText(checkStatusLabel(relevant[0].range_status)):tText('No check recorded')}. {tText('Snapshot history starts with this integration; current-vintage values may include seasonal revisions. No complete historical first-print history is claimed.')}</p>
 {event.result_state?.report_exhibit_difference?<p>{tText('The current Exhibit 1 differs from the historical report; the displayed value includes later revisions.')}</p>:null}
 <p>{event.usage_rights.original_title} · {event.usage_rights.source}</p>
 <p><a href={event.usage_rights.original_url} target="_blank" rel="noreferrer">{tText('Official Exhibit 1 XLSX')}</a>{' · '}<a href={event.usage_rights.terms_url} target="_blank" rel="noreferrer">{tText('BEA data use policy')}</a></p>
 <p>{tText(event.usage_rights.modifications)}</p>
 </>:null}
 {empire&&event.usage_rights?<>
 <p>{tText('NY Fed schedule, report and CSV availability are separate. The scheduled time is not a guarantee of immediate data availability.')}</p>
 <p>{tText('Report document')}: {tText(event.document_status==='available'?'Available':'Not confirmed')}{safeLink(event.document_url)?<> · <a href={event.document_url!} target="_blank" rel="noreferrer">{tText('Official event document')}</a></>:null}</p>
 <p>{tText('Source check')}: {relevant?.[0]?tText(checkStatusLabel(relevant[0].range_status)):tText('No check recorded')}. {tText('Snapshot history starts with this integration; current-vintage values may include seasonal revisions. No complete historical first-print history is claimed.')}</p>
 {event.result_state?.report_csv_difference?<p>{tText('The current CSV differs from the archived report; the displayed value is current-vintage.')}</p>:null}
 <p>{event.usage_rights.original_title} · {event.usage_rights.copyright}</p>
 <p><a href={event.usage_rights.original_url} target="_blank" rel="noreferrer">{tText('Original NY Fed CSV')}</a>{' · '}<a href={event.usage_rights.terms_url} target="_blank" rel="noreferrer">{tText('NY Fed Terms of Use')}</a></p>
 <p>{tText(event.usage_rights.modifications)}</p>
 </>:null}
 {michigan||adp?<>
 <p>{tText('Observation period')}: {event.reference_period?formatObservationDate(event.reference_period,'monthly'):tText('Reference period unconfirmed')} · {tText(adp?'Monthly NER':event.publication_stage==='preliminary'?'Preliminary':'Final')}</p>
 <p>{tText('Numerical results are not integrated. Dashboard redistribution requires clarification or permission from the publisher. The scheduled release and document availability are separate from access to its numbers.')}</p>
 <p><a href={event.publisher_reports_url} target="_blank" rel="noreferrer">{tText('Publisher reports')}</a>{' · '}<a href={event.license_source_url} target="_blank" rel="noreferrer">{tText('Publisher usage agreement')}</a></p>
 <p>{event.document_status==='available'&&safeLink(event.document_url)?<a href={event.document_url!} target="_blank" rel="noreferrer">{tText('Official event document')}</a>:tText('No matching report link has been verified; this does not establish that the report is unpublished.')}</p>
 {event.document_kind==='current_summary_link'?<p>{tText('This link opens the publisher’s changing current summary, verified for this month and stage at the recorded check time; it is not an archived report.')}</p>:null}
 <p>{tText('Forecast')}: — · {tText('No integrated consensus source')}.</p>
 <p>{tText(adp?'Previous would be the preceding month’s employment change, with its data version. No Previous value is integrated.':'Previous would compare the preceding month, not Preliminary versus Final of the same month. No Previous value is integrated.')}</p>
 {safeLink(event.date_source_url)?<p><a href={event.date_source_url!} target="_blank" rel="noreferrer">{tText('Publication date source')}</a></p>:null}
 {event.schedule_status==='changed'?<p>{tText('The publisher changed this event’s date or confirmed time; its identity is preserved.')}</p>:null}
 {event.schedule_provenance?<p>{tText('Retrieved')}: {availabilityTime(event.schedule_provenance.retrieved_at)} · {tText('Document hash')}: {event.schedule_provenance.raw_hash}</p>:null}
 </>:null}
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
 {refresh?.bea_release_checks?.filter(row=>row.release_id===event.release_id&&row.release_date===event.release_date&&(!event.estimate_stage||row.estimate_stage===event.estimate_stage)&&(!measure?.reference_period||row.reference_period===measure.reference_period)).map(row=><section key={row.id} aria-label={tLabel('BEA publication check')}><strong>{tText('BEA publication check')}</strong><p>{tText('Checks reserved')}: {row.attempts}/{row.max_attempts} · {tText('Confirmed measures')}: {row.confirmed_measures}/{row.expected_measures}</p><p>{tText(({confirmed:'BEA report confirmed',waiting:'Waiting for the next permitted BEA check',due:'BEA check due',partial:'BEA report partially confirmed',attempt_limit:'Short BEA check limit reached',window_closed:'Short BEA check window ended',backoff:'BEA provider backoff'} as Record<string,string>)[row.status]??row.status)}</p>{row.next_check_at?<p>{tText('Next permitted source check')}: {availabilityTime(row.next_check_at)}</p>:null}<p>{tText('This checks the due BEA report; other sources keep their normal cadence. Availability at the scheduled time is not guaranteed.')}</p></section>)}

 </div></MacroEventCard></div></td></tr>;
}
function AgendaRow({event,measure,now,next,showCountdown,expanded,toggle,check,refresh,revision,rowId,showForecast=true}:{showForecast?:boolean;event:CalendarEvent;measure?:CalendarMeasure;now:Date;next:number;showCountdown:boolean;expanded:boolean;toggle:()=>void;check:CalendarResponse['check'];refresh?:CalendarResponse['refresh'];revision?:string;rowId:string}){
 const stars=eventImportanceStars(event),instant=eventInstant(event),remaining=showCountdown?countdownText(next,now):null;
 const name=measure?compactMeasureName(measure):tText(event.release_name),period=measure?compactPeriod(measure,event.release_date):(event.event_type?.startsWith('michigan_')||event.event_type==='adp_monthly')&&event.reference_period?compactPeriod({reference_period:event.reference_period,frequency:'monthly',feature_name:'raw'},event.release_date):'';
 const forecast=measure&&comparableForecast(measure)?measure.forecast:null;
 const vsForecast=measure?calendarComparison(measure,'forecast'):null,vsPrevious=measure?calendarComparison(measure,'previous'):null;
 const reading=(kind:'actual'|'previous',target=measure)=>{const text=target?calendarReadingValue(target,kind):'—';return text==='—'?<MissingValue reason={macroMissingReason(event,target,kind)}/>:text;};
 const buttonId=`agenda-button-${rowId}`,detailId=`agenda-detail-${rowId}`;
 const close=()=>{toggle();document.getElementById(buttonId)?.focus({preventScroll:true});};
 return <Fragment><tr className="agenda-entry" onClick={e=>{if(!(e.target as HTMLElement).closest('button,a'))toggle();}} onKeyDown={e=>{if(e.key==='Escape'&&expanded){e.stopPropagation();close();}}}>
 <td className="agenda-time">{instant!==null?formatPolandTime(event.release_datetime_utc).replace(/ PL$/,''):'\u2014'}</td>
 <th scope="row"><button type="button" id={buttonId} className="agenda-measure-name" aria-expanded={expanded} aria-controls={expanded?detailId:undefined} onClick={toggle}>{name}{period?` (${period})`:''}</button>{remaining?<small>{remaining}</small>:null}</th>
 <td className="agenda-stars"><span role="img" aria-label={tLabel(stars===null?'Importance unavailable':`Importance ${stars} of 3`)}>{stars===null?'\u2014':'\u2605'.repeat(stars)}</span></td>
 {showForecast?<><td className="agenda-number agenda-secondary" data-label={tLabel('Forecast')}>{measure?.forecast_details?<ForecastValue forecast={measure.forecast_details} unit={measure.unit}/>:forecast!==null&&measure?compactMeasureValue(forecast,measure.unit):<MissingValue reason={macroMissingReason(event,measure,'forecast')}/>}</td>
 <td className="agenda-difference" data-label={tLabel('vs forecast')}>{vsForecast?<ComparisonTooltip comparison={vsForecast} colorByDirection/>:<MissingValue reason={measure?.actual==null?macroMissingReason(event,measure,'actual'):et('No comparable consensus for this reading.','Brak porównywalnego konsensusu dla tego odczytu.')}/>}</td></>:null}
 <td className="agenda-number agenda-actual" data-label={tLabel('Actual')}>{event.result_integration_status==='publisher_permission_required'?<a href={safeLink(event.document_url)??event.publisher_reports_url} target="_blank" rel="noreferrer">{tText(event.document_status==='available'&&event.document_url?'Data at publisher':'Publisher reports')}</a>:reading('actual')}{measure?.year_over_year?<><br/><small>{tText('YoY (NSA)')}: {reading('actual',measure.year_over_year)}</small></>:null}</td>
 <td className="agenda-difference" data-label={tLabel('vs previous')}>{vsPrevious?<ComparisonTooltip comparison={vsPrevious} colorByDirection/>:<MissingValue reason={macroMissingReason(event,measure,'difference')}/>}</td>
 <td className="agenda-number agenda-secondary" data-label={tLabel('Previous')}>{reading('previous')}{measure?.year_over_year?<><br/><small>{tText('YoY (NSA)')}: {reading('previous',measure.year_over_year)}</small></>:null}</td></tr>
 {expanded?<EventDetails event={event} measure={measure} now={now} check={check} refresh={refresh} revision={revision} columns={showForecast?8:6} id={detailId} onClose={close}/>:null}</Fragment>;
}
function UnifiedEarningsRow({row,onDetails}:{row:Extract<TimelineEvent,{kind:'earnings'}>;onDetails:()=>void}){
 const e=row.event,stars=earningsImportance(e);
 const label=stars===3?et('Importance 3 of 3 · market capitalization at least USD 200 billion','Ważność 3 z 3 · kapitalizacja co najmniej 200 mld USD'):et('Importance unavailable','Ważność niedostępna');
 return <tr className="agenda-entry agenda-earnings" data-event-id={e.event_id}>
 <td className="agenda-time"><span title={row.description} aria-label={row.description}>{row.clock}</span></td>
 <th scope="row"><button type="button" className="agenda-measure-name" onClick={onDetails} title={companyDisplayName(e)}>{et('Earnings','Wyniki')} {e.ticker} · {e.period_label}</button></th>
 <td className="agenda-stars"><span role="img" aria-label={label} title={label}>{stars===3?'★★★':'—'}</span></td>
 <td className="agenda-number agenda-actual" data-label={tLabel('Actual')}><UnifiedEarningsValues event={e} kind="current"/></td><td className="agenda-difference" data-label={tLabel('vs previous')}><UnifiedEarningsValues event={e} kind="difference"/></td><td className="agenda-number agenda-secondary" data-label={tLabel('Previous')}><UnifiedEarningsValues event={e} kind="previous"/></td>
 </tr>;
}
export function CalendarPage(){
 const [domain,setDomain]=useState<'macro'|'earnings'|'all'>('all');
 const [now,setNow]=useState(()=>new Date());
 const [preset,setPreset]=useState<DatePreset>('week'),[range,setRange]=useState(()=>presetRange('week'));
 const [custom,setCustom]=useState(range),[validation,setValidation]=useState<string|null>(null),[showFilters,setShowFilters]=useState(false);
 const [stars,setStars]=useState(()=>new Set([2,3])),[unknown,setUnknown]=useState(false),[categories,setCategories]=useState(()=>new Set<string>());
 const [data,setData]=useState<CalendarResponse>(),[error,setError]=useState(false),[retry,setRetry]=useState(0),[selected,setSelected]=useState<string>();
 const receive=useCallback((value:CalendarResponse)=>setData(value),[]);
 const operations=useMemo(()=>({request:(signal:AbortSignal)=>requestOverviewRefresh(signal,range),load:async(signal:AbortSignal)=>{const value=await fetchCalendarAgenda(range.startDate,range.endDate,signal);if(value.check?.sources.some(s=>s.scope_error==='selected_range_not_checked'))await requestOverviewRefresh(signal,range);return value;}}),[range]);
 const refresh=useBackgroundRefresh(data?.start_date===range.startDate&&data?.end_date===range.endDate?data:undefined,receive,operations);
 useEffect(()=>{const abort=new AbortController();setData(undefined);setError(false);fetchCalendarAgenda(range.startDate,range.endDate,abort.signal).then(value=>{if(!abort.signal.aborted)setData(value);}).catch(()=>{if(!abort.signal.aborted)setError(true);});return()=>abort.abort();},[range,retry]);
 const earnings=useEarningsCalendar(range.startDate,range.endDate,domain!=='macro');
 const events=useMemo(()=>data?filterEvents(data.events,stars,unknown,categories):[],[data,stars,unknown,categories]),groups=groupAgenda(events),next=nextInstant(events,now);
 const onlyThree=stars.size===1&&stars.has(3)&&!unknown;
 const earningsEvents=(earnings.data?.events??[]).filter((e):e is EarningsItem=>e.domain==='earnings'&&(!onlyThree||earningsImportance(e)===3));
 const timeline=domain==='all'?unifiedGroups(events,earningsEvents,range.startDate,range.endDate):groups.map(g=>({date:g.date,rows:g.events.map(event=>({kind:'macro' as const,key:identity(event),day:g.date,instant:eventInstant(event),event}))}));
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
 <fieldset className="calendar-domains"><legend>{et('Calendar domain','Domena kalendarza')}</legend>{([['all',et('All','Wszystko')],['macro',et('Data','Dane')],['earnings',et('Earnings','Wyniki')]] as const).map(([key,label])=><label key={key}><input type="radio" name="calendar-domain" checked={domain===key} onChange={()=>setDomain(key)}/>{label}</label>)}</fieldset>
 <div className="agenda-date-presets" role="group" aria-label={tLabel('Calendar date range')}>{presetGroups.map((group,index)=><div className="agenda-date-group" key={index}>{group.map(([value,label])=><button key={value} type="button" aria-pressed={preset===value} onClick={()=>choose(value)}>{value==='previousWeek'?<span aria-hidden="true">‹ </span>:value==='custom'?<svg aria-hidden="true" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 11h18"/></svg>:null}{tText(label)}{value==='nextWeek'?<span aria-hidden="true"> ›</span>:null}</button>)}</div>)}</div>
 {preset==='custom'?<form className="agenda-range-form" onSubmit={e=>{e.preventDefault();const error=rangeError(custom.startDate,custom.endDate);setValidation(error);if(!error){setRange(custom);setSelected(undefined);}}}>
 <label>{tText('Start date')}<input type="date" value={custom.startDate} onChange={e=>setCustom({...custom,startDate:e.target.value})} required/></label><label>{tText('End date')}<input type="date" value={custom.endDate} onChange={e=>setCustom({...custom,endDate:e.target.value})} required/></label><button type="submit">{tText('Apply range')}</button>{validation?<p role="alert">{tText(validation)}</p>:null}</form>:null}
 {domain==='earnings'?<EarningsCalendar startDate={range.startDate} endDate={range.endDate} state={earnings}/>:null}
 <div hidden={domain==='earnings'}>
 <div className="agenda-toolbar"><span>{formatCalendarDate(range.startDate)} – {formatCalendarDate(range.endDate)}</span><label><input type="checkbox" checked={stars.size===1&&stars.has(3)&&!unknown} onChange={e=>{setStars(new Set(e.target.checked?[3]:[2,3]));setUnknown(false);}}/>{tText('Only')} ★★★</label><button type="button" aria-expanded={showFilters} onClick={()=>setShowFilters(v=>!v)}>{tText('Filters')}</button><button type="button" onClick={()=>{setStars(new Set([1,2,3]));setUnknown(true);setCategories(new Set());}}>{tText('Clear filters')}</button></div>
 {showFilters?<div className="agenda-filters"><fieldset><legend>{tText('Importance')}</legend>{[1,2,3].map(star=><label key={star}><input type="checkbox" checked={stars.has(star)} onChange={()=>toggleStar(star)}/>{'★'.repeat(star)}</label>)}<label><input type="checkbox" checked={unknown} onChange={e=>setUnknown(e.target.checked)}/>{tText('Importance unavailable')}</label></fieldset><fieldset><legend>{tText('Categories')}</legend>{calendarCategories.map(c=><label key={c.id}><input type="checkbox" checked={categories.has(c.id)} onChange={()=>setCategories(old=>{const next=new Set(old);next.has(c.id)?next.delete(c.id):next.add(c.id);return next;})}/>{tText(c.label)}</label>)}</fieldset></div>:null}
 {domain==='all'&&(earnings.error||earnings.warning)?<div role="alert">{et('Unable to load earnings dates. Stored macro data remain available.','Nie można wczytać terminów wyników spółek. Zapisane dane makro pozostają dostępne.')} <button onClick={earnings.retry}>{et('Retry','Ponów')}</button></div>:null}
 {domain==='all'&&!earnings.data&&!earnings.error?<p role="status">{et('Loading earnings dates…','Wczytywanie terminów wyników…')}</p>:null}
 {data?<CalendarCheckStatus data={data} refresh={refresh??data.refresh}/>:null}
 {!data&&!error?<p role="status">{tText('Loading calendar...')}</p>:null}{error?<div role="alert"><p>{tText('Unable to load calendar.')}</p><button onClick={()=>setRetry(n=>n+1)}>{tText('Retry')}</button></div>:null}
 {data&&!timeline.length&&(domain!=='all'||earnings.data)?<p className="calendar-state">{tText(data.events.length?'No events match the selected filters.':'No stored events in this date range.')}</p>:null}
 {timeline.length?<table className={domain==='all'?'agenda-table agenda-unified':'agenda-table'}><caption className="visually-hidden">{tText('Calendar')} · {formatCalendarDate(range.startDate)} – {formatCalendarDate(range.endDate)}</caption>
 <colgroup>{(domain==='all'?[8,44,8,15,10,15]:[8,34,8,11,8.5,11,8.5,11]).map((w,i)=><col key={i} style={{width:`${w}%`}}/>)}</colgroup>
 <thead><tr>{(domain==='all'?['Time','Event','Importance','Actual','vs previous','Previous']:['Time','Event','Importance','Forecast','vs forecast','Actual','vs previous','Previous']).map(label=><th scope="col" key={label} className={label.startsWith('vs ')?'agenda-difference-heading':undefined}>{tText(label)}</th>)}</tr></thead>
 {timeline.map(group=><tbody key={group.date} aria-label={formatAgendaDate(group.date)}><tr className="agenda-day-heading"><th scope="rowgroup" colSpan={domain==='all'?6:8}><h2>{formatAgendaDate(group.date)}</h2></th></tr>
 {group.rows.flatMap(row=>{
  if(row.kind==='earnings')return <UnifiedEarningsRow key={row.key} row={row} onDetails={()=>setDomain('earnings')}/>;
  const event=row.event;
  const measures=event.expects_numeric_result===false?[]:event.measures??fallbackMeasures(event);
  return (measures.length?measures:[undefined]).map((measure,index)=>{
   const key=`${identity(event)}:${measure?`${measure.series_id}:${measure.feature_name}`:'event'}`;
   const firstNext=events.find(e=>eventInstant(e)===next);
   return <AgendaRow key={key} event={event} measure={measure} now={now} next={next} showCountdown={index===0&&firstNext!==undefined&&identity(firstNext)===identity(event)} expanded={selected===key} toggle={()=>setSelected(v=>v===key?undefined:key)} check={data?.check} refresh={refresh??data?.refresh} revision={data?.data_revision} rowId={encodeURIComponent(key)} showForecast={domain!=='all'}/>;
  });
 })}</tbody>)}</table>:null}
 </div>
 <p hidden={domain==='earnings'} className="agenda-comparison-legend">{et('Change color: higher = green, lower = red; zero or unavailable = neutral.','Kolor zmiany: więcej = zielony, mniej = czerwony; zero lub brak danych = neutralny.')}</p>
 <p hidden={domain==='earnings'} className="agenda-attribution">{tText('Sources')}: <a href="https://fred.stlouisfed.org/">FRED / ALFRED</a>, <a href="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm">{tText('Federal Reserve')}</a>{data?.events.some(event=>event.event_type==='ism_report')?<>, <a href="https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/">ISM</a></>:null}{data?.events.some(event=>event.event_type==='adp_monthly')?<>, <a href="https://adpemploymentreport.com/">ADP Research</a></>:null}{data?.events.some(event=>event.event_type?.startsWith('michigan_'))?<>, <a href="https://data.sca.isr.umich.edu/survey-info.php">University of Michigan Surveys of Consumers</a></>:null}. {tText('Stars express MacroLens editorial importance, not market direction or an Investing.com rating.')}</p></main>;
}
