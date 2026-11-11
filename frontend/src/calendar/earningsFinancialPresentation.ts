import {getLanguage} from '../i18n/language';
import type {EarningsItem,FinancialObservation} from './earningsTypes';
import {earningsAnchor,earningsDay,et} from './earningsPresentation';

export type EarningsActualKey='current_eps'|'previous_eps'|'current_revenue'|'previous_revenue';
/** The same explicit-null and legacy-field rules in both Calendar views. */
export function earningsActual(e:EarningsItem,key:EarningsActualKey):FinancialObservation|null|undefined {
 if(key==='current_eps')return e.current_eps_actual===undefined?e.reported_eps_actual??e.gaap_diluted_eps_actual:e.current_eps_actual;
 if(key==='current_revenue')return e.current_revenue_actual===undefined?e.revenue_actual:e.current_revenue_actual;
 return e[`${key}_actual`];
}

export function financialValue(value:FinancialObservation|null|undefined):string {
 if(!value)return '—';
 const n=Number(value.actual);if(!Number.isFinite(n))return '—';
 const language=getLanguage()==='pl'?'pl-PL':'en-US';
 if(value.metric!=='revenue')return `${new Intl.NumberFormat(language,{minimumFractionDigits:2,maximumFractionDigits:6}).format(n)} ${value.currency}`;
 const divisor=Math.abs(n)>=1e9?1e9:Math.abs(n)>=1e6?1e6:1;
 return `${new Intl.NumberFormat(language,{maximumFractionDigits:2}).format(n/divisor)}${divisor===1e9?et(' bn',' mld'):divisor===1e6?et(' m',' mln'):''} ${value.currency}`;
}
export function epsBasis(value:FinancialObservation|null|undefined):string {
 const standard=value?.reporting_standard==='IFRS'?'IFRS':value?.reporting_standard==='US_GAAP'?'US GAAP':'GAAP';
 const shares=value?.share_basis==='ADR'?'ADR':et('ordinary/common share','akcja zwykła');
 return `${standard} diluted EPS · ${shares}${value?.methodology==='gaap_diluted_attributable_to_intel'?et(' · attributable to Intel',' · przypadający Intel'):''}`;
}
export function financialStatus(e:EarningsItem,compact=false):string {
 const state=e.publication_state;
 if(compact){
  if(state)return ({scheduled:et('Scheduled','Zaplanowano'),published_pending:et('Published · pending','Opublikowano · weryfikacja'),published_complete:et('Published','Opublikowano'),published_partial:et('Published · partial','Opublikowano · częściowe'),date_passed_unconfirmed:et('Date passed','Termin minął'),unconfirmed:et('Date not announced','Termin nieogłoszony')})[state.code];
  return e.financial_data_status==='complete'?et('Published','Opublikowano'):e.financial_data_status==='partial'?et('Published · partial','Opublikowano · częściowe'):et('Unconfirmed','Niepotwierdzono');
 }
 if(state){
  const missing=state.missing_metrics.map(m=>m==='revenue'?et('revenue','przychody'):'EPS').join(', ');
  return ({scheduled:et('Scheduled','Zaplanowano'),published_pending:et('Published · financials pending','Opublikowano · dane w weryfikacji'),published_complete:et('Published · actuals verified','Opublikowano · dane zweryfikowane'),published_partial:et('Published · partial data','Opublikowano · dane częściowe')+et(' · missing: ',' · brak: ')+missing,date_passed_unconfirmed:et('Date passed · release unconfirmed','Termin minął · publikacja niepotwierdzona'),unconfirmed:et('Release unconfirmed','Publikacja niepotwierdzona')})[state.code];
 }
 return e.financial_data_status==='complete'?et('Published','Opublikowano'):e.financial_data_status==='partial'?et('Published · partial data','Opublikowano · dane częściowe'):et('Publication unverified','Publikacja niezweryfikowana');
}
export function earningsDate(e:EarningsItem):string|null {return earningsDay(e)??e.financial_release_date??null;}
export function compareEarnings(a:EarningsItem,b:EarningsItem):number {
 const time=(e:EarningsItem)=>{const t=earningsAnchor(e);const instant=t.scheduled_at_utc??t.expected_time_utc??t.session_boundary_utc;return instant?`0:${new Date(instant).toISOString()}`:'1';};
 return (earningsDate(a)??'9999-12-31').localeCompare(earningsDate(b)??'9999-12-31')||time(a).localeCompare(time(b))||a.ticker.localeCompare(b.ticker)||a.event_id.localeCompare(b.event_id);
}
