import {afterEach,expect,it} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import type {CalendarMeasure} from '../api/macrolens';
import type {EarningsItem,FinancialObservation} from './earningsTypes';
import {changeDirection} from './changeDirection';
import {calendarComparison} from './calendarComparisons';
import {ComparisonTooltip} from './ComparisonTooltip';
import {UnifiedEarningsValues} from './UnifiedEarningsValues';
import {setLanguage} from '../i18n/language';

afterEach(()=>{cleanup();setLanguage('en');});
it.each([[1,'positive'],[-1,'negative'],[0,'neutral'],[-0,'neutral'],[1n,'positive'],[-1n,'negative'],[0n,'neutral'],[null,'neutral'],[undefined,'neutral'],[NaN,'neutral'],[Infinity,'neutral']] as const)('classifies %s numerically',(value,result)=>{
 expect(changeDirection(value)).toBe(result);
});
const measure={series_id:'ICSA',feature_name:'raw',unit:'claims',mapping_status:'confirmed',reference_period:'2026-11-07',previous_period:'2026-10-31',previous_kind:'previous_period',frequency:'weekly',actual:201000,previous:200000} as CalendarMeasure;
it.each(['en','pl'] as const)('uses numerical direction for claims only when requested in %s',language=>{
 setLanguage(language);const higher=calendarComparison(measure,'previous')!;
 expect(higher.tone).toBe('unfavorable');expect(higher.direction).toBe('positive');
 const view=render(<ComparisonTooltip comparison={higher} colorByDirection/>);
 expect(screen.getByRole('button').parentElement).toHaveClass('agenda-comparison--positive');
 view.rerender(<ComparisonTooltip comparison={higher}/>);
 expect(screen.getByRole('button').parentElement).toHaveClass('agenda-comparison--unfavorable');
 const lower=calendarComparison({...measure,actual:199000},'previous')!;
 expect(lower.tone).toBe('favorable');view.rerender(<ComparisonTooltip comparison={lower} colorByDirection/>);
 expect(screen.getByRole('button').parentElement).toHaveClass('agenda-comparison--negative');
 const equal=calendarComparison({...measure,actual:200000},'previous')!;
 view.rerender(<ComparisonTooltip comparison={equal} colorByDirection/>);
 expect(screen.getByRole('button').parentElement).toHaveClass('agenda-comparison--neutral');
 expect(calendarComparison({...measure,actual:null},'previous')).toBeNull();
});
const observation=(actual:string,metric:'reported_diluted_eps'|'revenue')=>({actual,metric,currency:'USD',reporting_standard:'US_GAAP',methodology:metric==='revenue'?'consolidated_revenue':'reported_diluted_total_eps'} as FinancialObservation);
it.each(['en','pl'] as const)('colors EPS and revenue independently and preserves null in %s',language=>{
 setLanguage(language);
 const event={fiscal_year:2026,fiscal_quarter:3,previous_period:{fiscal_year:2026,fiscal_quarter:2},current_eps_actual:observation('0.12','reported_diluted_eps'),previous_eps_actual:observation('0.25','reported_diluted_eps'),current_revenue_actual:observation('1443000000','revenue'),previous_revenue_actual:observation('1289000000','revenue')} as EarningsItem;
 const view=render(<UnifiedEarningsValues event={event} kind="difference"/>);
 const line=(metric:string)=>document.querySelector(`[data-financial-metric="${metric}"]`)!.parentElement!;
 expect(line('eps')).toHaveClass('agenda-financial-line--negative');expect(line('revenue')).toHaveClass('agenda-financial-line--positive');
 event.current_eps_actual=observation('0.50','reported_diluted_eps');event.current_revenue_actual=observation('1200000000','revenue');view.rerender(<UnifiedEarningsValues event={event} kind="difference"/>);
 expect(line('eps')).toHaveClass('agenda-financial-line--positive');expect(line('revenue')).toHaveClass('agenda-financial-line--negative');
 event.previous_eps_actual=null;event.current_revenue_actual=event.previous_revenue_actual;view.rerender(<UnifiedEarningsValues event={event} kind="difference"/>);
 expect(line('eps')).toHaveClass('agenda-financial-line--neutral');expect(line('eps')).toHaveTextContent('—');expect(line('revenue')).toHaveClass('agenda-financial-line--neutral');
 view.rerender(<UnifiedEarningsValues event={event} kind="current"/>);
 expect(document.querySelector('[class*="agenda-financial-line--"]')).toBeNull();
});
