import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {EarningsCalendar} from './EarningsCalendar';
import {financialStatus,financialValue,epsBasis} from './earningsFinancialPresentation';
import type {EarningsItem,EarningsTime,FinancialObservation,ReportDocument} from './earningsTypes';
import {setLanguage} from '../i18n/language';

const unknown:EarningsTime={component:'release',date_status:'unknown',precision:'unknown',source_local_date:null,source_local_time:null,source_timezone:null,timezone_label_raw:null,scheduled_at_utc:null,expected_time_utc:null,poland_date:null,session_boundary_utc:null,session_boundary_source:null,source_url:null,verified_on:null,facts:null,verification_method:null,sequence:0};
const metric:FinancialObservation={metric:'reported_diluted_eps',actual:'29.43',currency:'TWD',unit:'TWD/share',source_value:'29.43',source_unit:'per_share',decimal_places:'2',methodology:'reported_diluted_total_eps',source_url:'https://pr.tsmc.com/english/news/3346',document_type:'earnings_release',verified_on:'2026-11-04',captured_at:'2026-11-04T09:00:00Z',source_version:'review-1',version:'1',observation_id:'eps',supersedes_id:null,correction_reason:null,release_date:'2026-10-15',period_end:'2026-09-30',evidence_method:'manual_official_report_review',reporting_standard:'IFRS',share_basis:'ordinary_share'};
const doc:ReportDocument={document_type:'earnings_release',source_url:metric.source_url,linked_from:null,release_date:'2026-10-15',period_end:'2026-09-30',verified_on:'2026-11-04',verification_method:'manual_official_report_review',source_version:'review-1',facts:'TIFRS; TWD per ordinary share, not USD per ADR.',version:'1',correction_reason:null,reporting_standard:'IFRS',reporting_currency:'TWD',eps_share_basis:'ordinary_share',captured_at:'2026-11-04T09:00:00Z'};
const event:EarningsItem={domain:'earnings',event_id:'earnings:tsm',company_id:'tsm',cik:'0001046179',ticker:'TSM',name:'Taiwan Semiconductor Manufacturing',fiscal_year:2026,fiscal_quarter:3,period_label:'Q3 2026',period_end:'2026-09-30',publication_status:'unconfirmed',release:{...unknown,date_status:'confirmed',precision:'date_only',source_local_date:'2026-10-15',source_timezone:'Asia/Taipei'},call:unknown,history:[],financial_store_status:'available',report_store_status:'available',publication_state:{code:'published_complete',reason:'verified_official_release',missing_metrics:[],evidence:[doc]},reported_eps_actual:metric,gaap_diluted_eps_actual:null,revenue_actual:{...metric,metric:'revenue',actual:'1494240000000',unit:'TWD',share_basis:'not_applicable',source_value:'1494.24',source_unit:'billions',methodology:'consolidated_revenue',observation_id:'revenue'},financial_history:[metric],report_documents:[doc]};
afterEach(()=>{cleanup();vi.unstubAllGlobals();setLanguage('en');vi.useRealTimers();});

it.each(['en','pl'] as const)('renders original currency and reporting basis with neutral headers in %s',async language=>{
 setLanguage(language);vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({events:[event],undated:[{...event,event_id:'unknown',ticker:'UNDATED'}]})}));
 render(<EarningsCalendar startDate="2026-10-01" endDate="2026-10-31"/>);
 const button=await screen.findByRole('button',{name:/TSM/});
 expect(screen.getByRole('columnheader',{name:new RegExp(language==='pl'?'EPS raportowany':'Reported EPS')})).toBeInTheDocument();
 expect(screen.queryByText(/All companies.*USD|Wszystkie spółki.*USD|EPS GAAP/)).not.toBeInTheDocument();
 expect(button.closest('tr')).toHaveTextContent(language==='pl'?'29,43 TWD':'29.43 TWD');
 expect(button.closest('tr')).toHaveTextContent(language==='pl'?'dane zweryfikowane':'actuals verified');
 expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();expect(screen.queryByText('UNDATED')).not.toBeInTheDocument();
 fireEvent.click(button);expect(screen.getByText(/^IFRS diluted EPS · (ordinary\/common share|akcja zwykła)$/)).toBeInTheDocument();
 expect(screen.getByRole('link',{name:/Official report|Oficjalny raport/})).toHaveAttribute('href',metric.source_url);
 expect(screen.getByText(/TIFRS; TWD per ordinary share/)).toBeInTheDocument();
 fireEvent.keyDown(screen.getByRole('link',{name:/Official report|Oficjalny raport/}),{key:'Escape'});
 expect(button).toHaveFocus();
});

it.each([
 ['scheduled','Scheduled','Zaplanowano'],['published_pending','Published · financials pending','Opublikowano · dane w weryfikacji'],
 ['published_complete','Published · actuals verified','Opublikowano · dane zweryfikowane'],
 ['date_passed_unconfirmed','Date passed · release unconfirmed','Termin minął · publikacja niepotwierdzona'],
] as const)('uses server publication state %s without frontend date heuristics',(code,en,pl)=>{
 const e={...event,publication_state:{...event.publication_state!,code}};
 expect(financialStatus(e)).toBe(en);setLanguage('pl');expect(financialStatus(e)).toBe(pl);
});
it('identifies which metric is missing instead of implying complete actuals',()=>{
 const e={...event,publication_state:{...event.publication_state!,code:'published_partial' as const,missing_metrics:['reported_diluted_eps']}};
 expect(financialStatus(e)).toContain('missing: EPS');setLanguage('pl');expect(financialStatus(e)).toContain('brak: EPS');
});
it('distinguishes IFRS ordinary shares, GAAP and ADR and preserves zero/negative values',()=>{
 expect(epsBasis(metric)).toContain('IFRS');expect(epsBasis({...metric,reporting_standard:'US_GAAP',share_basis:'ADR'})).toContain('US GAAP diluted EPS · ADR');
 expect(financialValue({...metric,actual:'0',currency:'EUR'})).toBe('0.00 EUR');
 expect(financialValue({...metric,actual:'-2.16',currency:'USD'})).toBe('-2.16 USD');
 expect(financialValue(null)).toBe('—');
});
