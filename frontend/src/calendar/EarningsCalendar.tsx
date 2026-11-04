import {useEffect,useState} from 'react';
import {fetchEarnings,type CalendarItemsResponse,type EarningsItem} from './earningsTypes';
import {earningsAnchor,earningsSummary,earningsTime,et} from './earningsPresentation';
import {compareEarnings,earningsDate,financialStatus,financialValue,epsBasis} from './earningsFinancialPresentation';
import {formatAgendaDate,formatPolandTime} from './calendarDates';
import './earnings.css';

function officialSources(e:EarningsItem):[string,string][] {
 const urls=new Map<string,string>();
 const add=(url:string|null|undefined,label:string)=>{if(url&&!urls.has(url))urls.set(url,label);};
 const eps=e.current_eps_actual??e.reported_eps_actual??e.gaap_diluted_eps_actual;
 for(const value of [eps,e.current_revenue_actual??e.revenue_actual])add(value?.source_url,et('Financial report','Raport finansowy'));
 const latest=e.report_documents?.[e.report_documents.length-1];
 if(latest?.document_type==='earnings_release')add(latest.source_url,et('Financial report','Raport finansowy'));
 for(const value of [e.previous_eps_actual,e.previous_revenue_actual])add(value?.source_url,et('Previous report','Poprzedni raport'));
 add(e.release.source_url,et('Results announcement','Komunikat wyników'));
 if(e.call.date_status!=='unknown'&&e.call.date_status!=='cancelled'){
  if(e.call.source_url===e.release.source_url&&e.call.source_url&&urls.get(e.call.source_url)===et('Results announcement','Komunikat wyników'))urls.set(e.call.source_url,et('Announcement / conference','Komunikat / konferencja'));
  else add(e.call.source_url,et('Conference announcement','Zapowiedź konferencji'));
 }
 return [...urls];
}

function EarningsRow({event:e}:{event:EarningsItem}){
 const [open,setOpen]=useState(false);const anchor=earningsAnchor(e);
 const id=`details-${e.event_id}`;
 const summary=e.financial_release_date&&anchor.date_status==='unknown'?et('Time not announced','Godzina nieogłoszona'):earningsSummary(e);
 const escape=(ev:React.KeyboardEvent)=>{if(ev.key==='Escape'&&open){ev.stopPropagation();setOpen(false);document.getElementById(`button-${e.event_id}`)?.focus();}};
 return <><tr className="earnings-row" onKeyDown={escape}>
 <th scope="row"><strong>{e.ticker} · {e.period_label}</strong><span className="earnings-company-name">{e.name}</span></th>
 <td className="earnings-center">{summary}{e.call.scheduled_at_utc&&e.call.date_status!=='cancelled'?<small>{et('Conference','Konferencja')}: {formatPolandTime(e.call.scheduled_at_utc)}</small>:null}</td>
 {(['current_eps','previous_eps','current_revenue','previous_revenue'] as const).map(key=><td key={key} className={`earnings-number${key.startsWith('previous')?' earnings-previous':''}`}>{financialValue(key==='current_eps'?(e.current_eps_actual===undefined?e.reported_eps_actual??e.gaap_diluted_eps_actual:e.current_eps_actual):key==='current_revenue'?(e.current_revenue_actual===undefined?e.revenue_actual:e.current_revenue_actual):e[`${key}_actual`])}<small>{financialValue(e[`${key}_forecast`])}</small></td>)}
 <td className="earnings-center"><button id={`button-${e.event_id}`} aria-expanded={open} aria-controls={id} onClick={()=>setOpen(v=>!v)}><span className="earnings-sr">{e.ticker} · {e.period_label} · {summary} · </span>{et('Details','Szczegóły')}</button></td>
 </tr>
 {open?<tr onKeyDown={escape}><td colSpan={7}><div id={id} className="earnings-details">
 <strong>{e.name} ({e.ticker}) · {e.period_label}</strong>
 {e.period_end?<p>{et('Period end','Okres do')}: {e.period_end}</p>:null}
 {e.financial_release_date||e.release.source_local_date?<p>{et('Results date (issuer)','Data wyników (emitenta)')}: {e.financial_release_date??e.release.source_local_date}</p>:null}
 <p>{et('Results time','Godzina wyników')}: {summary}</p>
 {e.call.date_status!=='unknown'&&e.call.date_status!=='cancelled'?<p>{et('Conference','Konferencja')}: {e.call.scheduled_at_utc?formatPolandTime(e.call.scheduled_at_utc):earningsTime(e.call)}</p>:null}
 <p>Status: {financialStatus(e,e.publication_state?.code==='published_complete')}</p>
 {e.reported_eps_actual||e.gaap_diluted_eps_actual?<p>EPS: {epsBasis(e.reported_eps_actual??e.gaap_diluted_eps_actual)} · {(e.reported_eps_actual??e.gaap_diluted_eps_actual)?.currency}</p>:null}
 {e.previous_period?<p>{et('Comparison','Porównanie')}: {e.previous_period.period_label}</p>:null}
 <h4>{et('Official sources','Oficjalne źródła')}</h4>
 <ul>{officialSources(e).map(([url,label])=><li key={url}><a href={url} target="_blank" rel="noreferrer">{label}</a></li>)}</ul>
 </div></td></tr>:null}</>;

}

