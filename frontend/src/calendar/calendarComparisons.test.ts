import {afterEach,expect,test} from 'vitest';
import type {CalendarMeasure} from '../api/macrolens';
import {setLanguage} from '../i18n/language';
import {calendarComparison} from './calendarComparisons';
import {calendarReadingValue,compactMeasureName,compactPeriod} from './calendarPresentation';
const nfp:CalendarMeasure={series_id:'PAYEMS',label:'NFP',feature_name:'monthly_change',frequency:'monthly',unit:'thousand jobs',reference_period:'2026-09-01',previous_period:'2026-08-01',previous_kind:'previous_period',actual:157,previous:182,forecast:120,consensus_status:'available',data_version:'stored_date_vintage',revision_confirmed:false,binding_method:'alfred_release_date',vintage_date:'2026-10-26',realtime_end:null,result_status:'available',mapping_status:'confirmed',source_url:''};
afterEach(()=>setLanguage('en'));

test.each(['en','pl'] as const)('key calendar publications preserve units and transformations in %s',language=>{
 setLanguage(language);const pl=language==='pl';
 const opening:CalendarMeasure={...nfp,series_id:'JTSJOL',feature_name:'raw',unit:'thousand openings',actual:7079,previous:7335,forecast:null,consensus_status:'not_integrated',data_version:'current_vintage'};
 expect(calendarReadingValue(opening,'actual')).toBe(pl?'7,08\u00a0mln':'7.08\u00a0m');
 expect(calendarReadingValue(opening,'previous')).toBe(pl?'7,34\u00a0mln':'7.34\u00a0m');
 expect(calendarComparison(opening,'previous')?.text).toBe(pl?'\u2212256\u00a0tys.':'\u2212256\u00a0k');
 expect(calendarComparison(opening,'forecast')).toBeNull();
 for(const [sid,feature,actual,previous,shown,delta] of [
  ['RSAFS','mom',.77,1.29,'0.77%','\u22120.52'],
  ['INDPRO','mom',.66,.06,'0.66%','+0.6'],
  ['TCU','raw',76.85,76.42,'76.85%','+0.43'],
  ['PPIFIS','mom',1.34,.47,'1.34%','+0.87'],
  ['ECIALLCIV','qoq',.89,.75,'0.89%','+0.14'],
 ] as const){
  const m={...opening,series_id:sid,feature_name:feature,unit:'percent',actual,previous};
  expect(calendarReadingValue(m,'actual')).toBe(pl?shown.replace('.',','):shown);
  expect(calendarComparison(m,'previous')?.text).toBe((pl?delta.replace('.',','):delta)+'\u00a0'+(pl?'pkt proc.':'pp'));
  expect(calendarComparison({...m,actual:null},'previous')).toBeNull();
 }
 expect(compactMeasureName({...opening,series_id:'ECIALLCIV',feature_name:'qoq'})).toBe(pl?'Indeks koszt\u00f3w zatrudnienia k/k':'Employment cost index QoQ');
});

test.each(['en','pl'] as const)('CFNAI/NFCI consistently use two decimals in %s without changing other measures',language=>{
 setLanguage(language);
 for(const series_id of ['CFNAI','NFCI']){
  const m={...nfp,series_id,feature_name:'raw',unit:'index points',actual:.07,previous:-.08};
  expect(calendarReadingValue(m,'actual')).toBe(language==='en'?'0.07\u00a0pt':'0,07\u00a0pkt');
  expect(calendarComparison(m,'previous')?.text).toBe(language==='en'?'+0.15\u00a0pt':'+0,15\u00a0pkt');
  expect(calendarComparison({...m,actual:.0001,previous:0},'previous')).toMatchObject({text:language==='en'?'0.00\u00a0pt':'0,00\u00a0pkt',tone:'neutral'});
 }
 expect(calendarReadingValue({...nfp,series_id:'OTHER',unit:'index points',actual:.1},'actual')).toBe(language==='en'?'0.1\u00a0pt':'0,1\u00a0pkt');
});

