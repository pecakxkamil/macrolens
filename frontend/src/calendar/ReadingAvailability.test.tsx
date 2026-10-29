import {cleanup,render,screen} from '@testing-library/react';
import {afterEach,expect,test} from 'vitest';
import type {CalendarCheck,CalendarMeasure,OverviewRefreshState} from '../api/macrolens';
import {setLanguage} from '../i18n/language';
import {ReadingAvailability} from './ReadingAvailability';

const measure:CalendarMeasure={series_id:'GDPC1',label:'Real GDP',feature_name:'qoq_annualized',frequency:'quarterly',unit:'percent',reference_period:'2026-07-01',previous_period:'2026-04-01',previous_kind:'previous_period',actual:null,previous:2.22,forecast:null,consensus_status:'not_integrated',data_version:null,revision_confirmed:false,binding_method:'official_schedule',vintage_date:null,realtime_end:null,result_status:'awaiting_data',mapping_status:'confirmed',source_url:'https://fred.stlouisfed.org/series/GDPC1',period_provenance:{source_url:'https://www.bea.gov/news/schedule/full',reference_period:'2026-07-01',binding_method:'official_schedule',report_url:'https://www.bea.gov/news/gdp'}};
const check:CalendarCheck={status:'partial',checked_at:'2020-01-01T00:00:00Z',start_date:'2026-10-29',end_date:'2026-10-29',required_resources:['fred:GDPC1'],sources:[{resource:'fred:GDPC1',label:'GDPC1',range_status:'success',checked_at:'2020-01-01T00:00:00Z',last_finished_at:'2026-10-29T12:52:18Z',error_code:null,scope:{observation_end:'2026-04-01',last_updated:'2026-09-30 07:53:55-05',observation_fetch_status:'metadata_unchanged'}},{resource:'calendar:periods',label:'Publishers',range_status:'partial',checked_at:null,error_code:null,scope:{sources:[{source_url:'https://www.bea.gov/news/gdp',status:'error',error_code:'ValueError'}]}}]};
const refresh:OverviewRefreshState={status:'partial',publication_id:'new-generation',completed_at:'2026-10-29T13:09:56Z',next_check_at:'2026-10-29T13:24:56Z',results:[{resource:'fred:GDPC1',status:'success',outcome:'unchanged'}]};
afterEach(()=>{cleanup();setLanguage('en');});

test.each(['en','pl'] as const)('missing GDP shows its own check, metadata period and document failure in %s',language=>{
 setLanguage(language);render(<ReadingAvailability measure={measure} check={check} refresh={refresh} now={new Date('2026-10-29T12:53:00Z')}/>);
 const details=screen.getByRole('region',{name:language==='en'?'Reading availability':'Dostępność odczytu'});
 expect(details).toHaveTextContent('GDPC1');expect(details).toHaveTextContent('13:52');
 expect(details).not.toHaveTextContent('2020');
 expect(details).toHaveTextContent(language==='en'?'provider metadata was unchanged':'metadane dostawcy się nie zmieniły');
 expect(details).toHaveTextContent(language==='en'?'could not be validated':'Nie udało się zweryfikować');
 expect(details).toHaveTextContent(language==='en'?'Expected report period':'Oczekiwany okres raportu');
 expect(details).toHaveTextContent(language==='en'?'Next permitted source check':'Następna dozwolona kontrola');
 expect(details).not.toHaveTextContent(language==='en'?'Generation published':'Publikacja generacji');
});

test('available result uses only the matching displayed generation completion, never ingestion time',()=>{
 const current={...measure,actual:3.37,data_version:'current_vintage' as const,actual_provenance:{vintage_date:'2026-10-29',ingested_at:'2000-01-01'}};
 const {rerender}=render(<ReadingAvailability measure={current} check={check} refresh={refresh} revision='old-generation' now={new Date('2026-10-29T13:10:00Z')}/>);
 expect(screen.getByText(/Actual is available/)).toBeInTheDocument();
 expect(screen.queryByText(/Generation published/)).not.toBeInTheDocument();
 rerender(<ReadingAvailability measure={current} check={check} refresh={refresh} revision='new-generation' now={new Date('2026-10-29T13:10:00Z')}/>);
 expect(screen.getByText(/Generation published/)).toHaveTextContent('14:09');
 expect(document.body).not.toHaveTextContent('2000-01-01');
 rerender(<ReadingAvailability measure={current} check={check} refresh={{...refresh,status:'error'}} revision='new-generation' now={new Date('2026-10-29T13:10:00Z')}/>);
 expect(screen.queryByText(/Generation published/)).not.toBeInTheDocument();
});

test('absent per-series metadata never borrows another series or global checked_at',()=>{
 render(<ReadingAvailability measure={{...measure,series_id:'PCEPI'}} check={check} refresh={refresh} now={new Date()}/>);
 expect(screen.queryByRole('region')).not.toBeInTheDocument();
});

test.each(['error','skipped','cached'])('latest %s refresh outcome is distinct from an earlier successful source check',status=>{
 render(<ReadingAvailability measure={measure} check={check} refresh={{...refresh,results:[{resource:'fred:GDPC1',status}]}} now={new Date('2026-10-29T13:00:00Z')}/>);
 expect(document.body).toHaveTextContent(status==='error'?'source check failed':status==='skipped'?'skipped the source':'reused a stored source check');
});