export function EarningsCalendar({startDate,endDate}:{startDate:string;endDate:string}){
 const [data,setData]=useState<CalendarItemsResponse>(),[error,setError]=useState(false),[retry,setRetry]=useState(0);
 useEffect(()=>{const abort=new AbortController();setData(undefined);setError(false);
 fetchEarnings(startDate,endDate,[],abort.signal).then(value=>{if(!abort.signal.aborted)setData(value);}).catch(()=>{if(!abort.signal.aborted)setError(true);});return()=>abort.abort();},[startDate,endDate,retry]);
 const events=(data?.events??[]).filter((e):e is EarningsItem=>{
  if(e.domain!=='earnings')return false;
  const day=earningsDate(e);
  return day!==null&&day>=startDate&&day<=endDate;
 });
 const groups=new Map<string,EarningsItem[]>();
 for(const e of events.sort(compareEarnings)){
  const key=earningsDate(e)!;
  groups.set(key,[...(groups.get(key)??[]),e]);
 }
 return <section className="earnings-calendar" aria-label={et('Company earnings','Wyniki spółek')}>
 <h2>{et('Company earnings','Wyniki spółek')}</h2>
 {events.some(e=>e.financial_store_status==='not_activated')?<p role="status">{et('Financial data module not activated in this database. Earnings dates remain available.','Moduł danych finansowych nieaktywny w tej bazie. Terminy wyników pozostają dostępne.')}</p>:null}
 {error?<div role="alert">{et('Unable to load earnings dates. Stored macro data remain available.','Nie można wczytać terminów wyników spółek. Zapisane dane makro pozostają dostępne.')} <button onClick={()=>setRetry(v=>v+1)}>{et('Retry','Ponów')}</button></div>:!data?<p role="status">{et('Loading earnings dates…','Wczytywanie terminów wyników…')}</p>:null}
 {data&&!events.length?<p>{et('No earnings releases with a confirmed date in the selected range.','Brak publikacji wyników z potwierdzoną datą w wybranym zakresie.')}</p>:null}
 {data&&events.length>0?<>
 <p className="earnings-scroll-hint">{et('On small screens, scroll the table horizontally for values and sources.','Na małym ekranie przewiń tabelę poziomo, aby zobaczyć wartości i źródła.')}</p>
 <div className="earnings-table-scroll" role="region" aria-label={et('Earnings table','Tabela wyników')} tabIndex={0}>
 <table className="earnings-table"><colgroup><col className="earnings-company-column"/><col className="earnings-time-column"/><col className="earnings-eps-column"/><col className="earnings-eps-column"/><col className="earnings-revenue-column"/><col className="earnings-revenue-column"/><col className="earnings-details-column"/></colgroup><thead><tr><th scope="col">{et('Company','Spółka')}</th><th scope="col" className="earnings-center">{et('Results time · Poland','Czas wyników · Polska')}</th>{[["Current EPS","EPS aktualny"],["Previous EPS","EPS poprzednio"],["Current revenue","Przychody aktualne"],["Previous revenue","Przychody poprzednio"]].map(([en,pl])=><th key={en} scope="col" className="earnings-center">{et(en,pl)}<small>Actual / {et('Forecast','Prognoza')}</small></th>)}<th scope="col" className="earnings-center">{et('Details','Szczegóły')}</th></tr></thead>
 {[...groups].map(([key,rows])=><tbody key={key}><tr className="earnings-date"><th colSpan={7} scope="rowgroup"><h3>{formatAgendaDate(key)}</h3></th></tr>{rows.map(e=><EarningsRow key={e.event_id} event={e}/>)}</tbody>)}
 </table></div></>:null}
 </section>;
}
