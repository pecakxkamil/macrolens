import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import type {CalendarEvent,CalendarMeasure} from '../api/macrolens';
import {setLanguage} from '../i18n/language';
import {MacroTrend} from './MacroTrend';
import {blsTrend} from './macroTrendData';
import {insightWarnings} from './macroInsight';

const m:CalendarMeasure={label:'NFP',previous_period:'2026-09-01',previous_kind:'previous_period',forecast:null,consensus_status:'not_integrated',data_version:'official_release',binding_method:'official_bls',vintage_date:null,realtime_end:null,result_status:'available',source_url:'https://api.bls.gov/publicAPI/v2/timeseries/data/',series_id:'PAYEMS',feature_name:'monthly_change',frequency:'monthly',unit:'thousand jobs',reference_period:'2026-10-01',actual:165,previous:60,selected_source:'bls:employment',mapping_status:'confirmed',revision_confirmed:true,actual_provenance:{raw_hash:'a'.repeat(64)},fred_alternative:{actual:null,previous:29},bls_history:{'2026-08-01':'186','2026-09-01':'60','2026-10-01':'165'}};
afterEach(()=>{cleanup();setLanguage('en');vi.unstubAllGlobals();});
it.each(['pl','en'] as const)('explains same-capture Previous without calling Current a revision in %s',language=>{
 setLanguage(language);const warnings=insightWarnings({release_date:'2026-11-06'} as CalendarEvent,m).join(' ');
 expect(warnings).toContain('BLS');expect(warnings).toContain('60');expect(warnings).toContain('29');
 expect(warnings).not.toContain('revised estimate');expect(warnings).not.toContain('zrewidowany szacunek');expect(warnings).not.toContain('\\u');
});
it('draws source-specific BLS points without requesting or mixing FRED history',()=>{
 const fetch=vi.fn();vi.stubGlobal('fetch',fetch);render(<MacroTrend measure={m}/>);
 expect(screen.getByRole('img')).toBeInTheDocument();expect(document.querySelectorAll('circle')).toHaveLength(3);
 expect(blsTrend(m).map(p=>p.value)).toEqual([186,60,165]);expect(fetch).not.toHaveBeenCalled();
});
it('keeps ordinary FRED measures on their existing path',()=>{
 expect(blsTrend({...m,selected_source:'fred_fallback'})).toEqual([]);
});
