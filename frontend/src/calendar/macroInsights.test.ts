import {afterEach,expect,it} from 'vitest';
import type {CalendarEvent,CalendarMeasure} from '../api/macrolens';
import {setLanguage} from '../i18n/language';
import {macroFamily} from './macroInsightFamilies';
import {macroInsight,insightWarnings} from './macroInsight';
import {comparableTrend,trendGeometry,trendRequest} from './macroTrendData';

const event={release_date:'2026-11-03',event_type:undefined} as CalendarEvent;
const measure:CalendarMeasure={series_id:'JTSJOL',label:'JOLTS',feature_name:'raw',frequency:'monthly',unit:'thousand openings',reference_period:'2026-09-01',previous_period:'2026-08-01',previous_kind:'previous_period',actual:7523,previous:7190,forecast:null,consensus_status:'not_integrated',data_version:'current_vintage',revision_confirmed:false,binding_method:'test',vintage_date:null,realtime_end:null,result_status:'available',mapping_status:'confirmed',source_url:'https://fred.stlouisfed.org/series/JTSJOL'};
afterEach(()=>setLanguage('en'));
it.each(['en','pl'] as const)('interprets the actual selected measure in %s',language=>{
 setLanguage(language);const text=macroInsight(event,measure)!;
 expect(text).toContain('333');expect(text).toContain(language==='pl'?'wzrosła':'rose');
 expect(macroInsight(event,{...measure,actual:6800})).toContain(language==='pl'?'spadła':'fell');
 expect(macroInsight(event,{...measure,actual:7190})).toContain(language==='pl'?'nie zmieniła':'unchanged');
 expect(macroInsight(event,{...measure,actual:null})).toBeNull();
 expect(macroInsight(event,{...measure,previous:null})).toContain(language==='pl'?'Brak porównywalnego':'No comparable');
 expect(macroInsight(event,{...measure,previous_period:'2025-09-01'})).toContain(language==='pl'?'Brak porównywalnego':'No comparable');
});
it.each([
 ['PAYEMS','monthly_change','nfp'],['UNRATE','raw','unemployment'],['CPIAUCSL','mom','cpi'],['CPILFESL','yoy','core_cpi'],['PCEPI','mom','pce'],['PCEPILFE','yoy','core_pce'],['ISM_MANUFACTURING_PMI','raw','manufacturing'],['ISM_SERVICES_PMI','raw','services'],['ICSA','raw','initial_claims'],['CCSA','raw','continuing_claims'],['GDPC1','qoq_annualized','gdp'],['RSAFS','mom','retail'],['RSFSXMV','mom','retail_ex_autos'],['RETAIL_CONTROL','mom','retail_control'],
])('uses a reviewed identity for %s %s',(series_id,feature_name,id)=>{
 const weekly=['ICSA','CCSA'].includes(series_id),pmi=series_id.startsWith('ISM_');
 const frequency=weekly?'weekly':series_id==='GDPC1'?'quarterly':'monthly';
 const unit=weekly?'claims':pmi?'index points':series_id==='PAYEMS'?'thousand jobs':'percent';
 expect(macroFamily(event,{...measure,series_id,feature_name,frequency,unit})?.id).toBe(id);
});
it('does not apply a monthly family template to a quarterly measure',()=>{
 const wrong={...measure,frequency:'quarterly',previous_period:'2026-06-01'};
 expect(macroFamily(event,wrong)).toBeUndefined();expect(macroInsight(event,wrong)).not.toContain('preceding month');
});
it('does not guess families from names or unknown transforms',()=>{
 expect(macroFamily(event,{...measure,series_id:'UNKNOWN',label:'CPI Core GDP JOLTS'})).toBeUndefined();
 expect(macroFamily(event,{...measure,feature_name:'yoy'})).toBeUndefined();
 expect(macroFamily({...event,event_type:'adp_monthly'})?.id).toBe('adp');
 expect(macroFamily({...event,event_type:'fomc_decision'},{...measure,feature_name:'target_range'})?.id).toBe('fomc');
});
it('preserves negative values, same-quarter GDP estimates and PMI thresholds',()=>{
 const gdp={...measure,series_id:'GDPC1',feature_name:'qoq_annualized',frequency:'quarterly',unit:'percent',reference_period:'2026-07-01',previous_period:'2026-07-01',previous_kind:'previous_estimate' as const,actual:-.5,previous:-1};
 expect(macroInsight(event,gdp)).toContain('-0.50%');expect(macroInsight(event,gdp)).toContain('same quarter');
 expect(macroInsight(event,{...gdp,previous_period:'2026-04-01'})).toContain('No comparable');
 expect(macroInsight(event,{...measure,series_id:'ISM_SERVICES_PMI',unit:'index points',actual:49,previous:51})).toContain('below 50');
 expect(macroInsight(event,{...measure,series_id:'ISM_MANUFACTURING_PMI',unit:'index points',actual:52,previous:51})).toContain('above 50');
 expect(macroInsight(event,{...measure,series_id:'ISM_MANUFACTURING_PMI',unit:'index points',actual:50,previous:51})).toContain('at 50');
});
it('does not interpret incompatible units or mixed-source comparisons',()=>{
 expect(macroInsight(event,{...measure,series_id:'CPIAUCSL',feature_name:'mom',unit:'index'})).toContain('No comparable');
 expect(macroInsight(event,{...measure,comparison_status:'mixed_sources'})).toContain('No comparable');
 expect(insightWarnings(event,{...measure,source_comparison:'conflict'}).join(' ')).toContain('disagree');
 expect(insightWarnings(event,measure).join(' ')).toContain('revisions');
});
function history(){return {series_id:'JTSJOL',frequency:'monthly',unit:'thousands',history_type:'current_vintage',observations:[{observation_date:'2026-03-01',value:-1},{observation_date:'2026-01-01',value:2},{observation_date:'2026-04-01',value:0}]};}
it('orders real periods, keeps negative values and gaps, and requires at least three points',()=>{
 const result=comparableTrend(measure,history());expect(result.map(p=>p.period)).toEqual(['2026-01-01','2026-03-01','2026-04-01']);
 const geometry=trendGeometry(result,'monthly');expect(geometry.path.match(/M/g)).toHaveLength(2);expect(geometry.path).not.toContain('NaN');
 expect(result[1].value).toBe(-1);expect(comparableTrend(measure,{...history(),observations:history().observations.slice(1)})).toEqual([]);
});
it.each([{series_id:'OTHER'},{frequency:'quarterly'},{unit:'percent'},{history_type:'point_in_time'},{feature_name:'mom'}])('rejects mismatched history metadata %j',patch=>{
 expect(comparableTrend(measure,{...history(),...patch})).toEqual([]);
});
it('limits history to 12 points and refuses conflicting duplicate periods',()=>{
 const data=history();data.observations=Array.from({length:15},(_,i)=>({observation_date:new Date(Date.UTC(2025,6+i,1)).toISOString().slice(0,10),value:i}));
 expect(comparableTrend(measure,data)).toHaveLength(12);
 const bad=history();bad.observations.push({observation_date:'2026-01-01',value:10});expect(comparableTrend(measure,bad)).toEqual([]);
 expect(trendRequest({...measure,actual:null})).toBeNull();expect(trendRequest({...measure,seasonal_adjustment:'Not Seasonally Adjusted'})).toBeNull();
});
it('checks feature methodology and uses a single reviewed ISM document',()=>{
 const cpi={...measure,series_id:'CPIAUCSL',feature_name:'mom',unit:'percent'};
 expect(comparableTrend(cpi,{...history(),series_id:'CPIAUCSL',unit:'index',feature_name:'mom',methodology_version:'v1'})).toHaveLength(3);
 expect(comparableTrend(cpi,{...history(),series_id:'CPIAUCSL',unit:'index',feature_name:'yoy',methodology_version:'v1'})).toEqual([]);
 const ism={...measure,series_id:'ISM_MANUFACTURING_PMI',unit:'index points',actual_provenance:{raw_hash:'reviewed'}};
 const rows=history().observations.map(p=>({...p,raw_hash:'reviewed'}));rows.push({...rows[0],observation_date:'2026-02-01',raw_hash:'other'});
 expect(comparableTrend(ism,{...history(),series_id:ism.series_id,unit:'index',source:'ism',observations:rows})).toHaveLength(3);
 expect(trendRequest({...ism,actual_provenance:{}})).toBeNull();
});
