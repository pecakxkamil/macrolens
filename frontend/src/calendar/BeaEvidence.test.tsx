import {cleanup,render,screen} from '@testing-library/react';
import {afterEach,test,expect} from 'vitest';
import type {CalendarMeasure,OverviewReadingComparison} from '../api/macrolens';
import {setLanguage} from '../i18n/language';
import {BeaEvidence} from './BeaEvidence';
import {calendarReadingValue} from './calendarPresentation';
import {calendarComparison} from './calendarComparisons';
import {prepareReading,readingReportLine} from '../brief/readingComparisons';

const measure:CalendarMeasure={revision_confirmed:false,binding_method:"official_bea_published_value",vintage_date:"2026-10-29",realtime_end:null,result_status:"available",series_id:'GDPC1',feature_name:'qoq_annualized',frequency:'quarterly',unit:'percent',label:'Real GDP',reference_period:'2026-07-01',previous_period:'2026-04-01',previous_kind:'previous_period',actual:1.2,previous:2.3,forecast:null,consensus_status:'not_integrated',data_version:'official_release',mapping_status:'confirmed',selected_source:'bea_official',published_precision:1,previous_precision:1,source_url:'https://www.bea.gov/news/synthetic',source_comparison:'consistent_with_rounding',comparison_status:'same_bea_document',actual_provenance:{original_title:'Synthetic GDP',retrieved_at:'2026-10-29T20:00:00Z',raw_hash:'abc',estimate_stage:'advance'},fred_alternative:{actual:1.234567,previous:2.34},usage_rights:{source:'BEA',copyright:'BEA',original_url:'https://www.bea.gov/news/synthetic',modifications:'MacroLens normalization',redistribution_conditions:'Retain attribution',terms_url:'https://www.bea.gov/help/faq/147'}};
afterEach(()=>{cleanup();setLanguage('en');});

test.each(['en','pl'] as const)('published precision and source details are explicit in %s',language=>{
 setLanguage(language);render(<BeaEvidence measure={measure}/>);
 expect(screen.getByRole('region')).toHaveTextContent(language==='en'?'Official BEA reading: 1.2%':'Oficjalny odczyt BEA: 1,2%');
 expect(screen.getByRole('region')).toHaveTextContent('1.234567%');
 expect(screen.getByRole('link',{name:language==='en'?'Official event document':'Oficjalny dokument wydarzenia'})).toHaveAttribute('href',measure.source_url);
 expect(screen.getByRole('region')).toHaveTextContent(language==='en'?'not proof of the first print':'nie potwierdza pierwszego wydania');
 expect(calendarReadingValue({...measure,actual:0},'actual')).toBe(language==='en'?'0.0%':'0,0%');
});

test.each(['en','pl'] as const)('source conflicts and mixed previous are not hidden in %s',language=>{
 setLanguage(language);const mixed={...measure,source_comparison:'conflict' as const,comparison_status:'mixed_sources' as const,previous_precision:null};
 render(<BeaEvidence measure={mixed}/>);
 expect(screen.getByRole('region')).toHaveTextContent(language==='en'?'Source conflict':'Konflikt źródeł');
 expect(screen.getByRole('region')).toHaveTextContent(language==='en'?'difference across these sources is not calculated':'Nie obliczamy różnicy');
 expect(calendarComparison(mixed,'previous')).toBeNull();expect(calendarComparison(mixed,'forecast')).toBeNull();
});

test('explicit FRED fallback does not claim a BEA Actual',()=>{
 render(<BeaEvidence measure={{...measure,selected_source:'fred_fallback'}}/>);
 expect(screen.getByText(/FRED fallback/)).toBeInTheDocument();expect(screen.queryByRole('region')).not.toBeInTheDocument();
});

test('Overview and export retain precision, source, stage and captured-snapshot limits',()=>{
 const item={series_id:'GDPC1',feature_name:'qoq_annualized',component:'real_gdp',frequency:'quarterly',unit:'percent',change_unit:'percentage points',change:-1.1,current:{value:1.2,observation_date:'2026-07-01',published_precision:1},previous:{value:2.3,observation_date:'2026-04-01',published_precision:1},bea_direct:measure} as OverviewReadingComparison;
 const prepared=prepareReading('real_gdp','GDPC1',item);
 expect(prepared.current.display).toBe('1.2%');expect(prepared.previous.display).toBe('2.3%');expect(prepared.tone).toBe('neutral');
 const report=readingReportLine(prepared);expect(report).toContain('Bureau of Economic Analysis');expect(report).toContain('advance');expect(report).toContain('not verified first print');expect(report).toContain('abc');
});
