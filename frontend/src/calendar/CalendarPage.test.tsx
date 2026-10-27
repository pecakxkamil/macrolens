import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,beforeEach,expect,test,vi} from 'vitest';
import App from '../App';
import {CalendarPage} from './CalendarPage';
import {setLanguage,tText} from '../i18n/language';
import type {CalendarEvent,CalendarMeasure,CalendarResponse} from '../api/macrolens';
import {formatPolandTime,weekRange,todayIso} from './calendarDates';
import {compactMeasureName,compactPeriod,compactMeasureValue} from './calendarPresentation';
import {countdown,filterEvents,groupAgenda,nextInstant,presetRange,rangeError,resultPending} from './calendarAgenda';
const NOW='2026-10-26T10:00:00Z';
const cpi={series_id:'CPIAUCSL',name:'Consumer Price Index',short_name:'CPI',frequency:'monthly',unit:'index',category:'inflation'};
function measure(label='CPI MoM'):CalendarMeasure{return {series_id:'CPIAUCSL',label,feature_name:'mom',frequency:'monthly',unit:'percent',reference_period:'2026-09-01',previous_period:'2026-08-01',previous_kind:'previous_period',actual:.3,previous:.2,forecast:null,consensus_status:'not_integrated',data_version:'stored_date_vintage',revision_confirmed:false,binding_method:'alfred_release_date',vintage_date:'2026-10-26',realtime_end:'9999-12-31',result_status:'available',mapping_status:'confirmed',source_url:'https://fred.stlouisfed.org/series/CPIAUCSL'};}
function events():CalendarEvent[]{return [
 {release_id:10,release_name:'Consumer Price Index',release_date:'2026-10-26',release_time:'08:30:00',source_timezone:'America/New_York',release_datetime_utc:'2026-10-26T12:30:00Z',importance:'high',source_link:'https://www.bls.gov/cpi/',date_precision:'date',series:[cpi],measures:[measure(),{...measure('Core CPI MoM'),series_id:'CPILFESL'}]},
 {release_id:50,release_name:'Employment Situation',release_date:'2026-10-26',release_time:'08:30:00',source_timezone:'America/New_York',release_datetime_utc:'2026-10-26T12:30:00Z',importance:'high',source_link:null,date_precision:'date',series:[{...cpi,series_id:'UNRATE',category:'labor'}],measures:[{...measure('Unemployment rate'),series_id:'UNRATE',feature_name:'raw'}]},
 {release_id:180,release_name:'Unemployment Insurance Weekly Claims Report',release_date:'2026-10-29',release_time:null,source_timezone:null,release_datetime_utc:null,importance:'high',source_link:null,date_precision:'date',series:[{...cpi,series_id:'ICSA',category:'labor'}],measures:[{...measure('Initial jobless claims'),series_id:'ICSA',feature_name:'raw',unit:'claims',actual:null,previous:null,reference_period:null,previous_period:null,mapping_status:'reference_period_unconfirmed',data_version:null}]},
 {release_id:18,release_name:'H.15 Selected Interest Rates',release_date:'2026-10-26',release_time:null,source_timezone:null,release_datetime_utc:null,importance:'low',source_link:null,date_precision:'date',series:[{...cpi,series_id:'DFF',name:'Effective Fed Funds Rate',short_name:'Effective Fed Funds Rate',category:'financial_conditions'}]},
 {release_id:999,release_name:'Unclassified release',release_date:'2026-10-26',release_time:null,source_timezone:null,release_datetime_utc:null,importance:undefined as unknown as CalendarEvent['importance'],source_link:null,date_precision:'date',series:[{...cpi,series_id:'UNKNOWN',name:'Unclassified indicator',short_name:'Unclassified indicator'}]},
 ];}
function mockApi(mode='ready',automatic=false){
 const fetch=vi.fn(async(input:string|URL,init?:RequestInit)=>{const url=new URL(String(input));if(url.pathname.endsWith('/brief/refresh'))return {ok:true,json:async()=>({status:'complete',publication_id:'saved',next_check_at:'2026-10-26T10:15:00Z',results:[]})};
 if(url.pathname==='/api/v1/calendar'){
  if(mode==='loading')return new Promise(()=>{});if(mode==='error')return {ok:false};
  const start=url.searchParams.get('start_date')!,end=url.searchParams.get('end_date')!;
  return {ok:true,json:async()=>({start_date:start,end_date:end,events:mode==='empty'?[]:events().filter(e=>e.release_date>=start&&e.release_date<=end),data_revision:'saved',automatic_refresh_supported:automatic,check:{status:'complete',checked_at:'2026-10-26T09:00:00Z',start_date:start,end_date:end,sources:[],required_resources:[]}})};
 }return new Promise(()=>{});});vi.stubGlobal('fetch',fetch);return fetch;
}
beforeEach(()=>{vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date(NOW));});
afterEach(()=>{cleanup();vi.useRealTimers();vi.restoreAllMocks();vi.unstubAllGlobals();setLanguage('en');location.hash='';});


