import {useEffect,useState} from 'react';
import {fetchEarnings,type CalendarItemsResponse,type EarningsItem} from './earningsTypes';
import {earningsAnchor,earningsDay,earningsSummary,earningsTime,et} from './earningsPresentation';
import {formatAgendaDate,formatPolandTime} from './calendarDates';
import './earnings.css';

function EarningsRow({event:e}:{event:EarningsItem}){
 const [open,setOpen]=useState(false);const anchor=earningsAnchor(e);
 const id=`details-${e.event_id}`;
 const status=(value:string)=>({confirmed:et('Confirmed','Potwierdzono'),changed:et('Changed','Zmieniono'),cancelled:et('Cancelled','Odwołano'),unknown:et('Date not announced','Termin nieogłoszony')}[value]??value);
 return <article className="earnings-row" onKeyDown={ev=>{if(ev.key==='Escape'&&open){ev.stopPropagation();setOpen(false);document.getElementById(`button-${e.event_id}`)?.focus();}}}>
 <button id={`button-${e.event_id}`} aria-expanded={open} aria-controls={id} onClick={()=>setOpen(v=>!v)}><strong>{e.ticker} · {e.period_label}</strong> · {earningsSummary(e)}{anchor===e.call&&anchor.date_status!=='unknown'?` · ${et('Conference date','Data konferencji')}`:''}</button>
 <span>{e.name} · {status(anchor.date_status)}</span>
 {open?<div id={id} className="earnings-details">
 <p>{et('Results','Wyniki')}: {earningsTime(e.release)}</p>
 <p>{et('Conference','Konferencja')}: {e.call.scheduled_at_utc&&e.call.date_status!=='cancelled'?formatPolandTime(e.call.scheduled_at_utc):earningsTime(e.call)}</p>
 <p>{et('Publication not verified; the scheduled date does not prove results are available.','Publikacja niezweryfikowana; zaplanowana data nie potwierdza dostępności wyników.')}</p>
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
 </div>:null}</article>;
}

export function EarningsCalendar({startDate,endDate}:{startDate:string;endDate:string}){
 const [tickers,setTickers]=useState<string[]>([]),[data,setData]=useState<CalendarItemsResponse>(),[error,setError]=useState(false),[retry,setRetry]=useState(0);
 useEffect(()=>{const abort=new AbortController();setData(undefined);setError(false);
 fetchEarnings(startDate,endDate,tickers,abort.signal).then(value=>{if(!abort.signal.aborted)setData(value);}).catch(()=>{if(!abort.signal.aborted)setError(true);});return()=>abort.abort();},[startDate,endDate,tickers,retry]);
 const events=(data?.events??[]).filter((e):e is EarningsItem=>e.domain==='earnings');
 const groups=new Map<string,EarningsItem[]>();
 for(const e of events.sort((a,b)=>(earningsDay(a)??'').localeCompare(earningsDay(b)??'')||a.ticker.localeCompare(b.ticker))){
  const a=earningsAnchor(e);const key=a.poland_date?`pl:${a.poland_date}`:`source:${a.source_local_date}`;
  groups.set(key,[...(groups.get(key)??[]),e]);
 }
 return <section className="earnings-calendar" aria-label={et('Company earnings','Wyniki spółek')}>
 <h2>{et('Company earnings','Wyniki spółek')}</h2>
 <fieldset><legend>{et('Tickers','Tickery')}</legend>{['NVDA','AMZN','INTC'].map(symbol=><label key={symbol}><input type="checkbox" checked={tickers.includes(symbol)} onChange={()=>setTickers(old=>old.includes(symbol)?old.filter(s=>s!==symbol):[...old,symbol])}/>{symbol}</label>)}</fieldset>
 <p>{et('No selection: all companies.','Brak wyboru: wszystkie spółki.')}</p>
 {error?<div role="alert">{et('Unable to load earnings dates. Stored macro data remain available.','Nie można wczytać terminów wyników spółek. Zapisane dane makro pozostają dostępne.')} <button onClick={()=>setRetry(v=>v+1)}>{et('Retry','Ponów')}</button></div>:!data?<p role="status">{et('Loading earnings dates…','Wczytywanie terminów wyników…')}</p>:null}
 {data&&!events.length?<p>{et('No confirmed events in this range.','Brak potwierdzonych wydarzeń w tym zakresie.')}</p>:null}
 {[...groups].map(([key,rows])=><section key={key}><h3>{formatAgendaDate(key.split(':')[1])}{key.startsWith('source:')?` · ${et('Issuer date; Polish publication day/time not established','Data emitenta; dzień i godzina publikacji w PL nieustalone')}`:''}</h3>{rows.map(e=><EarningsRow key={e.event_id} event={e}/>)}</section>)}
 {data?.undated.length?<section><h3>{et('Date not announced','Termin nieogłoszony')}</h3>{data.undated.map(e=><EarningsRow key={e.event_id} event={e}/>)}</section>:null}
 </section>;
}
