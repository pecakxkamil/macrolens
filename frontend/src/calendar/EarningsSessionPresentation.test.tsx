import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import {EarningsCalendar} from './EarningsCalendar';
import {earningsSessionPresentation as timing,earningsSessionLabel} from './earningsSessionPresentation';
import type {EarningsItem,EarningsTime} from './earningsTypes';
import {setLanguage} from '../i18n/language';

const unknown:EarningsTime={component:'release',date_status:'unknown',precision:'unknown',source_local_date:null,source_local_time:null,source_timezone:null,timezone_label_raw:null,scheduled_at_utc:null,expected_time_utc:null,poland_date:null,session_boundary_utc:null,session_boundary_source:null,source_url:null,verified_on:null,facts:null,verification_method:null,sequence:0};
const verified={date_status:'confirmed',source_url:'https://issuer.example/release',verified_on:'2026-11-04',verification_method:'manually_verified_official_source'} as const;
const session=(day='2026-11-02',close='21:00')=>({date:day,open_at_utc:day+'T14:30:00Z',close_at_utc:day+'T'+close+':00Z',source:'https://www.nyse.com/trade/hours-calendars'});
const base:EarningsItem={domain:'earnings',event_id:'test',company_id:'issuer',cik:'0000000001',ticker:'TEST',name:'Synthetic issuer',fiscal_year:2026,fiscal_quarter:3,period_label:'Q3 2026',period_end:null,publication_status:'unconfirmed',release:{...unknown,...verified,precision:'date_only',source_local_date:'2026-11-02'},call:{...unknown,...verified,component:'call',precision:'exact',source_local_date:'2026-11-02',source_timezone:'America/Los_Angeles',scheduled_at_utc:'2026-11-02T22:00:00Z'},history:[],session_context:{us_listed:true,release:session(),call:session()}};
afterEach(()=>{cleanup();vi.unstubAllGlobals();setLanguage('en');});

it.each([['AAPL','indicative'],['PLTR','indicative'],['AMD','official'],['INTC','official'],['AMZN','indicative'],['ARM','official'],['QCOM','official']] as const)('uses a general rule for %s without changing evidence', (ticker,basis)=>{
 const e={...base,ticker,release:{...base.release,precision:basis==='official'?'after_close' as const:'date_only' as const}};
 const before=JSON.stringify(e);
 expect(timing(e)).toMatchObject({window:'after_close',basis});
 expect(JSON.stringify(e)).toBe(before);
 expect(e.release.scheduled_at_utc).toBeNull();
});

it.each(['en','pl'] as const)('renders one shared vocabulary and two lines in %s',async language=>{
 setLanguage(language);
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({events:[base],undated:[]})}));
 const view=render(<EarningsCalendar startDate="2026-11-01" endDate="2026-11-30"/>);
 const row=(await screen.findByText('TEST · Q3 2026')).closest('tr')!;
 const cell=row.querySelector('td')!;
 expect(cell.firstChild?.textContent).toBe(language==='pl'?'Po sesji USA':'After US close');
 expect(cell.querySelector('small')).toHaveTextContent(language==='pl'?'Konferencja: 23:00 PL':'Call: 23:00 Warsaw');
 expect(cell.querySelectorAll('small')).toHaveLength(1);
 expect(cell.className).toContain('earnings-center');
 expect(view.container.querySelectorAll('thead th')).toHaveLength(7);
 expect(cell).not.toHaveTextContent(/21:00|America\/|unknown|nieogłoszona/);
});

it('official before-open or exact during-session evidence wins over the late call',()=>{
 for(const [precision,instant,expected] of [['before_open',null,'before_open'],['exact','2026-11-02T16:00:00Z','during_session']] as const){
  const e={...base,release:{...base.release,precision,scheduled_at_utc:instant}};
  expect(timing(e)).toMatchObject({window:expected,basis:'official'});
 }
});

it('does not infer when there is no basis, an unverified call, another day, or no US listing',()=>{
 for(const e of [
  {...base,call:unknown},
  {...base,call:{...base.call,verified_on:null}},
  {...base,call:{...base.call,date_status:'cancelled' as const}},
  {...base,session_context:{...base.session_context!,us_listed:false}},
  {...base,session_context:{...base.session_context!,call:null}},
  {...base,session_context:{...base.session_context!,call:session('2026-11-03')}},
  {...base,release:{...base.release,date_status:'cancelled' as const}},
  {...base,financial_release_date:'2026-10-30'},
  {...base,call:{...base.call,scheduled_at_utc:'2026-11-02T20:00:00Z'}},
 ])expect(timing(e).window).toBe('unknown');
 expect(timing({...base,call:unknown}).call).toBeNull();
 expect(earningsSessionLabel({...base,call:unknown})).toBe('Time not confirmed');
 setLanguage('pl');expect(earningsSessionLabel({...base,call:unknown})).toBe('Godzina niepotwierdzona');
});

it('does not override a different approximate release schedule with the call',()=>{
 const e={...base,release:{...base.release,precision:'approximate' as const,expected_time_utc:'2026-11-02T12:00:00Z'}};
 expect(timing(e)).toMatchObject({window:'before_open',basis:'indicative'});
 expect(timing({...e,release:{...e.release,expected_time_utc:'2026-11-02T16:00:00Z'}}).window).toBe('unknown');
});

it('keeps an official after-close window despite a call during the session',()=>{
 const e={...base,release:{...base.release,precision:'after_close' as const},call:{...base.call,scheduled_at_utc:'2026-11-02T18:00:00Z'}};
 expect(timing(e)).toMatchObject({window:'after_close',basis:'official',call:'Call: 19:00 Warsaw'});
});

it.each(['scheduled','published_complete'] as const)('does not derive a time from publication status %s',code=>{
 expect(timing({...base,publication_state:{code,reason:'test',missing_metrics:[],evidence:[]}})).toEqual(timing(base));
});

it.each([['2026-03-16','20:00','21:00','22:00'],['2026-03-30','20:00','21:00','23:00'],['2026-10-29','20:00','21:00','22:00'],['2026-11-02','21:00','22:00','23:00'],['2026-11-27','18:00','18:30','19:30']])('uses actual UTC sessions and Warsaw DST on %s',(day,close,call,warsaw)=>{
 const e={...base,release:{...base.release,source_local_date:day},call:{...base.call,source_local_date:day,scheduled_at_utc:day+'T'+call+':00Z'},session_context:{us_listed:true,release:session(day,close),call:session(day,close)}};
 expect(timing(e)).toMatchObject({window:'after_close',basis:'indicative',call:'Call: '+warsaw+' Warsaw'});
});

it('uses short shared labels for every confirmed window in both languages',()=>{
 for(const [language,after,before,during] of [['en','After US close','Before US open','During US session'],['pl','Po sesji USA','Przed sesją USA','W trakcie sesji USA']] as const){
  setLanguage(language);
  expect(earningsSessionLabel({...base,release:{...base.release,precision:'after_close'}})).toBe(after);
  expect(earningsSessionLabel({...base,release:{...base.release,precision:'before_open'}})).toBe(before);
  expect(earningsSessionLabel({...base,release:{...base.release,precision:'exact',scheduled_at_utc:'2026-11-02T16:00:00Z'}})).toBe(during);
 }
});
