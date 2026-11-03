import {getLanguage} from '../i18n/language';
import {formatPolandTime} from './calendarDates';
import type {EarningsItem,EarningsTime} from './earningsTypes';
export const et=(en:string,pl:string)=>getLanguage()==='pl'?pl:en;
const clock=(utc:string)=>formatPolandTime(utc).replace(/ PL$/,'');
export function earningsTime(c:EarningsTime):string{
 if(c.date_status==='unknown')return et('Date not announced','Termin nieogłoszony');
 if(c.date_status==='cancelled')return et('Cancelled','Odwołano');
 if(c.precision==='exact'&&c.scheduled_at_utc)return `${clock(c.scheduled_at_utc)} — ${et('results','wyniki')}`;
 if(c.precision==='approximate'&&c.expected_time_utc)return `${et('approx.','ok.')} ${clock(c.expected_time_utc)} — ${et('results','wyniki')}`;
 if(c.precision==='after_close')return c.session_boundary_utc?`${clock(c.session_boundary_utc)}+ — ${et('after US close','po sesji USA')}`:et('After US close','Po sesji USA');
 if(c.precision==='before_open')return et('Before US open','Przed otwarciem USA')+(c.session_boundary_utc?` (${et('before','przed')} ${clock(c.session_boundary_utc)} PL)`:'');
 return et('Time not announced','Godzina nieogłoszona');
}
export function earningsAnchor(e:EarningsItem){return e.release.date_status!=='unknown'?e.release:e.call;}
export function earningsDay(e:EarningsItem){const a=earningsAnchor(e);return a.poland_date??a.source_local_date;}
export function earningsSummary(e:EarningsItem){
 if(e.release.date_status==='unknown'&&e.call.date_status==='unknown')return et('Date not announced','Termin nieogłoszony');
 if(e.release.date_status!=='unknown')return earningsTime(e.release);
 return et('Results: time unknown','Wyniki: godzina nieznana');
}
