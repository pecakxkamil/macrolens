import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import {EarningsCalendar} from './EarningsCalendar';
import {marketCap} from './earningsMarketCap';
import type {EarningsItem} from './earningsTypes';
import {setLanguage} from '../i18n/language';

const empty={component:'release',date_status:'unknown',precision:'unknown',source_local_date:null,source_local_time:null,source_timezone:null,timezone_label_raw:null,scheduled_at_utc:null,expected_time_utc:null,poland_date:null,session_boundary_utc:null,session_boundary_source:null,source_url:null,verified_on:null,facts:null,verification_method:null,sequence:0} as const;
const event:EarningsItem={domain:'earnings',event_id:'one',company_id:'issuer',cik:'0000000001',name:'Synthetic issuer',ticker:'TEST',fiscal_year:2026,fiscal_quarter:3,period_label:'Q3 2026',period_end:null,publication_status:'unconfirmed',release:{...empty,date_status:'confirmed',precision:'date_only',source_local_date:'2026-11-02'},call:{...empty,component:'call'},history:[],market_cap_usd:'850400000000.123456789',market_cap_as_of:'2026-11-03',market_cap_status:'verified_snapshot'};
afterEach(()=>{cleanup();vi.unstubAllGlobals();setLanguage('en');});

it.each(['en','pl'] as const)('renders dated USD billions, seven columns and no details in %s',async language=>{
 setLanguage(language);vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({events:[event,{...event,event_id:'two',period_label:'Q2 2026'}],undated:[]})}));
 const view=render(<EarningsCalendar startDate="2026-11-01" endDate="2026-11-30"/>);
 await screen.findByRole('table');expect(screen.getAllByRole('columnheader')).toHaveLength(7);
 expect(screen.getByRole('columnheader',{name:'Market Cap'})).toBeInTheDocument();
 expect(screen.queryByRole('columnheader',{name:/Status|Details|Szczegóły/})).not.toBeInTheDocument();
 expect(screen.queryByRole('button')).not.toBeInTheDocument();expect(view.container.querySelector('.earnings-details')).toBeNull();
 const cells=[...view.container.querySelectorAll('.earnings-row')].map(row=>row.lastElementChild!);
 expect(cells).toHaveLength(2);for(const cell of cells){expect(cell).toHaveTextContent(language==='pl'?'850,4 mld USD':'850.4 bn USD');expect(cell.querySelector('small')).toBeNull();}
 expect(screen.queryByText(/live/i)).not.toBeInTheDocument();
});

it.each([undefined,null,'0','-1','NaN','Infinity','garbage'])('does not fabricate a cap for %s',value=>{
 expect(marketCap({...event,market_cap_usd:value})).toBeNull();
});
it('requires both a verified status and a real measurement date',()=>{
 for(const changes of [{market_cap_status:'unavailable' as const},{market_cap_status:'stale' as const},{market_cap_as_of:null},{market_cap_as_of:'2026-02-30'}])expect(marketCap({...event,...changes})).toBeNull();
});
it('formats precise amounts and small issuers without zero placeholders',()=>{
 expect(marketCap({...event,market_cap_usd:'1000000005.999999999'})?.value).toBe('1 bn USD');
 expect(marketCap({...event,market_cap_usd:'1'})?.value).toBe('< 0.01 bn USD');
 expect(marketCap({...event,market_cap_usd:'850405000000'})?.value).toBe('850.41 bn USD');
});

it.each(['TGMCharts','DeltaScreener'] as const)('keeps the Market Cap header plain for %s',async provider=>{
 const source=provider==='TGMCharts'?'https://tgmcharts.com':'https://deltascreener.com/data';
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({events:[{...event,market_cap_provider:provider,market_cap_source:source}],undated:[]})}));
 render(<EarningsCalendar startDate="2026-11-01" endDate="2026-11-30"/>);
 expect(await screen.findByRole('columnheader',{name:'Market Cap'})).toHaveTextContent(/^Market Cap$/);
 expect(screen.queryByRole('link',{name:provider})).not.toBeInTheDocument();
 expect(screen.getAllByRole('columnheader')).toHaveLength(7);
 expect(marketCap({...event,market_cap_provider:provider,market_cap_source:'https://unapproved.invalid'} as EarningsItem)?.source).toBeUndefined();
});

it('groups four-digit Polish billions',()=>{setLanguage('pl');expect(marketCap({...event,market_cap_usd:'4937502977600'})?.value).toBe('4\u00a0937,5 mld USD');});
