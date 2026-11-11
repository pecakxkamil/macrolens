import type {CalendarEvent} from '../api/macrolens';
import {eventDay,eventInstant} from '../brief/upcomingEvents';
import {warsawDate} from '../datePeriods';
import {formatPolandTime} from './calendarDates';
import {earningsDate} from './earningsFinancialPresentation';
import type {EarningsItem} from './earningsTypes';
import {marketCap} from './earningsMarketCap';
import {et} from './earningsPresentation';

type Base={key:string;day:string;instant:number|null};
export type TimelineEvent=(Base&{kind:'macro';event:CalendarEvent})|(Base&{kind:'earnings';event:EarningsItem;clock:string;description:string});
const valid=(value:string|null|undefined)=>{const n=value?Date.parse(value):NaN;return Number.isFinite(n)?n:null;};
const verified=(e:EarningsItem)=>['confirmed','changed'].includes(e.release.date_status)&&Boolean(e.release.verified_on&&e.release.source_url?.startsWith('https://')&&e.release.verification_method==='manually_verified_official_source');

export function earningsTimeline(e:EarningsItem):Extract<TimelineEvent,{kind:'earnings'}>|null{
 const release=e.release,session=e.session_context?.us_listed?e.session_context.release:null;
 let instant:number|null=null,clock='—',description=et('Release time unconfirmed; conference time is not the release time.','Czas publikacji niepotwierdzony; godzina konferencji nie jest godziną publikacji.');
 if(verified(e)&&release.precision==='exact'){
  instant=valid(release.scheduled_at_utc);
  if(instant!==null){clock=formatPolandTime(release.scheduled_at_utc).replace(/ PL$/,'');description=et('Official release time, Europe/Warsaw.','Oficjalna godzina publikacji, Europe/Warsaw.');}
 }else if(verified(e)&&session&&session.source.startsWith('https://')){
  const open=valid(session.open_at_utc),close=valid(session.close_at_utc),expected=valid(release.expected_time_utc);
  let window=release.precision;
  if(window==='approximate'&&expected!==null&&open!==null&&close!==null){window=expected>=close?'after_close':expected<open?'before_open':'unknown';}
  if(open!==null&&close!==null&&open<close){
   if(window==='after_close'){
    instant=close;clock=formatPolandTime(session.close_at_utc).replace(/ PL$/,'')+'+';
    description=et('Indicative window after the US session close; not a confirmed release minute. Session calendar: ','Orientacyjne okno po zamknięciu sesji USA; nie potwierdzona minuta publikacji. Kalendarz sesji: ')+session.source;
   }else if(window==='before_open'){
    // Sort by the known boundary; do not manufacture a beginning of this window.
    instant=open;clock='< '+formatPolandTime(session.open_at_utc).replace(/ PL$/,'');
    description=et('Indicative window before the US session open; ordered by its opening boundary, not a release timestamp.','Orientacyjne okno przed otwarciem sesji USA; kolejność według granicy otwarcia, nie czasu publikacji.');
   }
  }
 }
 const day=instant!==null?warsawDate(new Date(instant)):(release.poland_date??release.source_local_date??e.financial_release_date??earningsDate(e));
 return day?{kind:'earnings',key:'earnings:'+e.event_id,day,instant,event:e,clock,description}:null;
}

/** Editorial UI tier; no conversion or inference from stale/unavailable caps. */
export function earningsImportance(e:EarningsItem):3|null{
 if(!marketCap(e)||!e.market_cap_usd)return null;
 const integer=e.market_cap_usd.split('.')[0];
 return BigInt(integer)>=200000000000n?3:null;
}

export function unifiedGroups(macro:CalendarEvent[],earnings:EarningsItem[],start:string,end:string){
 const unique=new Map<string,TimelineEvent>();
 for(const event of macro){const row:TimelineEvent={kind:'macro',key:'macro:'+(event.event_id??`${event.release_id}:${event.release_date}`),day:eventDay(event),instant:eventInstant(event),event};unique.set(row.key,row);}
 for(const event of earnings){const row=earningsTimeline(event);if(row)unique.set(row.key,row);}
 const groups=new Map<string,TimelineEvent[]>();
 // Macro API already owns its selected range, including its publication-stage
 // projections. Earnings additionally needs local-day filtering after conversion.
 const sorted=[...unique.values()].filter(r=>r.kind==='macro'||(r.day>=start&&r.day<=end)).sort((a,b)=>a.day.localeCompare(b.day)||(a.instant??Infinity)-(b.instant??Infinity)||a.key.localeCompare(b.key));
 for(const row of sorted)groups.set(row.day,[...(groups.get(row.day)??[]),row]);
 return [...groups].map(([date,rows])=>({date,rows}));
}
