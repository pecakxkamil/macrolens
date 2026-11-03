import type {CalendarEvent} from '../api/macrolens';
export type EarningsPrecision='exact'|'approximate'|'after_close'|'before_open'|'date_only'|'unknown';
export interface EarningsTime {
 component:'release'|'call'; date_status:'unknown'|'confirmed'|'changed'|'cancelled'; precision:EarningsPrecision;
 source_local_date:string|null;source_local_time:string|null;source_timezone:string|null;timezone_label_raw:string|null;
 scheduled_at_utc:string|null;expected_time_utc:string|null;poland_date:string|null;
 session_boundary_utc:string|null;session_boundary_source:string|null;
 source_url:string|null;verified_on:string|null;facts:string|null;verification_method:string|null;sequence:number;
}
export interface EarningsItem {
 domain:'earnings';event_id:string;company_id:string;cik:string;name:string;ticker:string;
 fiscal_year:number;fiscal_quarter:number;period_label:string;period_end:string|null;publication_status:'unconfirmed';
 release:EarningsTime;call:EarningsTime;history:EarningsTime[];
}
export type MacroItem={domain:'macro';event:CalendarEvent};
export type CalendarItem=MacroItem|EarningsItem;
export interface CalendarItemsResponse {events:CalendarItem[];undated:EarningsItem[];macro_data_revision:string|null;earnings_data_revision:string|null;assembled_at:string;snapshot_scope:string}
const base=import.meta.env.VITE_API_BASE_URL?.replace(/\/$/,'')??'http://127.0.0.1:8000';
export async function fetchEarnings(start:string,end:string,tickers:string[],signal:AbortSignal):Promise<CalendarItemsResponse>{
 const query=new URLSearchParams({start_date:start,end_date:end,domains:'earnings'});
 if(tickers.length)query.set('tickers',tickers.join(','));
 const response=await fetch(`${base}/api/v1/calendar/events?${query}`,{signal});
 if(!response.ok)throw new Error('Earnings calendar unavailable');
 return response.json();
}
