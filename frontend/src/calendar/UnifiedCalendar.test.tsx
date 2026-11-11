import {afterEach,expect,it,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {CalendarPage} from './CalendarPage';
import {fetchCalendarAgenda,requestOverviewRefresh} from '../api/macrolens';
import type {CalendarEvent} from '../api/macrolens';
import type {EarningsItem,EarningsTime,CalendarItemsResponse} from './earningsTypes';
import {fetchEarnings} from './earningsTypes';
import {earningsImportance,earningsTimeline,unifiedGroups} from './unifiedCalendar';
import {setLanguage} from '../i18n/language';
vi.mock('../api/macrolens',async original=>({...await original<typeof import('../api/macrolens')>(),fetchCalendarAgenda:vi.fn(),requestOverviewRefresh:vi.fn()}));
vi.mock('./earningsTypes',async original=>({...await original<typeof import('./earningsTypes')>(),fetchEarnings:vi.fn()}));
const time:EarningsTime={component:'release',date_status:'confirmed',precision:'after_close',source_local_date:'2026-11-03',source_local_time:null,source_timezone:'America/New_York',timezone_label_raw:'ET',scheduled_at_utc:null,expected_time_utc:null,poland_date:'2026-11-03',session_boundary_utc:null,session_boundary_source:null,source_url:'https://issuer.example/results',verified_on:'2026-11-01',facts:null,verification_method:'manually_verified_official_source',sequence:1};
const base:EarningsItem={domain:'earnings',event_id:'amd',company_id:'amd',cik:'0000002488',ticker:'AMD',name:'AMD',fiscal_year:2026,fiscal_quarter:3,period_label:'Q3 2026',period_end:null,publication_status:'unconfirmed',release:time,call:{...time,component:'call',precision:'exact',scheduled_at_utc:'2026-11-03T23:00:00Z'},history:[],session_context:{us_listed:true,release:{date:'2026-11-03',open_at_utc:'2026-11-03T14:30:00Z',close_at_utc:'2026-11-03T21:00:00Z',source:'https://www.nyse.com/trade/hours-calendars'},call:null},market_cap_status:'verified_snapshot',market_cap_usd:'200000000000',market_cap_as_of:'2026-11-01'};
const macro={event_id:'macro',release_id:10,release_name:'Synthetic CPI',release_date:'2026-11-03',release_datetime_utc:'2026-11-03T13:30:00Z',importance:'high',market_impact_stars:3,importance_status:'classified',series:[],expects_numeric_result:false} as unknown as CalendarEvent;
const response=(events:EarningsItem[]):CalendarItemsResponse=>({events,undated:[],assembled_at:'2026-11-01T00:00:00Z',snapshot_scope:'test',earnings_data_revision:null,macro_data_revision:null});
afterEach(()=>{cleanup();vi.useRealTimers();vi.clearAllMocks();setLanguage('en');});

it.each([
 ['2026-03-16','20:00','21:00+'],['2026-03-30','20:00','22:00+'],
 ['2026-10-29','20:00','21:00+'],['2026-11-03','21:00','22:00+'],
 ['2026-11-27','18:00','19:00+'],['2026-12-24','18:00','19:00+'],
])('uses supplied session and Warsaw DST on %s',(day,utc,label)=>{
 const e={...base,release:{...time,source_local_date:day,poland_date:day},session_context:{...base.session_context!,release:{...base.session_context!.release!,date:day,open_at_utc:day+'T14:30:00Z',close_at_utc:day+'T'+utc+':00Z'}}};
 const before=JSON.stringify(e);expect(earningsTimeline(e)?.clock).toBe(label);expect(JSON.stringify(e)).toBe(before);
});
it('never substitutes the conference time or manufactures a session',()=>{
 expect(earningsTimeline({...base,session_context:{us_listed:false,release:null,call:null}})?.clock).toBe('—');
 expect(earningsTimeline({...base,release:{...time,precision:'date_only'}})?.clock).toBe('—');
 expect(earningsTimeline({...base,release:{...time,precision:'before_open'}})?.clock).toBe('< 15:30');
 expect(earningsTimeline({...base,session_context:{us_listed:true,release:null,call:null}})?.instant).toBeNull();
});
it('moves an exact UTC release to its Warsaw date',()=>{
 const row=earningsTimeline({...base,release:{...time,precision:'exact',scheduled_at_utc:'2026-11-03T23:30:00Z'}});
 expect(row).toMatchObject({day:'2026-11-04',clock:'00:30'});
});
it.each([['199999999999.99','verified_snapshot',null],['200000000000','verified_snapshot',3],['200000000000.01','verified_snapshot',3],['999999999999','stale',null],['NaN','verified_snapshot',null]])('uses exact USD cap %s and status %s',(value,status,expected)=>{
 expect(earningsImportance({...base,market_cap_usd:value,market_cap_status:status as EarningsItem['market_cap_status']})).toBe(expected);
});
it('deduplicates, sorts confirmed times and places unknown times last',()=>{
 const unknown={...base,event_id:'unknown',release:{...time,precision:'date_only' as const}};
 const groups=unifiedGroups([macro,macro],[base,base,unknown],'2026-11-01','2026-11-05');
 expect(groups).toHaveLength(1);expect(groups[0].rows.map(r=>r.key)).toEqual(['macro:macro','earnings:amd','earnings:unknown']);
});
function arrange(){
 vi.mocked(fetchCalendarAgenda).mockImplementation(async(start_date,end_date)=>({start_date,end_date,events:[macro],timezone:'Europe/Warsaw',policy:{},refresh:{status:'complete',next_check_at:'2099-01-01T00:00:00Z',results:[]}} as unknown as Awaited<ReturnType<typeof fetchCalendarAgenda>>));
 vi.mocked(fetchEarnings).mockResolvedValue(response([base]));
}
it.each(['en','pl'] as const)('renders one shared table and navigates to unchanged Earnings in %s',async language=>{
 setLanguage(language);vi.setSystemTime(new Date('2026-11-03T12:00:00Z'));arrange();
 render(<CalendarPage/>);
 const name=language==='pl'?'Wyniki AMD · Q3 2026':'Earnings AMD · Q3 2026';
 await screen.findByRole('button',{name});expect(screen.getAllByRole('table')).toHaveLength(1);
 const row=screen.getByRole('button',{name}).closest('tr')!;
 expect(within(row).getByText('22:00+')).toBeInTheDocument();expect(within(row).getAllByText('—')).toHaveLength(6);
 expect(within(screen.getByRole('table')).getAllByRole('columnheader').map(e=>e.textContent)).toEqual(language==='pl'?['Godzina','Wydarzenie','Ważność','Aktualny','vs poprzedni','Poprzednio']:['Time','Event','Importance','Actual','vs previous','Previous']);
 expect(row.children).toHaveLength(6);
 fireEvent.click(screen.getByRole('radio',{name:language==='pl'?'Dane':'Data'}));
 expect(screen.getAllByRole('columnheader')).toHaveLength(8);
 expect(screen.getByRole('columnheader',{name:language==='pl'?'Prognoza':'Forecast'})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('radio',{name:language==='pl'?'Wszystko':'All'}));
 await screen.findByRole('button',{name});
 expect(within(row).getByRole('img',{name:/200/})).toHaveTextContent('★★★');
 expect(screen.getAllByRole('heading',{level:2})).toHaveLength(1);
 fireEvent.click(screen.getByRole('button',{name:'Synthetic CPI'}));expect(document.querySelector('.agenda-detail td')).toHaveAttribute('colspan','6');
 fireEvent.click(screen.getByRole('button',{name:'Synthetic CPI'}));
 fireEvent.click(screen.getByRole('button',{name}));expect(screen.getByRole('radio',{name:language==='pl'?'Wyniki':'Earnings'})).toBeChecked();
 expect(await screen.findByRole('columnheader',{name:'Market Cap'})).toBeInTheDocument();expect(fetchEarnings).toHaveBeenCalledTimes(2);
});
it('keeps macro usable when Earnings fails',async()=>{
 vi.setSystemTime(new Date('2026-11-03T12:00:00Z'));arrange();vi.mocked(fetchEarnings).mockRejectedValue(Error('offline'));
 render(<CalendarPage/>);expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load earnings');
 expect(screen.getByRole('button',{name:'Synthetic CPI'})).toBeInTheDocument();
});
it('keeps Earnings usable when macro fails',async()=>{
 vi.setSystemTime(new Date('2026-11-03T12:00:00Z'));arrange();vi.mocked(fetchCalendarAgenda).mockRejectedValue(Error('offline'));
 render(<CalendarPage/>);expect(await screen.findByRole('button',{name:'Earnings AMD · Q3 2026'})).toBeInTheDocument();
 expect(screen.getByRole('alert')).toHaveTextContent('Unable to load calendar');
});
it('ignores a late response after the selected range changes',async()=>{
 arrange();let resolve!:(r:CalendarItemsResponse)=>void,settled=false;
 const old=new Promise<CalendarItemsResponse>(r=>{resolve=r;});old.then(()=>{settled=true;});
 vi.mocked(fetchEarnings).mockReturnValueOnce(old).mockResolvedValue(response([]));
 render(<CalendarPage/>);await waitFor(()=>expect(fetchEarnings).toHaveBeenCalledTimes(1));
 const signal=vi.mocked(fetchEarnings).mock.calls[0][3];
 fireEvent.click(screen.getByRole('button',{name:'Next week'}));await waitFor(()=>expect(fetchEarnings).toHaveBeenCalledTimes(2));
 expect(signal.aborted).toBe(true);
 const newDay=vi.mocked(fetchEarnings).mock.calls[1][0];
 // Even an old response whose row falls inside the NEW range must be ignored.
 act(()=>resolve(response([{...base,release:{...time,precision:'date_only',source_local_date:newDay,poland_date:newDay}}])));
 await waitFor(()=>expect(settled).toBe(true));
 expect(screen.queryByRole('button',{name:'Earnings AMD · Q3 2026'})).not.toBeInTheDocument();
});
