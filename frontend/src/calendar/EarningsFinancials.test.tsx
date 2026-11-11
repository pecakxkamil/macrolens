import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import {EarningsCalendar} from './EarningsCalendar';
import {financialValue,compareEarnings} from './earningsFinancialPresentation';
import type {EarningsItem,EarningsTime,FinancialObservation} from './earningsTypes';
import {setLanguage} from '../i18n/language';
const unknown:EarningsTime={component:'release',date_status:'unknown',precision:'unknown',source_local_date:null,source_local_time:null,source_timezone:null,timezone_label_raw:null,scheduled_at_utc:null,expected_time_utc:null,poland_date:null,session_boundary_utc:null,session_boundary_source:null,source_url:null,verified_on:null,facts:null,verification_method:null,sequence:0};
const observation:FinancialObservation={metric:'revenue',actual:'16513000000',currency:'USD',unit:'USD',source_value:'16513',source_unit:'USD_millions',decimal_places:'0',methodology:'consolidated_revenue',source_url:'https://www.intc.com/news-events/press-releases/detail/1786/intel-reports-third-quarter-2026-financial-results',document_type:'earnings_release',verified_on:'2026-11-03',captured_at:'2026-11-03T10:00:00Z',source_version:'manual-v1',version:'1',observation_id:'revenue',supersedes_id:null,correction_reason:null,release_date:'2026-10-29',period_end:'2026-09-26',sec_accession:null,evidence_method:'manual_official_fact_entry',availability_status:'manually_verified'};
const event:EarningsItem={domain:'earnings',event_id:'earnings:intc',company_id:'intel',name:'Intel',ticker:'INTC',cik:'0000050863',fiscal_year:2026,fiscal_quarter:3,period_label:'Q3 2026',period_end:'2026-09-26',publication_status:'unconfirmed',release:unknown,call:unknown,history:[],financial_release_date:'2026-10-29',financial_store_status:'available',financial_data_status:'complete',financial_publication_status:'published',revenue_actual:observation,gaap_diluted_eps_actual:{...observation,metric:'gaap_diluted_eps',actual:'-2.16',unit:'USD/share',methodology:'gaap_diluted_attributable_to_intel',observation_id:'eps'},financial_history:[observation],eps_consensus:null,revenue_consensus:null};
afterEach(()=>{cleanup();vi.unstubAllGlobals();setLanguage('en');});
it.each(['en','pl'] as const)('shows every company, financial values, null forecasts and official evidence in %s',async language=>{
 setLanguage(language);
 const fourth={...event,event_id:'earnings:four',ticker:'FOUR',company_id:'synthetic-four',cik:'9999999999',name:'Synthetic fourth company',financial_data_status:'partial' as const,gaap_diluted_eps_actual:null};
 const fetcher=vi.fn().mockResolvedValue({ok:true,json:async()=>({events:[event,fourth],undated:[]})});vi.stubGlobal('fetch',fetcher);
 const view=render(<EarningsCalendar startDate="2026-10-01" endDate="2026-10-31"/>);
 const button=await screen.findByRole('link',{name:/INTC · Q3 2026/});
 expect(screen.getByRole('table')).toBeInTheDocument();expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
 expect(screen.getByText('Synthetic fourth company')).toBeInTheDocument();
 const row=button.closest('tr')!;
 expect(row).toHaveTextContent(language==='pl'?'16,51 mld USD':'16.51 bn USD');
 expect(row).toHaveTextContent(language==='pl'?'-2,16 USD':'-2.16 USD');
 expect(row.querySelectorAll('td.earnings-number small')).toHaveLength(4);expect([...row.querySelectorAll('td.earnings-number small')].every(x=>x.textContent==='—')).toBe(true);
 expect(row.children).toHaveLength(7);
 expect(screen.queryByText(/beat|miss|surprise/i)).not.toBeInTheDocument();
 expect(button).toHaveAttribute('href',observation.source_url);button.focus();expect(button).toHaveFocus();
 expect(screen.queryByText(/manual-v1/)).not.toBeInTheDocument();expect(view.container.querySelector('.earnings-details')).toBeNull();
 view.rerender(<EarningsCalendar startDate="2026-10-01" endDate="2026-10-31"/>);
 expect(fetcher).toHaveBeenCalledTimes(1);expect(String(fetcher.mock.calls[0][0])).not.toContain('tickers');
});
it('formats millions, billions, zero, missing values and source precision',()=>{
 expect(financialValue({...observation,actual:'2500000'})).toBe('2.5 m USD');
 expect(financialValue({...observation,metric:'gaap_diluted_eps',actual:'0'})).toBe('0.00 USD');
 expect(financialValue(null)).toBe('—');
});
it('sorts by actual date/time, ticker and stable ID without inventing unknown dates',()=>{
 const late={...event,event_id:'z',release:{...unknown,date_status:'confirmed' as const,source_local_date:'2026-10-29',scheduled_at_utc:'2026-10-29T21:00:00Z',poland_date:'2026-10-29'}};
 const early={...late,event_id:'a',release:{...late.release,scheduled_at_utc:'2026-10-29T20:00:00Z'}};
 expect([event,late,early].sort(compareEarnings).map(x=>x.event_id)).toEqual(['a','z',event.event_id]);
 expect(compareEarnings({...event,event_id:'a'},{...event,event_id:'b'})).toBeLessThan(0);
});


it.each(['en','pl'] as const)('colors detailed current EPS and revenue independently against comparable previous in %s',async language=>{
 setLanguage(language);
 const eps={...observation,metric:'reported_diluted_eps',unit:'USD/share',actual:'0.12',methodology:'reported_diluted_total_eps'} as FinancialObservation;
 const item:EarningsItem={...event,release:{...unknown,date_status:'confirmed',source_local_date:'2026-10-29',poland_date:'2026-10-29'},current_eps_actual:eps,previous_eps_actual:{...eps,actual:'0.25'},current_revenue_actual:{...observation,actual:'1443000000'},previous_revenue_actual:{...observation,actual:'1289000000'},previous_period:{fiscal_year:2026,fiscal_quarter:2,period_label:'Q2 2026',period_end:null}};
 const state={data:{events:[item],undated:[]},error:null,retry:vi.fn()} as never;
 const view=render(<EarningsCalendar startDate="2026-10-01" endDate="2026-10-31" state={state}/>);
 const cells=()=>document.querySelectorAll('.earnings-row .earnings-number');
 expect(cells()[0].firstChild).toHaveClass('earnings-actual--negative');expect(cells()[2].firstChild).toHaveClass('earnings-actual--positive');
 expect(cells()[1].querySelector('[class*="earnings-actual--"]')).toBeNull();expect(cells()[0].querySelector('small')).not.toHaveClass('earnings-actual--negative');
 item.current_eps_actual={...eps,actual:'0.50'};item.current_revenue_actual={...observation,actual:'1200000000'};
 view.rerender(<EarningsCalendar startDate="2026-10-01" endDate="2026-10-31" state={state}/>);
 expect(cells()[0].firstChild).toHaveClass('earnings-actual--positive');expect(cells()[2].firstChild).toHaveClass('earnings-actual--negative');
 item.previous_eps_actual=null;item.current_revenue_actual=item.previous_revenue_actual;
 view.rerender(<EarningsCalendar startDate="2026-10-01" endDate="2026-10-31" state={state}/>);
 expect(cells()[0].firstChild).toHaveClass('earnings-actual--neutral');expect(cells()[2].firstChild).toHaveClass('earnings-actual--neutral');
 expect(document.querySelectorAll('thead th')).toHaveLength(7);
});