test('main Calendar and old route keep the Monday-Sunday range with one shared column header',async()=>{
 mockApi();location.hash='#/overview/calendar';render(<App/>);await screen.findByRole('button',{name:'CPI MoM (Sep)'});
 expect(location.hash).toBe('#/calendar');expect(screen.getByRole('link',{name:'Calendar'})).toHaveAttribute('aria-current','page');
 expect(screen.getByRole('button',{name:'This week'})).toHaveAttribute('aria-pressed','true');expect(screen.getAllByRole('columnheader',{name:'Event'})).toHaveLength(1);
 expect(screen.getByRole('rowgroup',{name:'Monday, October 26, 2026'})).toBeInTheDocument();expect(screen.getByRole('rowgroup',{name:'Thursday, October 29, 2026'})).toBeInTheDocument();
});

test('default importance, quick filter, categories and clear remain local',async()=>{
 const fetch=mockApi();render(<CalendarPage/>);await screen.findByRole('button',{name:'CPI MoM (Sep)'});
 expect(screen.queryByRole('button',{name:'Effective Fed Funds Rate'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Unclassified indicator'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByLabelText(/Only/));expect(screen.queryByRole('button',{name:'Initial jobless claims'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Clear filters'}));expect(screen.getByRole('button',{name:'Effective Fed Funds Rate'})).toBeInTheDocument();expect(screen.getByRole('button',{name:'Unclassified indicator'})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Filters'}));fireEvent.click(screen.getByLabelText('Housing'));expect(screen.getByText('No events match the selected filters.')).toBeInTheDocument();expect(fetch).toHaveBeenCalledTimes(1);
});

test('each measure has one ordinary row with its own unchanged time, importance and neutral values',async()=>{
 mockApi();render(<CalendarPage/>);const row=(await screen.findByRole('button',{name:'CPI MoM (Sep)'})).closest('tr')!;
 expect(row).toHaveTextContent('13:30');expect(row).not.toHaveTextContent('PL');expect(within(row).getByRole('img',{name:'Importance 3 of 3'})).toBeInTheDocument();
 expect(row).toHaveTextContent('0.30%');expect(row).toHaveTextContent('0.20%');expect(screen.getByRole('button',{name:'Core CPI MoM (Sep)'}).closest('tr')).toHaveTextContent('13:30');
 expect(screen.queryByRole('button',{name:/Consumer Price Index/})).not.toBeInTheDocument();expect(screen.queryByText('Stored date-level vintage')).not.toBeInTheDocument();
 expect(document.querySelectorAll('.agenda-entry')).toHaveLength(4);expect(row.querySelectorAll('.agenda-number')).toHaveLength(3);expect(row.querySelector('.overview-interpretation')).toBeNull();
});

test('details preserve the publication relationship, full units, provenance, definition and exact Explore link',async()=>{
 const fetch=mockApi();render(<CalendarPage/>);const button=await screen.findByRole('button',{name:'CPI MoM (Sep)'});fireEvent.click(button);
 expect(button).toHaveAttribute('aria-expanded','true');const detail=document.getElementById(button.getAttribute('aria-controls')!)!;
 expect(detail).toHaveTextContent('Consumer Price Index');expect(detail).toHaveTextContent('ALFRED establishes date-level availability');expect(detail).toHaveTextContent('2026-10-26');expect(detail).toHaveTextContent('mom');
 expect(within(detail).getByRole('link',{name:'View indicator'})).toHaveAttribute('href','#/explore/indicators/CPIAUCSL');expect(fetch).toHaveBeenCalledTimes(1);
 fireEvent.keyDown(button,{key:'Escape'});expect(button).toHaveAttribute('aria-expanded','false');expect(button).toHaveFocus();
});

test('row clicks and a single selected measure open details without duplicate publication panels',async()=>{
 mockApi();render(<CalendarPage/>);const first=await screen.findByRole('button',{name:'CPI MoM (Sep)'});fireEvent.click(first.closest('tr')!);
 expect(first).toHaveAttribute('aria-expanded','true');const second=screen.getByRole('button',{name:'Core CPI MoM (Sep)'});fireEvent.click(second);
 expect(first).toHaveAttribute('aria-expanded','false');expect(second).toHaveAttribute('aria-expanded','true');expect(document.querySelectorAll('.agenda-detail')).toHaveLength(1);
});

test('missing values, unknown periods, unknown times and consensus stay as dashes with explanations in details',async()=>{
 mockApi();render(<CalendarPage/>);const button=await screen.findByRole('button',{name:'Initial jobless claims'}),row=button.closest('tr')!;
 expect(row).not.toHaveTextContent('Reference period');expect(row).not.toHaveTextContent('Awaiting');expect(row.querySelectorAll('.agenda-number')).toHaveLength(3);
 expect([...row.querySelectorAll('.agenda-number')].every(x=>x.textContent==='—')).toBe(true);expect(row.querySelector('.agenda-time')).toHaveTextContent('—');expect(row).not.toHaveTextContent('00:00');
 fireEvent.click(button);const detail=document.getElementById(button.getAttribute('aria-controls')!)!;
 expect(detail).toHaveTextContent('Reference period unconfirmed');expect(detail).toHaveTextContent('publication date does not confirm');expect(detail).toHaveTextContent('No integrated consensus source');expect(detail).toHaveTextContent('no midnight time is inferred');
});

test('only the closest time group has one compact countdown; simultaneous rows retain the same time',async()=>{
 mockApi();render(<CalendarPage/>);const first=await screen.findByRole('button',{name:'CPI MoM (Sep)'}),second=screen.getByRole('button',{name:'Unemployment rate (Sep)'});
 expect(first.closest('tr')).not.toHaveClass('is-next');expect(second.closest('tr')).not.toHaveClass('is-next');expect(screen.getAllByText('In 2 hours 30 minutes')).toHaveLength(1);
 expect(second.closest('tr')).toHaveTextContent('13:30');expect(screen.getByRole('button',{name:'Initial jobless claims'}).closest('tr')).not.toHaveClass('is-next');
});

test.each(['en','pl'] as const)('revised permits explain a published result pending in FRED and the previous-month basis in %s',async language=>{
 setLanguage(language);
 const source='https://www.census.gov/construction/bps/permitsbyusreg_cust.xls';
 const permit:CalendarMeasure={...measure('Building permits'),series_id:'PERMIT',feature_name:'raw',unit:'thousand homes/year (SAAR)',actual:null,previous:1403,data_version:null,result_status:'awaiting_data',source_url:'https://fred.stlouisfed.org/series/PERMIT',period_provenance:{source_url:'https://www.census.gov/construction/soc/schedule.html',reference_period:'2026-09-01',binding_method:'official_schedule',estimate_stage:'revised_permits'},publication_provenance:{source_url:source,release_date:'2026-10-27',reference_period:'2026-09-01',estimate_stage:'revised_permits'},missing_reason:{actual:'revised_permits_provider_pending',previous:null}};
 const event:CalendarEvent={...events()[0],release_id:27,release_name:'New Residential Construction',release_date:'2026-10-27',release_datetime_utc:'2026-10-27T12:00:00Z',measures:[permit]};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-26',end_date:'2026-11-01',events:[event]})})));
 render(<CalendarPage/>);const button=await screen.findByRole('button',{name:language==='en'?'Building permits (Sep)':'Pozwolenia na budowę (wrz)'});
 expect(button.closest('tr')!.querySelector('.agenda-actual')).toHaveTextContent('—');
 fireEvent.click(button);const detail=document.getElementById(button.getAttribute('aria-controls')!)!;
 expect(detail).toHaveTextContent(tText('Census has published the revised permits, but a matching result has not yet been confirmed in FRED.'));
 expect(detail).toHaveTextContent(tText('This is a revision of the same month. Previous remains the preceding month, not the earlier estimate of this month.'));
 expect(detail.textContent).not.toContain('..');expect(within(detail).getByRole('link',{name:tText('Confirmed publisher release')})).toHaveAttribute('href',source);
});

test('custom date validation and presets retain saved-data requests',async()=>{
 const fetch=mockApi();render(<CalendarPage/>);await screen.findByRole('button',{name:'CPI MoM (Sep)'});fireEvent.click(screen.getByRole('button',{name:'Date range'}));
 fireEvent.change(screen.getByLabelText('Start date'),{target:{value:'2026-11-01'}});fireEvent.change(screen.getByLabelText('End date'),{target:{value:'2026-10-01'}});fireEvent.click(screen.getByRole('button',{name:'Apply range'}));expect(screen.getByRole('alert')).toHaveTextContent('The start date must not follow');expect(fetch).toHaveBeenCalledTimes(1);
 fireEvent.change(screen.getByLabelText('Start date'),{target:{value:'2025-01-01'}});fireEvent.click(screen.getByRole('button',{name:'Apply range'}));expect(screen.getByRole('alert')).toHaveTextContent('366 days');
 fireEvent.click(screen.getByRole('button',{name:'Tomorrow'}));await waitFor(()=>expect(fetch.mock.calls.some(([url])=>String(url).includes('start_date=2026-10-27'))).toBe(true));
});

test('empty stored data, loading and errors remain distinct',async()=>{
 mockApi('empty');render(<CalendarPage/>);expect(await screen.findByText('No stored events in this date range.')).toBeInTheDocument();cleanup();
 mockApi('loading');render(<CalendarPage/>);expect(screen.getByText('Loading calendar...')).toBeInTheDocument();cleanup();mockApi('error');render(<CalendarPage/>);expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load calendar.');expect(screen.getByRole('button',{name:'Retry'})).toBeInTheDocument();
});

test.each(['en','pl'] as const)('compact names, periods and values render in %s without refetching',async language=>{
 setLanguage(language);const fetch=mockApi();render(<CalendarPage/>);const button=await screen.findByRole('button',{name:language==='pl'?'Inflacja CPI m/m (wrz)':'CPI MoM (Sep)'});
 expect(button.closest('tr')).toHaveTextContent(language==='pl'?'0,30%':'0.30%');expect(screen.getByRole('heading',{name:language==='pl'?'Kalendarz':'Calendar'})).toBeInTheDocument();expect(fetch).toHaveBeenCalledTimes(1);
});

test('entry and focus keep the existing shared refresh and cooldown',async()=>{
 const fetch=mockApi('ready',true);render(<CalendarPage/>);await screen.findByRole('button',{name:'CPI MoM (Sep)'});await waitFor(()=>expect(fetch.mock.calls.some(([url])=>String(url).includes('calendar_start_date=2026-10-26'))).toBe(true));
 const before=fetch.mock.calls.length;fireEvent(window,new Event('focus'));await new Promise(r=>setTimeout(r,30));expect(fetch).toHaveBeenCalledTimes(before);
});

test('Warsaw dates, calendar weeks and DST keep their existing behavior',()=>{
 expect(todayIso(new Date('2026-12-31T23:30:00Z'))).toBe('2027-01-01');expect(weekRange('2027-01-01')).toEqual({startDate:'2026-12-28',endDate:'2027-01-03'});
 expect(presetRange('nextWeek',new Date('2026-12-31T23:30:00Z'))).toEqual({startDate:'2027-01-04',endDate:'2027-01-10'});
 expect(formatPolandTime('2026-03-13T12:30:00Z')).toBe('13:30 PL');expect(formatPolandTime('2026-09-30T12:30:00Z')).toBe('14:30 PL');expect(formatPolandTime('2026-10-29T12:30:00Z')).toBe('13:30 PL');
 expect(rangeError('2024-01-01','2024-12-31')).toBeNull();expect(rangeError('2024-02-30','2024-03-01')).not.toBeNull();
});

test('chronological ordering, deduplication, editorial stars and elapsed-time logic are unchanged',()=>{
 const source=events();expect(groupAgenda([source[3],source[1],source[0],{...source[0]}])[0].events.map(e=>e.release_id)).toEqual([10,50,18]);
 expect(filterEvents(source,new Set([3]),false,new Set())).toHaveLength(2);expect(filterEvents(source,new Set(),true,new Set())).toHaveLength(1);
 expect(resultPending(source[0],{...measure(),actual:null},new Date('2026-10-26T13:00:00Z'))).toBe(true);expect(countdown(nextInstant([source[0]],new Date(NOW)),new Date('2026-10-26T12:30:00Z'))).toBeNull();
});

test('GDP previous estimate, confirmed revision and current vintage stay explicit in details; nonnumeric events use one row',async()=>{
 const gdp={...events()[0],release_id:53,release_name:'Gross Domestic Product',measures:[{...measure('Real GDP QoQ, annualized'),series_id:'GDPC1',feature_name:'qoq_annualized',frequency:'quarterly',reference_period:'2026-04-01',previous_period:'2026-04-01',previous_kind:'previous_estimate' as const,actual:2.22,previous:1.48,revision_confirmed:true,data_version:'current_vintage' as const,previous_data_version:'stored_date_vintage' as const}]};
 const conference={...events()[0],release_id:null,event_id:'conference',release_name:'Policy conference',series:[],measures:[],expects_numeric_result:false};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-26',end_date:'2026-11-01',events:[gdp,conference]})})));render(<CalendarPage/>);
 const button=await screen.findByRole('button',{name:'Real GDP QoQ, annualized (Q2)'}),row=button.closest('tr')!;expect(row).toHaveTextContent('2.22%');expect(row).toHaveTextContent('1.48%');expect(row).not.toHaveTextContent('Current-vintage');fireEvent.click(button);
 const detail=document.getElementById(button.getAttribute('aria-controls')!)!;expect(detail).toHaveTextContent('Confirmed revision');expect(detail).toHaveTextContent('Current-vintage value');expect(detail).toHaveTextContent('Previous compares the earlier stored estimate of the same quarter');expect(detail).toHaveTextContent('Stored date-level vintage');
 const event=screen.getByRole('button',{name:'Policy conference'});expect(event.closest('tr')).not.toHaveTextContent('Awaiting');expect(document.querySelectorAll('.agenda-entry')).toHaveLength(2);
});

test('compact labels and units respect the existing transformation and never invent periods',()=>{
 expect(compactMeasureName({...measure(),series_id:'PAYEMS',feature_name:'monthly_change'})).toBe('Nonfarm payrolls change (NFP)');
 expect(compactMeasureName({...measure(),series_id:'DGORDER'})).toBe('Durable goods orders MoM');expect(compactMeasureName({...measure(),series_id:'DGORDER',feature_name:'raw'})).toBe('Durable goods orders');expect(compactMeasureName({...measure(),feature_name:'yoy'})).toBe('CPI YoY');
 expect(compactPeriod({...measure(),reference_period:null},'2026-10-26')).toBe('');expect(compactPeriod({...measure(),reference_period:'2025-09-01'},'2026-10-26')).toBe('Sep 2025');
 expect(compactMeasureValue(null,'percent')).toBe('—');expect(compactMeasureValue(1275,'thousand homes/year (SAAR)')).toBe('1,275\u00a0k');expect(compactMeasureValue(7079,'thousand openings')).toBe('7.08\u00a0m');
 setLanguage('pl');expect(compactMeasureName({...measure(),series_id:'DGORDER'})).toBe('Zamówienia na dobra trwałe m/m');expect(compactMeasureValue(-.5,'index points')).toBe('-0,5\u00a0pkt');
});

test('relevant refresh failures remain visible while unrelated partial failures do not downgrade this range',async()=>{
 const response={start_date:'2026-10-26',end_date:'2026-11-01',events:events(),automatic_refresh_supported:false,check:{status:'complete',checked_at:NOW,sources:[],required_resources:['fred:calendar']},refresh:{status:'partial',results:[{resource:'ism:manufacturing',status:'error',error_code:'discovery_failed'}]}};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>response})));render(<CalendarPage/>);expect(await screen.findByText('Sources checked:')).toBeInTheDocument();cleanup();
 response.refresh.results=[{resource:'fred:calendar',status:'error',error_code:'fetch_failed'}];render(<CalendarPage/>);expect(await screen.findByText('Unable to check some sources — stored data shown.')).toBeInTheDocument();expect(screen.queryByText('Check details')).not.toBeInTheDocument();expect(document.querySelector('.calendar-check details')).toBeNull();
});


