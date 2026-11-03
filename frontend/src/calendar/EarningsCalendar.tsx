import {useEffect,useState} from 'react';
import {fetchEarnings,type CalendarItemsResponse,type EarningsItem} from './earningsTypes';
import {earningsAnchor,earningsSummary,earningsTime,et} from './earningsPresentation';
import {compareEarnings,earningsDate,financialStatus,financialValue} from './earningsFinancialPresentation';
import {formatAgendaDate,formatPolandTime} from './calendarDates';
import './earnings.css';

function EarningsRow({event:e}:{event:EarningsItem}){
 const [open,setOpen]=useState(false);const anchor=earningsAnchor(e);
 const id=`details-${e.event_id}`;
 const status=(value:string)=>({confirmed:et('Confirmed','Potwierdzono'),changed:et('Changed','Zmieniono'),cancelled:et('Cancelled','Odwołano'),unknown:et('Date not announced','Termin nieogłoszony')}[value]??value);
 const summary=e.financial_release_date&&anchor.date_status==='unknown'?et('Time not announced','Godzina nieogłoszona'):earningsSummary(e);
 const escape=(ev:React.KeyboardEvent)=>{if(ev.key==='Escape'&&open){ev.stopPropagation();setOpen(false);document.getElementById(`button-${e.event_id}`)?.focus();}};
 return <><tr className="earnings-row" onKeyDown={escape}>
 <th scope="row"><strong>{e.ticker} · {e.period_label}</strong><span className="earnings-company-name">{e.name}</span></th>
 <td>{summary}{anchor===e.call&&anchor.date_status!=='unknown'?<small>{et('Conference date','Data konferencji')}</small>:null}</td>
 <td className="earnings-number">{financialValue(e.gaap_diluted_eps_actual)}<small>/ —</small></td>
 <td className="earnings-number">{financialValue(e.revenue_actual)}<small>/ —</small></td>
 <td>{financialStatus(e)}</td>
 <td><button id={`button-${e.event_id}`} aria-expanded={open} aria-controls={id} onClick={()=>setOpen(v=>!v)}><span className="earnings-sr">{e.ticker} · {e.period_label} · {summary} · </span>{et('Details / Source','Szczegóły / Źródło')}</button></td>
 </tr>
 {open?<tr onKeyDown={escape}><td colSpan={6}><div id={id} className="earnings-details">
 <p>{et('Results','Wyniki')}: {summary}</p>
 <p>{et('Conference','Konferencja')}: {e.call.scheduled_at_utc&&e.call.date_status!=='cancelled'?formatPolandTime(e.call.scheduled_at_utc):earningsTime(e.call)}</p>
 <p>{financialStatus(e)}. {et('A scheduled date alone does not prove publication.','Sama zaplanowana data nie potwierdza publikacji.')}</p>
 <p>{et('Company','Spółka')}: {e.name}</p>
 <p>EPS GAAP: {financialValue(e.gaap_diluted_eps_actual)} · {et('Revenue','Przychody')}: {financialValue(e.revenue_actual)}</p>
 <p>{et('Analyst consensus unavailable; forecasts are empty.','Konsensus analityków niedostępny; prognozy pozostają puste.')}</p>
 {(e.financial_history??[]).map(o=><section key={o.observation_id}>
 <p>{o.metric==='revenue'?et('Consolidated revenue','Przychody skonsolidowane'):'GAAP diluted EPS'}: {financialValue(o)} · {o.methodology}</p>
 <p>{et('Source units','Jednostki źródłowe')}: {o.source_value} {o.source_unit} · {et('Period end','Koniec okresu')}: {o.period_end}</p>
 <p>{et('Earnings release date (issuer)','Data komunikatu wyników (emitenta)')}: {o.release_date}</p>
 <a href={o.source_url} target="_blank" rel="noreferrer">{e.name} · {et('Official earnings release','Oficjalny komunikat wyników')}</a>
 <p>{et('Manually verified','Zweryfikowano ręcznie')}: {o.verified_on} · {et('Version','Wersja')}: {o.version} / {o.source_version}</p>
 <p>{et('Captured locally','Zapisano lokalnie')}: {o.captured_at}{o.sec_accession?` · SEC: ${o.sec_accession}`:''}</p>
 {o.correction_reason?<p>{et('Correction','Korekta')}: {o.correction_reason}</p>:null}
 </section>)}
 <p>{et('Approximate times and session windows do not guarantee publication time.','Godziny orientacyjne i okna sesji nie gwarantują godziny publikacji.')}</p>
 <p>CIK: {e.cik} · {e.period_label}{e.period_end?` · ${e.period_end}`:''}</p>
 {(['release','call'] as const).filter(k=>e[k].source_url).map(k=><section key={k}>
 <strong>{k==='release'?et('Results evidence','Dowód terminu wyników'):et('Conference evidence','Dowód konferencji')}</strong>
 <p>{et('Source','Źródło')}: <a href={e[k].source_url!} target="_blank" rel="noreferrer">{e.name} {et('Investor Relations / official announcement','Investor Relations / oficjalna zapowiedź')}</a></p>
 <p>{et('Verified','Zweryfikowano')}: {e[k].verified_on} · {et('Manual official-source review','Ręczna weryfikacja oficjalnego źródła')}</p>
 <p>{et('Source date','Data emitenta')}: {e[k].source_local_date} · {e[k].source_local_time??et('Time not announced','Godzina nieogłoszona')} · {e[k].timezone_label_raw} ({e[k].source_timezone})</p>
 <p>{et('Precision','Dokładność')}: {({exact:et('Exact','Dokładna'),approximate:et('Approximate','Orientacyjna'),after_close:et('After close','Po sesji'),before_open:et('Before open','Przed sesją'),date_only:et('Date only','Tylko data'),unknown:et('Unknown','Nieznana')})[e[k].precision]}</p>
 {e[k].session_boundary_source?<p><a href={e[k].session_boundary_source!} target="_blank" rel="noreferrer">{et('Reviewed US session boundary; not a publication timestamp','Zweryfikowana granica sesji USA; nie jest godziną publikacji')}</a></p>:null}
 {e.ticker==='INTC'&&k==='call'?<p>{et('The dated announcement specifies PDT; the conflicting PST widget was not used.','Datowana zapowiedź podaje PDT; sprzecznego oznaczenia PST z widgetu nie użyto.')}</p>:null}
 </section>)}
 {e.history.length>2?<><h4>{et('Date history','Historia terminów')}</h4><ul>{e.history.map((c,i)=><li key={i}>{c.component} · {status(c.date_status)} · {c.source_local_date??'—'} · {c.precision} · {c.verified_on??'—'}</li>)}</ul></>:null}
 </div></td></tr>:null}</>;
}

