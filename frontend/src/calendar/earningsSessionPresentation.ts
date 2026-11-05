import {formatPolandTime} from './calendarDates';
import type {EarningsItem,EarningsTime,UsEarningsSession} from './earningsTypes';
import {earningsTimeLabel} from './earningsTimeLabels';

export type EarningsWindow='after_close'|'before_open'|'during_session'|'unknown';
export type EarningsWindowBasis='official'|'indicative'|'unknown';
const verified=(c:EarningsTime)=>['confirmed','changed'].includes(c.date_status)
 &&Boolean(c.verified_on&&c.source_url?.startsWith('https://')&&c.verification_method==='manually_verified_official_source');
const position=(instant:string,s:UsEarningsSession):EarningsWindow=>{
 const value=Date.parse(instant),open=Date.parse(s.open_at_utc),close=Date.parse(s.close_at_utc);
 if(!Number.isFinite(value)||!Number.isFinite(open)||!Number.isFinite(close)||open>=close)return 'unknown';
 const day=new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(value));
 if(day!==s.date)return 'unknown';
 return value<open?'before_open':value>=close?'after_close':'during_session';
};

export function earningsSessionPresentation(e:EarningsItem):{window:EarningsWindow;basis:EarningsWindowBasis;call:string|null}{
 const release=e.release,context=e.session_context;
 let window:EarningsWindow='unknown',basis:EarningsWindowBasis='unknown';
 if(verified(release)){
  if(release.precision==='after_close'||release.precision==='before_open'){
   window=release.precision;basis='official';
  }else if(release.precision==='exact'&&release.scheduled_at_utc&&context?.release){
   window=position(release.scheduled_at_utc,context.release);basis=window==='unknown'?'unknown':'official';
  }else if(release.precision==='approximate'&&release.expected_time_utc&&context?.release){
   const estimated=position(release.expected_time_utc,context.release);
   if(estimated==='before_open'||estimated==='after_close'){window=estimated;basis='indicative';}
  }
 }
 // A verified same-day post-close call may suggest a window, never a release minute.
 const callVerified=verified(e.call)&&e.call.precision==='exact'&&Boolean(e.call.scheduled_at_utc)
  &&Number.isFinite(Date.parse(e.call.scheduled_at_utc!));
 const missingWindow=['unknown','date_only'].includes(release.precision)&&release.date_status!=='cancelled'
  &&!release.scheduled_at_utc&&!release.expected_time_utc;
 if(window==='unknown'&&missingWindow&&callVerified&&context?.us_listed&&context.release&&context.call
    &&context.release.date===context.call.date
    &&(!e.financial_release_date||e.financial_release_date===context.release.date)
    &&position(e.call.scheduled_at_utc!,context.call)==='after_close'){
  window='after_close';basis='indicative';
 }
 const clock=callVerified?formatPolandTime(e.call.scheduled_at_utc).replace(/ PL$/,''):null;
 return {window,basis,call:clock?`${earningsTimeLabel('call')}: ${clock} ${earningsTimeLabel('warsaw')}`:null};
}
export const earningsSessionLabel=(e:EarningsItem)=>earningsTimeLabel(earningsSessionPresentation(e).window);