test('Fed name omits the redundant day and M3 stages explain the previous-month comparison',()=>{
 const fed={...nfp,feature_name:'target_range',reference_period:'2026-10-28',frequency:'decision'};
 expect(compactMeasureName(fed)).toBe('Fed decision — interest rates');expect(compactPeriod(fed,'2026-10-28')).toBe('');
 const m={...nfp,series_id:'DGORDER',feature_name:'mom',unit:'percent',period_provenance:{source_url:'https://www.census.gov/manufacturing/m3/release_schedule.html',reference_period:'2026-09-01',binding_method:'official_schedule',estimate_stage:'full'}};
 expect(compactMeasureName(m)).toBe('Durable goods orders MoM — full M3');
 expect(calendarComparison(m,'previous')?.explanation).toContain('previous month, not the advance estimate');
 expect(compactMeasureName({...m,period_provenance:{...m.period_provenance,estimate_stage:'advance'}})).toBe('Durable goods orders MoM — advance');
});
test('NFP uses actual minus consensus and actual minus previous with economic colors',()=>{
 expect(calendarComparison(nfp,'forecast')).toMatchObject({text:'+37\u00a0k',tone:'favorable'});
 expect(calendarComparison(nfp,'previous')).toMatchObject({text:'\u221225\u00a0k',tone:'unfavorable'});
 expect(calendarComparison(nfp,'previous')?.explanation).toContain('smaller');
});
test.each([['UNRATE',4.2,4.1,'unfavorable'],['UNRATE',4,4.1,'favorable'],['ICSA',194000,200000,'favorable'],['ICSA',201000,200000,'unfavorable']])('%s compares direction without reversing the numerical sign', (series,actual,forecast,tone)=>{
 const m={...nfp,series_id:series as string,feature_name:'raw',unit:series==='UNRATE'?'percent':'claims',actual:actual as number,forecast:forecast as number,previous:forecast as number};
 expect(calendarComparison(m,'forecast')?.tone).toBe(tone);expect(calendarComparison(m,'previous')?.tone).toBe(tone);
 expect(calendarComparison(m,'forecast')?.text.startsWith((actual as number)<(forecast as number)?'\u2212':'+')).toBe(true);
});
test('improving negative NFP remains neutral and explains continuing job losses',()=>{
 const comparison=calendarComparison({...nfp,actual:-20,previous:-100},'previous');expect(comparison).toMatchObject({text:'+80\u00a0k',tone:'neutral'});expect(comparison?.explanation).toContain('Employment still fell');
});
test.each(['CPIAUCSL','CPILFESL','PCEPILFE','CES0500000003','DFF','DGS2','DGS10','T10Y2Y','UNKNOWN'])('%s has no automatic better/worse rule',series=>{
 expect(calendarComparison({...nfp,series_id:series,feature_name:'raw',unit:'percent',actual:4.2,previous:4.1},'previous')).toMatchObject({text:'+0.1\u00a0pp',tone:'neutral'});
});
test.each([{forecast:null},{consensus_status:'not_integrated' as const},{actual:null},{actual:NaN},{forecast:Infinity},{reference_period:null},{mapping_status:'reference_period_unconfirmed'},{reference_period:'2026-02-31'},{unit:'percent'}])('unavailable or incompatible consensus never produces a difference: %j',patch=>{
 expect(calendarComparison({...nfp,...patch},'forecast')).toBeNull();
});
test.each([{previous:null},{actual:null},{previous_period:null},{previous_period:'2026-07-01'},{previous_kind:'previous_estimate' as const},{feature_name:'mom',unit:'claims'}])('unconfirmed previous comparison stays absent: %j',patch=>{
 expect(calendarComparison({...nfp,...patch},'previous')).toBeNull();
});
test.each([0,.004,-.004])('equal or invisible difference %s has no negative zero or directional color',delta=>{
 expect(calendarComparison({...nfp,actual:120+delta,forecast:120},'forecast')).toMatchObject({text:'0\u00a0k',tone:'neutral'});
});
test('subtracts full precision before rounding and preserves percent and index difference units',()=>{
 expect(calendarComparison({...nfp,series_id:'CPIAUCSL',feature_name:'mom',unit:'percent',actual:.334848,previous:.289795},'previous')?.text).toBe('+0.05\u00a0pp');
 expect(calendarComparison({...nfp,series_id:'PMI',feature_name:'raw',unit:'index',actual:54.5,previous:54.6},'previous')?.text).toBe('\u22120.1\u00a0pt');
});
test('GDP same-quarter previous estimate and current-vintage caveats stay explicit',()=>{
 const m={...nfp,series_id:'GDPC1',feature_name:'qoq_annualized',frequency:'quarterly',unit:'percent',reference_period:'2026-04-01',previous_period:'2026-04-01',previous_kind:'previous_estimate' as const,actual:2.22,previous:1.48,revision_confirmed:true};
 expect(calendarComparison(m,'previous')).toMatchObject({text:'+0.74\u00a0pp',tone:'neutral'});expect(calendarComparison(m,'previous')?.explanation).toContain('previous estimate of the same quarter');
 expect(calendarComparison({...m,previous_period:'2026-01-01'},'previous')).toBeNull();
 expect(calendarComparison({...m,previous_kind:'previous_period',previous_period:'2026-01-01',data_version:'current_vintage'},'previous')?.explanation).toContain('later revisions');
});
test('Polish signed text and description convey the result without color',()=>{
 setLanguage('pl');const c=calendarComparison(nfp,'previous');expect(c?.text).toBe('\u221225\u00a0tys.');expect(c?.explanation).toContain('mniejszy');
 expect(calendarComparison({...nfp,series_id:'UNRATE',feature_name:'raw',unit:'percent',actual:4.2,forecast:4.1},'forecast')?.text).toBe('+0,1\u00a0pkt proc.');
});


test('FOMC compares only parallel target-bound moves after an official decision',()=>{
 const m:CalendarMeasure={...nfp,series_id:'DFEDTARL/DFEDTARU',feature_name:'target_range',frequency:'decision',unit:'percent',reference_period:'2026-10-28',previous_period:'2026-09-16',previous_kind:'previous_decision',actual:3.5,previous:3.75,actual_range:[3.5,3.75],previous_range:[3.75,4],forecast:null,consensus_status:'not_integrated',data_version:'official_release'};
 expect(calendarComparison(m,'previous')).toMatchObject({text:'\u22120.25\u00a0pp',tone:'neutral'});expect(calendarComparison(m,'previous')?.explanation).toContain('previous decision');
 expect(calendarComparison({...m,actual:null,actual_range:null},'previous')).toBeNull();
 expect(calendarComparison({...m,actual_range:[3.5,4]},'previous')).toBeNull();
});