export function EarningsCalendar({startDate,endDate}:{startDate:string;endDate:string}){
 const [data,setData]=useState<CalendarItemsResponse>(),[error,setError]=useState(false),[retry,setRetry]=useState(0);
 useEffect(()=>{const abort=new AbortController();setData(undefined);setError(false);
 fetchEarnings(startDate,endDate,[],abort.signal).then(value=>{if(!abort.signal.aborted)setData(value);}).catch(()=>{if(!abort.signal.aborted)setError(true);});return()=>abort.abort();},[startDate,endDate,retry]);
 const events=(data?.events??[]).filter((e):e is EarningsItem=>e.domain==='earnings');
 const groups=new Map<string,EarningsItem[]>();
 for(const e of events.sort(compareEarnings)){
  const a=earningsAnchor(e);const key=a.poland_date?`pl:${a.poland_date}`:`source:${earningsDate(e)}`;
  groups.set(key,[...(groups.get(key)??[]),e]);
 }
 return <section className="earnings-calendar" aria-label={et('Company earnings','Wyniki spółek')}>
 <h2>{et('Company earnings','Wyniki spółek')}</h2>
 <p>{et('All companies · Actual / Forecast · USD','Wszystkie spółki · Actual / Prognoza · USD')}</p>
 {events.some(e=>e.financial_store_status==='not_activated')?<p role="status">{et('Financial data module not activated in this database. Earnings dates remain available.','Moduł danych finansowych nieaktywny w tej bazie. Terminy wyników pozostają dostępne.')}</p>:null}
 {error?<div role="alert">{et('Unable to load earnings dates. Stored macro data remain available.','Nie można wczytać terminów wyników spółek. Zapisane dane makro pozostają dostępne.')} <button onClick={()=>setRetry(v=>v+1)}>{et('Retry','Ponów')}</button></div>:!data?<p role="status">{et('Loading earnings dates…','Wczytywanie terminów wyników…')}</p>:null}
 {data&&!events.length?<p>{et('No confirmed events in this range.','Brak potwierdzonych wydarzeń w tym zakresie.')}</p>:null}
 {data&&(events.length>0||data.undated.length>0)?<>
 <p className="earnings-scroll-hint">{et('On small screens, scroll the table horizontally for values and sources.','Na małym ekranie przewiń tabelę poziomo, aby zobaczyć wartości i źródła.')}</p>
 <div className="earnings-table-scroll" role="region" aria-label={et('Earnings table','Tabela wyników')} tabIndex={0}>
 <table className="earnings-table"><thead><tr><th scope="col">{et('Company','Spółka')}</th><th scope="col">{et('Results time · Poland','Czas wyników · Polska')}</th><th scope="col">EPS GAAP<small>Actual / {et('Forecast','Prognoza')}</small></th><th scope="col">{et('Revenue','Przychody')}<small>Actual / {et('Forecast','Prognoza')}</small></th><th scope="col">Status</th><th scope="col">{et('Details / Source','Szczegóły / Źródło')}</th></tr></thead>
 {[...groups].map(([key,rows])=><tbody key={key}><tr className="earnings-date"><th colSpan={6} scope="rowgroup"><h3>{formatAgendaDate(key.split(':')[1])}{key.startsWith('source:')?` · ${et('Issuer date; Polish publication day/time not established','Data emitenta; dzień i godzina publikacji w PL nieustalone')}`:''}</h3></th></tr>{rows.map(e=><EarningsRow key={e.event_id} event={e}/>)}</tbody>)}
 {data.undated.length?<tbody><tr className="earnings-date"><th colSpan={6} scope="rowgroup"><h3>{et('Date not announced','Termin nieogłoszony')}</h3></th></tr>{[...data.undated].sort(compareEarnings).map(e=><EarningsRow key={e.event_id} event={e}/>)}</tbody>:null}
 </table></div></>:null}
 </section>;
}
