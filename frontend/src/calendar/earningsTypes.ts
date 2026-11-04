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
 financial_store_status?:'available'|'not_activated';
 financial_data_status?:'complete'|'partial'|'unavailable';
 financial_publication_status?:'published'|'unconfirmed';
 financial_release_date?:string|null;
 revenue_actual?:FinancialObservation|null;gaap_diluted_eps_actual?:FinancialObservation|null;
 reported_eps_actual?:FinancialObservation|null;
 report_store_status?:'available'|'not_activated';report_documents?:ReportDocument[];
 publication_state?:{code:'scheduled'|'published_pending'|'published_complete'|'published_partial'|'date_passed_unconfirmed'|'unconfirmed';reason:string;missing_metrics:string[];evidence:ReportDocument[]};
 revenue_consensus?:null;eps_consensus?:null;financial_history?:FinancialObservation[];
}
export interface FinancialObservation {
 metric:'revenue'|'gaap_diluted_eps'|'reported_diluted_eps';actual:string;currency:'USD'|'EUR'|'TWD';unit:string;
 source_value:string;source_unit:string;decimal_places:string;methodology:string;
 source_url:string;document_type:string;verified_on:string;captured_at:string;
 source_version:string;version:string;observation_id:string;supersedes_id:string|null;
 correction_reason:string|null;release_date:string;period_end:string|null;sec_accession?:string|null;
 evidence_method:string;availability_status?:string;
 reporting_standard?:'US_GAAP'|'IFRS';share_basis?:'not_applicable'|'common_share'|'ordinary_share'|'ADR';
}
export interface ReportDocument {document_type:'earnings_release'|'earnings_date_announcement';source_url:string;linked_from:string|null;release_date:string|null;period_end:string|null;verified_on:string;verification_method:string;source_version:string;facts:string;version:string;correction_reason:string|null;reporting_standard:'US_GAAP'|'IFRS'|null;reporting_currency:'USD'|'EUR'|'TWD'|null;eps_share_basis:string|null;captured_at:string;}
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
