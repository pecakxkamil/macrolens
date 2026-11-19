import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {annualCpiReading,AnnualCpiReading} from './AnnualCpiReading';
import type {CalendarResponse} from '../api/macrolens';
import {setLanguage} from '../i18n/language';

const now=new Date('2026-11-17T10:00:00Z');
function fixture(patch:Record<string,unknown>={},eventPatch:Record<string,unknown>={}){
 return {events:[{release_date:'2026-11-10',release_datetime_utc:'2026-11-10T13:30:00Z',...eventPatch,measures:[{
  series_id:'CPIAUCSL',feature_name:'yoy',mapping_status:'confirmed',selected_source:'bls:cpi',seasonal_adjustment:'NSA',cpi_contract_id:'bls:cpi:CUUR0000SA0:yoy:NSA',
  cpi_rate_kind:'derived_index_rate',previous_kind:'previous_period',reference_period:'2026-10-01',previous_period:'2026-09-01',actual:null,previous:3.7,result_status:'publisher_unavailable',missing_reason:{actual:'publisher_base_unavailable'},cpi_missing_base_period:'2025-10-01',cpi_missing_proof:{missing_confirmed:true},comparison_status:'same_cpi_capture',source_url:'https://api.bls.gov/publicAPI/v2/timeseries/data/',...patch
 }]}]} as unknown as CalendarResponse;
}
afterEach(()=>{cleanup();vi.unstubAllGlobals();setLanguage('en');});

it('keeps September dated when October is terminally unavailable, using the API value',()=>{
 const result=annualCpiReading(fixture(),now);expect(result).toMatchObject({value:3.7,period:'2026-09-01',missing:true});
 expect(annualCpiReading(fixture({previous:2.9}),now)?.value).toBe(2.9);
});
it('uses a newly available current period without a stale fallback',()=>{
 expect(annualCpiReading(fixture({actual:4.1,result_status:'available'}),now)).toMatchObject({value:4.1,period:'2026-10-01',missing:false});
});
it.each([
 {seasonal_adjustment:'SA'},{selected_source:'fred_fallback'},{mapping_status:'unconfirmed'},
 {cpi_contract_id:'bls:cpi:CUSR0000SA0:yoy:SA'},{feature_name:'mom'},
 {cpi_missing_proof:{missing_confirmed:false}},{cpi_missing_base_period:'2025-09-01'},{previous:NaN},{previous_period:'2026-10-01'},
 {missing_reason:{actual:'observation_missing'}},{cpi_missing_base_period:'2025-13-01'}
])('rejects unverified or incompatible annual data %j',patch=>{expect(annualCpiReading(fixture(patch),now)).toBeNull();});
it('excludes future and not-yet-released same-day publications',()=>{
 expect(annualCpiReading(fixture({}, {release_date:'2026-11-18',release_datetime_utc:'2026-11-18T13:30:00Z'}),now)).toBeNull();
 expect(annualCpiReading(fixture({}, {release_date:'2026-11-17',release_datetime_utc:'2026-11-17T13:30:00Z'}),now)).toBeNull();
});
it.each(['en','pl'] as const)('shows annual value, observation month and missing-base explanation in %s',async language=>{
 setLanguage(language);const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>fixture()});vi.stubGlobal('fetch',fetch);
 render(<table><tbody><AnnualCpiReading revision="test" now={now}/></tbody></table>);
 expect(await screen.findByText(language==='pl'?'3,7':'3.7')).toBeInTheDocument();
 expect(document.querySelector('time')).toHaveAttribute('dateTime','2026-09-01');
 fireEvent.click(screen.getByRole('button',{name:language==='pl'?'Inflacja CPI r/r':'CPI YoY'}));
 const explanation=screen.getByRole('button',{name:language==='pl'?'Inflacja CPI r/r':'CPI YoY'}).parentElement!;
 expect(explanation.querySelector('[role="tooltip"]')).toHaveTextContent(language==='pl'?'brak bazy':'missing comparison base');
 expect(explanation.querySelector('[role="tooltip"]')).toHaveTextContent('2025');
 expect(screen.getByRole('link',{name:'BLS'})).toHaveAttribute('href','https://api.bls.gov/publicAPI/v2/timeseries/data/');
 expect(fetch).toHaveBeenCalledTimes(1);const url=new URL(String(fetch.mock.calls[0][0]));expect(url.pathname).toBe('/api/v1/calendar');expect(url.searchParams.get('include_readings')).toBe('true');expect(url.searchParams.get('end_date')).toBe('2026-11-17');
});
it('shows an unavailable state on API failure without inventing a number',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false}));render(<table><tbody><AnnualCpiReading revision="test" now={now}/></tbody></table>);
 await waitFor(()=>expect(screen.getByRole('status')).toHaveTextContent('unavailable'));expect(screen.queryByText('3.7%')).toBeNull();
});
it('renders the annual reading as a standard three-column row with the preceding month from the same capture',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>fixture({cpi_history:{'2026-07-01':'3.4','2026-08-01':'3.4','2026-09-01':'3.7'}})}));
 render(<table><tbody><AnnualCpiReading revision="test" now={now}/></tbody></table>);
 const row=screen.getByRole('row',{name:'CPI YoY'});await waitFor(()=>expect(row.querySelector('.overview-value--latest .overview-number')).toHaveTextContent('3.7'));
 expect(row).toHaveClass('overview-reading-row');expect(within(row).getAllByRole('cell')).toHaveLength(2);
 const cells=within(row).getAllByRole('cell');expect(cells[0]).toHaveTextContent('3.7%');expect(cells[1]).toHaveTextContent('3.4%');
 expect(cells[1].querySelector('time')).toHaveAttribute('dateTime','2026-08-01');expect(screen.queryByRole('region',{name:'Annual CPI inflation'})).toBeNull();
 expect(row.querySelector('.overview-reading-actions > .overview-explanation .info-tooltip__trigger')).toHaveTextContent('i');
 expect(row.querySelector('.overview-interpretation--favorable')).toHaveTextContent('+');
});
it.each([{previous:'3.4',arrow:'↑',marker:true},{previous:'4.0',arrow:'↓',marker:true},{previous:'3.7',arrow:'—',marker:false}])('keeps numerical direction separate from the contextual economic marker: $previous',async({previous,arrow,marker})=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>fixture({cpi_history:{'2026-08-01':previous}})}));
 render(<table><tbody><AnnualCpiReading revision="test" now={now}/></tbody></table>);
 const row=screen.getByRole('row',{name:'CPI YoY'});await waitFor(()=>expect(row.querySelector('.overview-value--latest .overview-number')).toHaveTextContent('3.7'));
 expect(row.querySelector('.overview-change')).toHaveTextContent(arrow);
 expect(!!row.querySelector('.overview-interpretation')).toBe(marker);
 if(marker)expect(row.querySelector('.overview-interpretation')).toHaveTextContent(arrow==='↑'?'+':'−');
 if(marker){fireEvent.click(within(row).getByRole('button',{name:/Potential (support for|pressure on) USD/}));expect(row.querySelector('.overview-interpretation [role="tooltip"]')).toHaveTextContent('Fed');}
});
it('does not borrow a non-adjacent history month for Previous',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>fixture({cpi_history:{'2026-07-01':'3.4'}})}));
 render(<table><tbody><AnnualCpiReading revision="test" now={now}/></tbody></table>);
 await screen.findByText('3.7');expect(within(screen.getByRole('row',{name:'CPI YoY'})).getAllByRole('cell')[1]).toHaveTextContent('—');
 expect(document.querySelector('.overview-interpretation')).toBeNull();
});
