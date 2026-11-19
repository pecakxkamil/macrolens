import {afterEach,expect,test} from 'vitest';
import {usdInterpretation,usdInflationInterpretation,fedUsdDecisionMarkers} from './usdInterpretation';
import {prepareReading} from './readingComparisons';
import {prepareFedTarget} from './fedTarget';
import type {OverviewReadingComparison} from '../api/macrolens';
import {setLanguage} from '../i18n/language';
afterEach(()=>setLanguage('en'));
function reading(key:string,feature:string,current:number,previous:number|null){
 const point=(value:number)=>({value,observation_date:'2026-09-01',feature_as_of_date:null});
 return prepareReading(key,'TEST',{component:key,feature_name:feature,unit:'percent',frequency:'monthly',current:point(current),previous:previous===null?null:point(previous),change:previous===null?null:current-previous} as OverviewReadingComparison);
}
test.each([
 ['headline_cpi','mom',.35,.65,'−'],['core_cpi','mom',.30,.33,'−'],['producer_ppi','mom',.35,1.41,'−'],
 ['unemployment','level',4.1,4.2,'+'],['initial_claims','raw',200000,191000,'−'],
 ['payrolls','monthly_change',165,60,'+'],['payrolls','monthly_change',29,133,'−'],
 ['services_pmi','raw',54.5,54.9,'−'],['real_gdp','qoq_annualized',3.4,2.2,'+'],
 ['real_consumption','mom',0,.5,'−'],['industrial_production','mom',-.43,.73,'−'],
 ['average_hourly_earnings','mom',.37,.26,'+'],['job_openings','level',7523,7190,'+'],
 ['mortgage_rate','level',7.11,7.18,'±'],['nfci','level',-.46,-.47,'±'],['yield_curve_2s10s','spread',.27,.24,'±']
])('USD direction: %s', (key,feature,current,previous,symbol)=>{
 const row=reading(key,feature,current as number,previous as number),arrow=row.arrow;
 expect(usdInterpretation(row)?.symbol).toBe(symbol);expect(row.arrow).toBe(arrow);
 expect(usdInterpretation(row)?.reason).toContain('USD');
 expect(usdInterpretation(row)?.reason).not.toContain('excludes market consensus');
});
test('annual CPI follows the USD rate-expectations channel, not price stability',()=>{
 expect(usdInflationInterpretation(3.7,3.4)?.symbol).toBe('+');expect(usdInflationInterpretation(3.4,3.7)?.symbol).toBe('−');
 expect(usdInflationInterpretation(3.7,3.4)?.reason).toContain('dollar investments');
});
test('missing, equal, wrong-definition and non-finite comparisons have no marker',()=>{
 expect(usdInterpretation(reading('core_pce','mom',.3,.3))).toBeNull();
 expect(usdInterpretation(reading('payrolls','monthly_change',165,null))).toBeNull();
 expect(usdInterpretation(reading('headline_cpi','level',.4,.3))).toBeNull();
 expect(usdInflationInterpretation(NaN,3)).toBeNull();
});
test('Polish tooltip explains the specific USD mechanism naturally',()=>{
 setLanguage('pl');const note=usdInflationInterpretation(3.7,3.4)!;
 expect(note.label).toContain('USD');expect(note.reason).toContain('inwestycji w dolarach');
 expect(note.reason).not.toContain('kanał stóp');
});
test('Fed absent decision does not invent a USD impulse',()=>expect(fedUsdDecisionMarkers(prepareFedTarget(undefined))).toBeNull());