test.each(['en','pl'] as const)('comparison columns and accessible explanations work in %s without opening event details',async language=>{
 setLanguage(language);
 const nfp={...measure(),series_id:'PAYEMS',feature_name:'monthly_change',unit:'thousand jobs',actual:157,previous:182,forecast:120,consensus_status:'available' as const};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-26',end_date:'2026-11-01',events:[{...events()[1],measures:[nfp]}],automatic_refresh_supported:false})})));
 render(<CalendarPage/>);await screen.findByRole('button',{name:language==='en'?/NFP.*Sep/:/NFP.*wrz/});
 expect([...document.querySelectorAll('thead th')].map(h=>h.textContent)).toEqual(['Time','Event','Importance','Forecast','vs forecast','Actual','vs previous','Previous'].map(tText));
 const row=document.querySelector('.agenda-entry')!;expect(row.children).toHaveLength(8);
 expect(row.children[3]).toHaveTextContent('120');expect(row.children[4]).toHaveTextContent('+37');expect(row.children[5]).toHaveTextContent('157');expect(row.children[6]).toHaveTextContent('25');expect(row.children[7]).toHaveTextContent('182');
 expect(row.querySelector('.agenda-comparison--favorable')).toBeInTheDocument();expect(row.querySelector('.agenda-comparison--unfavorable')).toBeInTheDocument();
 const trigger=within(row.children[4] as HTMLElement).getByRole('button');fireEvent.focus(trigger);expect(screen.getByRole('tooltip')).toHaveTextContent(language==='en'?'consensus':'konsensus');
 fireEvent.keyDown(trigger,{key:'Escape'});expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
 fireEvent.mouseEnter(trigger.parentElement!);expect(screen.getByRole('tooltip')).toBeInTheDocument();fireEvent.mouseLeave(trigger.parentElement!);expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
 fireEvent.click(trigger);expect(screen.getByRole('tooltip')).toBeInTheDocument();expect(document.querySelector('.agenda-detail')).toBeNull();fireEvent.pointerDown(document.body);expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
});


