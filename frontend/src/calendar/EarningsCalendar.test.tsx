import {afterEach,describe,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {EarningsCalendar} from './EarningsCalendar';
import {earningsDay,earningsSummary,earningsTime} from './earningsPresentation';
import type {EarningsItem,EarningsTime} from './earningsTypes';
import {setLanguage} from '../i18n/language';

const unknown:EarningsTime={component:'release',date_status:'unknown',precision:'unknown',source_local_date:null,source_local_time:null,source_timezone:null,timezone_label_raw:null,scheduled_at_utc:null,expected_time_utc:null,poland_date:null,session_boundary_utc:null,session_boundary_source:null,source_url:null,verified_on:null,facts:null,verification_method:null,sequence:1};
const release:EarningsTime={...unknown,date_status:'confirmed',precision:'approximate',source_local_date:'2026-11-17',source_local_time:'13:20',source_timezone:'America/Los_Angeles',timezone_label_raw:'PT',expected_time_utc:'2026-11-17T21:20:00Z',poland_date:'2026-11-17',source_url:'https://investor.nvidia.com/news/official',verified_on:'2026-11-02',verification_method:'manually_verified_official_source'};
const call:EarningsTime={...release,component:'call',precision:'exact',source_local_time:'14:00',scheduled_at_utc:'2026-11-17T22:00:00Z',expected_time_utc:null};
const event:EarningsItem={domain:'earnings',event_id:'earnings:nvda',company_id:'nvda',name:'NVIDIA',ticker:'NVDA',cik:'0001045810',fiscal_year:2027,fiscal_quarter:3,period_label:'Q3 FY2027',period_end:'2026-10-25',publication_status:'unconfirmed',release,call,history:[release,call]};
afterEach(()=>{cleanup();vi.unstubAllGlobals();setLanguage('en');});

describe('time certainty',()=>{
 it.each(['en','pl'] as const)('keeps release approximate and call separate in %s',language=>{
  setLanguage(language);expect(earningsTime(release)).toBe(language==='pl'?'ok. 22:20 — wyniki':'approx. 22:20 — results');
  expect(earningsTime(call)).toContain('23:00');expect(earningsSummary(event)).not.toContain('23:00');
 });
 it('exact, approximate, session and unknown remain distinct',()=>{
  expect(earningsTime({...release,precision:'exact',scheduled_at_utc:'2026-11-17T21:20:00Z',expected_time_utc:null})).toBe('22:20 — results');
  expect(earningsTime({...release,precision:'after_close',expected_time_utc:null,session_boundary_utc:'2026-11-17T21:00:00Z'})).toBe('22:00+ — after US close');
  expect(earningsTime({...release,precision:'after_close',expected_time_utc:null,session_boundary_utc:'2026-10-29T20:00:00Z'})).toBe('21:00+ — after US close');
  expect(earningsTime({...release,precision:'after_close',expected_time_utc:null})).toBe('After US close');
  expect(earningsTime({...release,precision:'before_open',expected_time_utc:null})).toBe('Before US open');
  expect(earningsTime({...release,precision:'date_only',expected_time_utc:null})).toBe('Time not announced');
  expect(earningsTime(unknown)).toBe('Date not announced');
 });
 it('early close uses the supplied reviewed boundary, not regular 16 ET',()=>{
  expect(earningsTime({...release,precision:'after_close',expected_time_utc:null,session_boundary_utc:'2026-11-27T18:00:00Z'})).toBe('19:00+ — after US close');
 });
 it('does not promote a call to release time or fabricate date-only Polish day',()=>{
  expect(earningsSummary({...event,release:unknown})).toBe('Results: time unknown');
  expect(earningsSummary({...event,release:unknown,call:unknown})).toBe('Date not announced');
  expect(earningsDay({...event,release:{...release,precision:'date_only',poland_date:null,expected_time_utc:null}})).toBe('2026-11-17');
  expect(earningsDay({...event,release:{...release,precision:'exact',scheduled_at_utc:'2026-11-18T00:30:00Z',poland_date:'2026-11-18'}})).toBe('2026-11-18');
 });
});

it.each(['en','pl'] as const)('renders metadata, source, unknown and Escape/focus in %s',async language=>{
 setLanguage(language);const fetcher=vi.fn().mockResolvedValue({ok:true,json:async()=>({events:[event],undated:[{...event,event_id:'earnings:next',period_label:'Q4 FY2027',release:unknown,call:unknown}],earnings_data_revision:'e1'})});vi.stubGlobal('fetch',fetcher);
 render(<EarningsCalendar startDate="2026-11-01" endDate="2026-11-30"/>);
 const row=(await screen.findByText('NVDA · Q3 FY2027')).closest('tr')!;
 expect(row).toHaveTextContent('22:20');expect(row).toHaveTextContent('23:00');
 expect(screen.getAllByText(new RegExp(language==='pl'?'Konferencja: 23:00':'Conference: 23:00'))).toHaveLength(1);
 expect(row.querySelector('a')).toBeNull();expect(screen.queryByRole('button')).not.toBeInTheDocument();
 expect(row.lastElementChild).toHaveTextContent(/^—$/);
 expect(screen.queryByRole('heading',{name:language==='pl'?'Termin nieogłoszony':'Date not announced'})).not.toBeInTheDocument();
 expect(screen.queryByText(/Q4 FY2027/)).not.toBeInTheDocument();
 expect(screen.queryByText('EPS')).not.toBeInTheDocument();expect(screen.queryByText('00:00')).not.toBeInTheDocument();
 expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();await waitFor(()=>expect(fetcher).toHaveBeenCalledTimes(1));
 expect(String(fetcher.mock.calls[0][0])).not.toContain('tickers=');expect(fetcher.mock.calls.every(call=>!call[1]?.method)).toBe(true);
});

it('shows retry after an API error without starting a refresh',async()=>{
 const fetcher=vi.fn().mockResolvedValueOnce({ok:false}).mockResolvedValue({ok:true,json:async()=>({events:[],undated:[]})});vi.stubGlobal('fetch',fetcher);
 render(<EarningsCalendar startDate="2026-11-01" endDate="2026-11-30"/>);
 expect(await screen.findByRole('alert')).toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'Retry'}));
 expect(await screen.findByText('No earnings releases with a confirmed date in the selected range.')).toBeInTheDocument();expect(fetcher).toHaveBeenCalledTimes(2);
});
