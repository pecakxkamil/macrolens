import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import type {CalendarEvent,CalendarMeasure} from '../api/macrolens';
import {fetchSeriesHistory} from '../api/macrolens';
import {setLanguage} from '../i18n/language';
import {MacroEventCard} from './MacroEventCard';
vi.mock('../api/macrolens',async original=>({...await original<typeof import('../api/macrolens')>(),fetchSeriesHistory:vi.fn(),fetchFeatureHistory:vi.fn()}));
const event={release_name:'Job Openings and Labor Turnover Survey',release_date:'2026-11-03',release_datetime_utc:'2026-11-03T15:00:00Z',source_link:'https://www.bls.gov/jlt/'} as CalendarEvent;
const measure={series_id:'JTSJOL',label:'JOLTS',feature_name:'raw',frequency:'monthly',unit:'thousand openings',reference_period:'2026-09-01',previous_period:'2026-08-01',previous_kind:'previous_period',actual:7523,previous:7190,forecast:null,mapping_status:'confirmed',result_status:'available',data_version:'current_vintage',source_url:'https://fred.stlouisfed.org/series/JTSJOL'} as CalendarMeasure;
afterEach(()=>{cleanup();vi.clearAllMocks();setLanguage('en');});
it.each(['en','pl'] as const)('shows the selected measure and hides technical evidence by default in %s',async language=>{
 setLanguage(language);vi.mocked(fetchSeriesHistory).mockResolvedValue({series_id:'JTSJOL',frequency:'monthly',history_type:'current_vintage',unit:'thousands',observations:[{observation_date:'2026-07-01',value:7335},{observation_date:'2026-08-01',value:7190},{observation_date:'2026-09-01',value:7523}]} as never);
 render(<MacroEventCard event={event} measure={measure}><p>TECHNICAL EVIDENCE</p><a href="https://example.org/proof">Proof</a></MacroEventCard>);
 expect(screen.getByText('TECHNICAL EVIDENCE')).not.toBeVisible();expect(document.querySelector('details')).not.toHaveAttribute('open');
 expect(document.querySelectorAll('.macro-insight-values dd')).toHaveLength(3);expect(document.querySelector('.macro-insight-values dd')).toHaveTextContent(language==='pl'?'7,52 mln':'7.52 m');
 expect(await screen.findByRole('img',{name:language==='pl'?'Trend · 3 odczytów':'Trend · 3 observations'})).toBeInTheDocument();
 expect(document.querySelectorAll('.macro-insight-trend li')).toHaveLength(3);
 expect(screen.getByRole('heading',{name:language==='pl'?'Jak to interpretować?':'How to interpret it?'})).toBeInTheDocument();
 expect(document.querySelector('.macro-insight-copy')).toContainElement(document.querySelector('.macro-market-context') as HTMLElement);
 expect(document.querySelector('.macro-insight-body')?.lastElementChild).toHaveClass('macro-insight-trend');
 expect(document.querySelector('.macro-market-caveat')).toBeNull();expect(document.querySelector('.macro-market-context a')).toBeNull();expect(document.querySelector('.macro-insight-trend p')).toBeNull();
 fireEvent.click(screen.getByText(language==='pl'?'Źródła, rewizje i szczegóły techniczne':'Sources, revisions and technical details'));expect(screen.getByText('TECHNICAL EVIDENCE')).toBeVisible();
 expect(screen.getByRole('link',{name:'Proof'})).toHaveAttribute('href','https://example.org/proof');
});
it('omits numerical blocks and graphs for pending and publisher-only events',()=>{
 const view=render(<MacroEventCard event={event} measure={{...measure,actual:null}}>proof</MacroEventCard>);
 expect(screen.getByText('Awaiting publication')).toBeInTheDocument();expect(document.querySelector('dl')).toBeNull();expect(fetchSeriesHistory).not.toHaveBeenCalled();
 view.rerender(<MacroEventCard event={{...event,event_type:'adp_monthly',result_integration_status:'publisher_permission_required',document_status:'available',document_url:'https://publisher.example/report.pdf'}}>proof</MacroEventCard>);
 expect(document.querySelector('.macro-insight-state')).toHaveTextContent('Data available in the source report');expect(screen.getByRole('link',{name:'Source report'})).toHaveAttribute('href','https://publisher.example/report.pdf');expect(document.querySelector('dl')).toBeNull();
});
it('hides an invalid history rather than inventing a chart',async()=>{
 vi.mocked(fetchSeriesHistory).mockResolvedValue({series_id:'OTHER',history_type:'current_vintage',observations:[]} as never);
 render(<MacroEventCard event={event} measure={measure}>proof</MacroEventCard>);
 await waitFor(()=>expect(fetchSeriesHistory).toHaveBeenCalledTimes(1));expect(screen.queryByRole('img')).toBeNull();
});
it('refreshes history when the selected reading changes on polling',async()=>{
 vi.mocked(fetchSeriesHistory).mockResolvedValue({series_id:'JTSJOL',frequency:'monthly',unit:'thousands',history_type:'current_vintage',observations:[]} as never);
 const view=render(<MacroEventCard event={event} measure={measure}>proof</MacroEventCard>);
 await waitFor(()=>expect(fetchSeriesHistory).toHaveBeenCalledTimes(1));
 view.rerender(<MacroEventCard event={event} measure={{...measure}}>proof</MacroEventCard>);
 expect(fetchSeriesHistory).toHaveBeenCalledTimes(1);
 view.rerender(<MacroEventCard event={event} measure={{...measure,actual:7623}}>proof</MacroEventCard>);
 await waitFor(()=>expect(fetchSeriesHistory).toHaveBeenCalledTimes(2));
});
it('does not display a late history response for another selected period',async()=>{
 let resolve!:(value:never)=>void;
 vi.mocked(fetchSeriesHistory).mockReturnValueOnce(new Promise(r=>{resolve=r;})).mockResolvedValue({series_id:'OTHER',history_type:'current_vintage',observations:[]} as never);
 const view=render(<MacroEventCard event={event} measure={measure}>proof</MacroEventCard>);
 await waitFor(()=>expect(fetchSeriesHistory).toHaveBeenCalledTimes(1));
 view.rerender(<MacroEventCard event={event} measure={{...measure,reference_period:'2026-08-01',actual:7190}}>proof</MacroEventCard>);
 await waitFor(()=>expect(fetchSeriesHistory).toHaveBeenCalledTimes(2));
 expect(vi.mocked(fetchSeriesHistory).mock.calls[0][1]?.signal?.aborted).toBe(true);
 resolve({series_id:'JTSJOL',frequency:'monthly',unit:'thousands',history_type:'current_vintage',observations:[{observation_date:'2026-07-01',value:7335},{observation_date:'2026-08-01',value:7190},{observation_date:'2026-09-01',value:7523}]} as never);
 await waitFor(()=>expect(screen.queryByRole('img')).toBeNull());
});
