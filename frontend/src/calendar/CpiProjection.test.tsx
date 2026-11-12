import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import type {CalendarEvent,CalendarMeasure} from '../api/macrolens';
import {setLanguage} from '../i18n/language';
import {MacroTrend} from './MacroTrend';
import {macroMissingReason} from './MissingValue';
import {MacroEventCard} from './MacroEventCard';
import {calendarComparison} from './calendarComparisons';
import {macroInsight,insightWarnings} from './macroInsight';
const event={release_id:10,release_date:'2026-11-10',release_datetime_utc:'2026-11-10T13:30:00Z',release_name:'CPI'} as CalendarEvent;
const m:CalendarMeasure={label:'Core CPI',previous_period:'2026-09-01',previous_kind:'previous_period',forecast:null,consensus_status:'not_integrated',data_version:'derived_bls_snapshot',binding_method:'official_bls',vintage_date:null,realtime_end:null,result_status:'available',source_url:'https://api.bls.gov/publicAPI/v2/timeseries/data/',series_id:'CPILFESL',feature_name:'mom',frequency:'monthly',unit:'percent',reference_period:'2026-10-01',actual:0.3,previous:0.3,selected_source:'bls:cpi',mapping_status:'confirmed',revision_confirmed:false,actual_provenance:{raw_hash:'a'.repeat(64)},published_precision:1,previous_precision:1,cpi_rate_kind:'derived_index_rate',seasonal_adjustment:'SA',cpi_history:{'2026-08-01':'0.2','2026-09-01':'0.3','2026-10-01':'0.3'}};
afterEach(()=>{cleanup();setLanguage('en');vi.unstubAllGlobals();});
it.each(['pl','en'] as const)('uses neutral Core CPI comparison and explicit derived method in %s',language=>{
 setLanguage(language);expect(calendarComparison(m,'previous')?.direction).toBe('neutral');
 expect(macroInsight(event,m)).toMatch(language==='pl'?/bez zmiany/:/unchanged/);
 expect(insightWarnings(event,m).join(' ')).toMatch(language==='pl'?/Wyliczone/:/Derived/);
 render(<MacroEventCard event={event} measure={m}>{null}</MacroEventCard>);
 expect(document.querySelector('.macro-insight-change--neutral')).not.toBeNull();
});
it.each(['pl','en'] as const)('shows terminal annual base gap and no publication waiting in %s',language=>{
 setLanguage(language);const annual={...m,actual:null,feature_name:'yoy',seasonal_adjustment:'NSA',result_status:'publisher_unavailable' as const,cpi_missing_base_period:'2025-10-01',cpi_missing_proof:{missing_confirmed:true},missing_reason:{actual:'publisher_base_unavailable',previous:null}};
 expect(macroMissingReason(event,annual,'actual')).toContain('2025-10');expect(calendarComparison(annual,'previous')).toBeNull();
 render(<MacroEventCard event={event} measure={annual}>{null}</MacroEventCard>);
 expect(document.querySelector('.macro-insight-state')?.textContent).toContain('2025-10');
 expect(document.querySelector('.macro-insight-state')?.textContent).not.toMatch(/Oczekiwanie|Awaiting/);
});
it('plots one CPI capture without fetching FRED and hides derived trend for published rates',()=>{
 const fetch=vi.fn();vi.stubGlobal('fetch',fetch);const view=render(<MacroTrend measure={m}/>);
 expect(screen.getByRole('img')).toBeInTheDocument();expect(document.querySelectorAll('circle')).toHaveLength(3);expect(fetch).not.toHaveBeenCalled();
 view.rerender(<MacroTrend measure={{...m,cpi_rate_kind:'published_report_rate',cpi_history:{}}}/>);expect(screen.queryByRole('img')).toBeNull();
});