test('future FOMC displays the prior range and effective date while awaiting a statement',async()=>{
 const policy:CalendarMeasure={...measure(),series_id:'DFEDTARL/DFEDTARU',feature_name:'target_range',frequency:'decision',reference_period:'2026-10-28',previous_period:'2026-09-16',previous_kind:'previous_decision',actual:null,previous:3.75,actual_range:null,previous_range:[3.75,4],data_version:null,previous_data_version:'official_release',previous_effective_date:'2026-09-17',missing_reason:{actual:'official_decision_not_available',previous:null},previous_provenance:{source_url:'https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm',version:'official_release'}};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-26',end_date:'2026-11-01',events:[{...events()[0],release_id:null,event_type:'fomc_decision',release_date:'2026-10-28',release_name:'FOMC policy decision',measures:[policy]}],automatic_refresh_supported:false})})));
 render(<CalendarPage/>);const button=await screen.findByRole('button',{name:'Fed decision — interest rates'}),row=button.closest('tr')!;
 expect(row.querySelector('.agenda-actual')).toHaveTextContent('\u2014');expect(row.children[7]).toHaveTextContent('3.75\u20134.00%');expect(row.querySelector('.agenda-comparison')).toBeNull();
 fireEvent.click(button);const detail=document.getElementById(button.getAttribute('aria-controls')!)!;
 expect(detail).toHaveTextContent('No official decision statement is stored');expect(detail).toHaveTextContent('Previous decision effective date:');expect(detail).toHaveTextContent('Sep 17, 2026');expect(detail).toHaveTextContent('Previous is the target range announced before this meeting');
});

