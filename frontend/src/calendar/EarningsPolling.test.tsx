import {afterEach,expect,it,vi} from 'vitest';
import {act,cleanup,render,screen} from '@testing-library/react';
import {EarningsCalendar} from './EarningsCalendar';
import type {EarningsItem,FinancialObservation} from './earningsTypes';
import {setLanguage} from '../i18n/language';

const empty={component:'release',date_status:'unknown',precision:'unknown',source_local_date:null,source_local_time:null,source_timezone:null,timezone_label_raw:null,scheduled_at_utc:null,expected_time_utc:null,poland_date:null,session_boundary_utc:null,session_boundary_source:null,source_url:null,verified_on:null,facts:null,verification_method:null,sequence:0} as const;
const event:EarningsItem={domain:'earnings',event_id:'test',company_id:'issuer',cik:'0000000001',ticker:'TEST',name:'Synthetic issuer',fiscal_year:2026,fiscal_quarter:4,period_label:'Q4 2026',period_end:null,publication_status:'unconfirmed',release:{...empty,date_status:'confirmed',precision:'date_only',source_local_date:'2026-11-04'},call:{...empty,component:'call'},history:[],current_eps_actual:null};
const metric:FinancialObservation={metric:'reported_diluted_eps',actual:'1.17',currency:'USD',unit:'USD/share',source_value:'1.17',source_unit:'per_share',decimal_places:'2',methodology:'reported_diluted_total_eps',source_url:'https://issuer.example/results',document_type:'earnings_release',verified_on:'2026-11-04',captured_at:'2026-11-04T21:30:00Z',source_version:'synthetic',version:'1',observation_id:'test',supersedes_id:null,correction_reason:null,release_date:'2026-11-04',period_end:'2026-09-27',evidence_method:'automated_official_report_validation'};
const reply=(e=event)=>({ok:true,json:async()=>({events:[e],undated:[]})});
afterEach(()=>{cleanup();vi.useRealTimers();vi.unstubAllGlobals();vi.restoreAllMocks();setLanguage('en');});

it('reads a newly imported Actual on the next60second tick without reloading',async()=>{
 vi.useFakeTimers({toFake:['setInterval','clearInterval']});vi.spyOn(document,'visibilityState','get').mockReturnValue('visible');
 const fetcher=vi.fn().mockResolvedValueOnce(reply()).mockResolvedValue(reply({...event,current_eps_actual:metric}));vi.stubGlobal('fetch',fetcher);
 const view=render(<EarningsCalendar startDate="2026-11-04" endDate="2026-11-04"/>);
 await screen.findByText('TEST · Q4 2026');expect(screen.queryByText('1.17 USD')).not.toBeInTheDocument();
 await act(async()=>{await vi.advanceTimersByTimeAsync(60000);});
 expect(screen.getByText('1.17 USD')).toBeInTheDocument();expect(fetcher).toHaveBeenCalledTimes(2);
 expect(fetcher.mock.calls.every(c=>!c[1]?.method)).toBe(true);
 expect(view.container.querySelectorAll('thead th')).toHaveLength(7);
 view.unmount();await vi.advanceTimersByTimeAsync(120000);expect(fetcher).toHaveBeenCalledTimes(2);
});

it('pauses hidden tabs and refreshes once when visible again',async()=>{
 vi.useFakeTimers({toFake:['setInterval','clearInterval']});const visibility=vi.spyOn(document,'visibilityState','get').mockReturnValue('visible');
 const fetcher=vi.fn().mockResolvedValue(reply());vi.stubGlobal('fetch',fetcher);
 render(<EarningsCalendar startDate="2026-11-04" endDate="2026-11-04"/>);await screen.findByText('TEST · Q4 2026');
 visibility.mockReturnValue('hidden');await act(async()=>{await vi.advanceTimersByTimeAsync(120000);});expect(fetcher).toHaveBeenCalledTimes(1);
 visibility.mockReturnValue('visible');await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});expect(fetcher).toHaveBeenCalledTimes(2);
});

it('keeps stored values after a background request error',async()=>{
 vi.useFakeTimers({toFake:['setInterval','clearInterval']});vi.spyOn(document,'visibilityState','get').mockReturnValue('visible');
 const fetcher=vi.fn().mockResolvedValueOnce(reply({...event,current_eps_actual:metric})).mockRejectedValue(new Error('synthetic offline'));vi.stubGlobal('fetch',fetcher);
 render(<EarningsCalendar startDate="2026-11-04" endDate="2026-11-04"/>);await screen.findByText('1.17 USD');
 await act(async()=>{await vi.advanceTimersByTimeAsync(60000);});expect(screen.getByText('1.17 USD')).toBeInTheDocument();expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('does not overlap a slow initial request with interval checks',async()=>{
 vi.useFakeTimers({toFake:['setInterval','clearInterval']});vi.spyOn(document,'visibilityState','get').mockReturnValue('visible');
 let finish:(value:ReturnType<typeof reply>)=>void=()=>{};
 const fetcher=vi.fn().mockReturnValue(new Promise(resolve=>{finish=resolve;}));vi.stubGlobal('fetch',fetcher);
 render(<EarningsCalendar startDate="2026-11-04" endDate="2026-11-04"/>);
 await act(async()=>{await vi.advanceTimersByTimeAsync(120000);});expect(fetcher).toHaveBeenCalledTimes(1);
 await act(async()=>{finish(reply());});expect(screen.getByText('TEST · Q4 2026')).toBeInTheDocument();
});
