import type {CalendarEvent,CalendarMeasure} from '../api/macrolens';
import {getLanguage,getLocale} from '../i18n/language';
import {eventDay,eventInstant,eventImportanceStars} from '../brief/upcomingEvents';
import {shiftDate,todayIso,weekRange} from './calendarDates';
export type DatePreset='yesterday'|'today'|'tomorrow'|'week'|'nextWeek'|'custom';
export const MAX_DAYS=366;
export function presetRange(preset:DatePreset,now=new Date()){
 const today=todayIso(now),week=weekRange(today);
 if(preset==='week'||preset==='custom')return week;
 if(preset==='nextWeek')return {startDate:shiftDate(week.startDate,7),endDate:shiftDate(week.endDate,7)};
 const day=shiftDate(today,preset==='yesterday'?-1:preset==='tomorrow'?1:0);return {startDate:day,endDate:day};
}
export function rangeError(start:string,end:string):string|null {
 if(!/^\d{4}-\d{2}-\d{2}$/.test(start)||!/^\d{4}-\d{2}-\d{2}$/.test(end)||!Number.isFinite(Date.parse(start))||!Number.isFinite(Date.parse(end))||new Date(start).toISOString().slice(0,10)!==start||new Date(end).toISOString().slice(0,10)!==end)return 'Choose valid start and end dates.';
 if(start>end)return 'The start date must not follow the end date.';
 if((Date.parse(end)-Date.parse(start))/86400000>=MAX_DAYS)return 'Calendar ranges are limited to 366 days.';
 return null;
}
export const calendarCategories=[{id:'labor',label:'Labor'},{id:'inflation',label:'Inflation'},{id:'activity',label:'Growth and consumer'},{id:'housing',label:'Housing'},{id:'financial',label:'Fed and financial conditions'}];
export function eventCategories(event:CalendarEvent):string[]{
 if(event.event_type?.startsWith('fomc_'))return ['financial'];
 return [...new Set(event.series.map(s=>['growth','consumer'].includes(s.category)?'activity':['financial_conditions','financial'].includes(s.category)?'financial':s.category))];
}
export function filterEvents(events:CalendarEvent[],stars:Set<number>,unknown:boolean,categories:Set<string>){return events.filter(e=>{const level=eventImportanceStars(e);return (level===null?unknown:stars.has(level))&&(categories.size===0||eventCategories(e).some(c=>categories.has(c)));});}
export function groupAgenda(events:CalendarEvent[]){
 const unique=new Map<string,CalendarEvent>();for(const e of events){const key=e.event_id??`${e.release_id}:${e.release_date}`;if(!unique.has(key)||eventInstant(e)!==null)unique.set(key,e);}
 const groups=new Map<string,CalendarEvent[]>();
 for(const e of [...unique.values()].sort((a,b)=>eventDay(a).localeCompare(eventDay(b))||(eventInstant(a)??Infinity)-(eventInstant(b)??Infinity)||a.release_name.localeCompare(b.release_name))){const day=eventDay(e);groups.set(day,[...(groups.get(day)??[]),e]);}
 return [...groups].map(([date,events])=>({date,events}));
}
export function nextInstant(events:CalendarEvent[],now:Date){return Math.min(...events.map(eventInstant).filter((v):v is number=>v!==null&&v>now.getTime()));}
export function countdown(instant:number,now:Date){
 const remaining=instant-now.getTime();if(!Number.isFinite(remaining)||remaining<=0)return null;
 if(remaining>=86400000)return {unit:'days' as const,days:Math.floor(remaining/86400000)};
 if(remaining<60000)return {unit:'soon' as const};
 const minutes=Math.floor(remaining/60000);return {unit:'time' as const,hours:Math.floor(minutes/60),minutes:minutes%60};
}
export function countdownText(instant:number,now:Date){
 const value=countdown(instant,now);if(!value)return null;const pl=getLanguage()==='pl';
 if(value.unit==='days')return pl?`Za ${value.days} ${value.days===1?'dzień':'dni'}`:`In ${value.days} ${value.days===1?'day':'days'}`;
 if(value.unit==='soon')return pl?'Za mniej niż minutę':'In less than a minute';
 const hours=value.hours?(pl?`${value.hours} godz.`:`${value.hours} ${value.hours===1?'hour':'hours'}`):'';
 const minutes=value.minutes?(pl?`${value.minutes} min`:`${value.minutes} ${value.minutes===1?'minute':'minutes'}`):'';
 return `${pl?'Za':'In'} ${[hours,minutes].filter(Boolean).join(' ')}`;
}
export function countdownDelay(instant:number,now:Date){
 const remaining=instant-now.getTime();if(!Number.isFinite(remaining)||remaining<=0)return null;
 return remaining<60000?remaining:remaining%(remaining>=86400000?86400000:60000)+1;
}
export function measureValue(value:number|null,unit:string){if(value===null||!Number.isFinite(value))return '—';const digits=['claims','thousand homes/year (SAAR)','thousand jobs','thousand openings'].includes(unit)?0:2;const number=new Intl.NumberFormat(getLocale(),{maximumFractionDigits:digits,minimumFractionDigits:unit==='percent'?2:0}).format(value);return number+(unit==='percent'?'%':'');}
export function resultPending(event:CalendarEvent,measure:CalendarMeasure,now:Date){const instant=eventInstant(event);return measure.actual===null&&(instant!==null?instant<=now.getTime():eventDay(event)<todayIso(now));}