test('a newly confirmed publication reloads actual and its difference after the shared publication revision changes',async()=>{
 let reads=0,finish:(()=>void)|undefined;
 const response=(published:boolean)=>({start_date:'2026-10-26',end_date:'2026-11-01',data_revision:published?'after':'before',automatic_refresh_supported:true,events:[{...events()[0],measures:[{...measure(),actual:published ? .3 : null,result_status:published?'available':'scheduled'}]}]});
 const fetch=vi.fn(async(input:string|URL)=>{
  if(new URL(String(input)).pathname.endsWith('/brief/refresh'))return new Promise<{ok:boolean;json:()=>Promise<unknown>}>(resolve=>{finish=()=>resolve({ok:true,json:async()=>({status:'complete',publication_id:'after',next_check_at:'2026-10-26T10:15:00Z',results:[]})});});
  return {ok:true,json:async()=>response(++reads>1)};
 });
 vi.stubGlobal('fetch',fetch);render(<CalendarPage/>);
 const row=(await screen.findByRole('button',{name:'CPI MoM (Sep)'})).closest('tr')!;
 expect(row.querySelector('.agenda-actual')).toHaveTextContent('—');expect(row.querySelector('.agenda-comparison')).toBeNull();
 await waitFor(()=>expect(finish).toBeTypeOf('function'));finish!();
 await waitFor(()=>expect(row.querySelector('.agenda-actual')).toHaveTextContent('0.30%'));
 expect(row.children[6]).toHaveTextContent('+0.1');expect(row.children[7]).toHaveTextContent('0.20%');expect(reads).toBe(2);
});
