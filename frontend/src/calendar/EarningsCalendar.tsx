import {companyDisplayName} from './earningsCompanyNames';
import {ForecastValue} from './ForecastValue';
import type {ForecastDetail} from '../api/macrolens';
import {useEarningsCalendar,type EarningsCalendarState} from './useEarningsCalendar';
import type {EarningsItem} from './earningsTypes';
import {et} from './earningsPresentation';
import {compareEarnings,earningsDate,earningsActual,financialValue} from './earningsFinancialPresentation';
import {formatAgendaDate} from './calendarDates';
import './earnings.css';
import {marketCap} from './earningsMarketCap';
import {earningsSessionPresentation} from './earningsSessionPresentation';
import {earningsTimeLabel} from './earningsTimeLabels';
import {earningsChange} from './earningsComparison';
import {MissingValue,earningsMissingReason} from './MissingValue';

function reportSource(e:EarningsItem):string|null {
 const latest=e.report_documents?.[e.report_documents.length-1];
 if(latest?.document_type==='earnings_release'&&latest.verified_on&&latest.source_url.startsWith('https://'))return latest.source_url;
 for(const m of [e.current_eps_actual??e.reported_eps_actual??e.gaap_diluted_eps_actual,e.current_revenue_actual??e.revenue_actual]){
  if(m?.document_type==='earnings_release'&&m.verified_on&&m.source_url.startsWith('https://'))return m.source_url;
 }
 return null;
}

function EarningsRow({event:e}:{event:EarningsItem}){
 const source=reportSource(e),cap=marketCap(e),timing=earningsSessionPresentation(e);
 const company=<><strong>{e.ticker} · {e.period_label}</strong><span className="earnings-company-name">{companyDisplayName(e)}</span></>;
 return <tr className="earnings-row">
 <th scope="row">{source?<a className="earnings-company-link" href={source} target="_blank" rel="noreferrer" aria-label={`${e.ticker} · ${e.period_label} · ${et('Official financial report','Oficjalny raport finansowy')}`}>{company}</a>:company}</th>
 <td className="earnings-center">{earningsTimeLabel(timing.window)}{timing.call?<small>{timing.call}</small>:null}</td>
 {(['current_eps','previous_eps','current_revenue','previous_revenue'] as const).map(key=>{
 const change=key.startsWith('current')?earningsChange(e,key==='current_eps'?'eps':'revenue'):null;
 const metric=key.endsWith('eps')?'eps':'revenue',text=financialValue(earningsActual(e,key)),forecast=financialValue(e[`${key}_forecast`]);
 const value=text==='—'?<MissingValue reason={earningsMissingReason(e,metric,change?'current':'previous')}/>:text;
 return <td key={key} className={`earnings-number${key.startsWith('previous')?' earnings-previous':''}`}>{change?<span className={`earnings-actual--${change.direction}`} title={text==='—'?undefined:`${et('vs previous','vs poprzedni')}: ${change.text}`}>{value}</span>:<span className="earnings-previous-value">{value}</span>}{e[`${key}_forecast`]?.kind?<ForecastValue forecast={e[`${key}_forecast`] as ForecastDetail} currency={e[`${key}_forecast`]?.currency}/>:<small>{forecast==='—'?<MissingValue reason={earningsMissingReason(e,metric,'forecast')}/>:forecast}</small>}</td>;
 })}
 <td className="earnings-number">{cap?cap.value:<MissingValue reason={et('No current verified market capitalization.','Brak aktualnej zweryfikowanej kapitalizacji.')}/>}</td>
 </tr>;
}

export function EarningsCalendar({startDate,endDate,state}:{startDate:string;endDate:string;state?:EarningsCalendarState}){
 const own=useEarningsCalendar(startDate,endDate,!state);
 const {data,error,retry}=state??own;
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
 {error?<div role="alert">{et('Unable to load earnings dates. Stored macro data remain available.','Nie można wczytać terminów wyników spółek. Zapisane dane makro pozostają dostępne.')} <button onClick={retry}>{et('Retry','Ponów')}</button></div>:!data?<p role="status">{et('Loading earnings dates…','Wczytywanie terminów wyników…')}</p>:null}
 {data&&!events.length?<p>{et('No earnings releases with a confirmed date in the selected range.','Brak publikacji wyników z potwierdzoną datą w wybranym zakresie.')}</p>:null}
 {data&&events.length>0?<>
 <p className="earnings-scroll-hint">{et('On small screens, scroll the table horizontally for values and sources.','Na małym ekranie przewiń tabelę poziomo, aby zobaczyć wartości i źródła.')}</p>
 <div className="earnings-table-scroll" role="region" aria-label={et('Earnings table','Tabela wyników')} tabIndex={0}>
 <table className="earnings-table"><colgroup><col className="earnings-company-column"/><col className="earnings-time-column"/><col className="earnings-eps-column"/><col className="earnings-eps-column"/><col className="earnings-revenue-column"/><col className="earnings-revenue-column"/><col className="earnings-market-cap-column"/></colgroup><thead><tr><th scope="col">{et('Company','Spółka')}</th><th scope="col" className="earnings-center">{et('Results time · Poland','Czas wyników · Polska')}</th>{[["Current EPS","EPS aktualny"],["Previous EPS","EPS poprzednio"],["Current revenue","Przychody aktualne"],["Previous revenue","Przychody poprzednio"]].map(([en,pl])=><th key={en} scope="col" className="earnings-center">{et(en,pl)}<small>Actual / {et('Forecast','Prognoza')}</small></th>)}<th scope="col" className="earnings-center" aria-label="Market Cap">Market Cap</th></tr></thead>
 {[...groups].map(([key,rows])=><tbody key={key}><tr className="earnings-date"><th colSpan={7} scope="rowgroup"><h3>{formatAgendaDate(key)}</h3></th></tr>{rows.map(e=><EarningsRow key={e.event_id} event={e}/>)}</tbody>)}
 </table></div></>:null}
 </section>;
}
