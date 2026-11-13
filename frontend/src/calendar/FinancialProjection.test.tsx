import {afterEach,expect,it} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import type {CalendarMeasure} from '../api/macrolens';
import {setLanguage} from '../i18n/language';
import {calendarComparison} from './calendarComparisons';
import {ComparisonTooltip} from './ComparisonTooltip';

afterEach(()=>{cleanup();setLanguage('en');});
const make=(sid:string,actual:number,previous:number):CalendarMeasure=>{
 const weekly=sid==='MORTGAGE30US';
 const m={series_id:sid,feature_name:'raw',unit:'percent',frequency:weekly?'weekly':'daily',mapping_status:'confirmed',reference_period:weekly?'2026-11-05':'2026-11-09',previous_period:weekly?'2026-10-29':'2026-11-06',previous_kind:'previous_period',actual,previous,data_version:'current_vintage',previous_data_version:'current_vintage'} as CalendarMeasure;
 m.period_provenance={reference_period:m.reference_period!,previous_period:m.previous_period!,binding_method:'reviewed_financial_table',frequency:m.frequency,publication_confirmed:true,evidence_sha256:'a'.repeat(64),source_url:weekly?'https://www.freddiemac.com/pmms/archive':'https://www.federalreserve.gov/releases/h15/'};
 return m;
};
it.each(['pl','en'] as const)('renders five real comparison directions in %s',language=>{
 setLanguage(language);
 for(const [sid,a,p,direction] of [['DFF',3.88,3.88,'neutral'],['DGS2',4.56,4.51,'positive'],['DGS10',4.88,4.86,'positive'],['DFII10',2.66,2.63,'positive'],['MORTGAGE30US',7.18,7.24,'negative']] as const){
  const comparison=calendarComparison(make(sid,a,p),'previous');expect(comparison?.direction).toBe(direction);if(!comparison)throw new Error('Missing confirmed comparison');
  render(<ComparisonTooltip comparison={comparison} colorByDirection/>);
  expect(screen.getByRole('button').parentElement).toHaveClass(`agenda-comparison--${direction}`);cleanup();
 }
});
it('requires exact publisher proof and never permits generic daily latest pairs',()=>{
 const m=make('DGS2',4.56,4.51);
 expect(calendarComparison({...m,period_provenance:null},'previous')).toBeNull();
 expect(calendarComparison({...m,previous:null},'previous')).toBeNull();
 expect(calendarComparison({...m,previous_data_version:'stored_date_vintage'},'previous')).toBeNull();
 expect(calendarComparison({...m,period_provenance:{...m.period_provenance!,source_url:'https://example.com'}},'previous')).toBeNull();
 expect(calendarComparison({...m,previous_period:'2026-11-08'},'previous')).toBeNull();
});
it('permits an explicitly documented short holiday week only for PMMS',()=>{
 const m=make('MORTGAGE30US',7.18,7.24);m.reference_period='2026-11-25';m.previous_period='2026-11-19';
 m.period_provenance={...m.period_provenance!,reference_period:m.reference_period,previous_period:m.previous_period};
 expect(calendarComparison(m,'previous')?.direction).toBe('negative');
});
