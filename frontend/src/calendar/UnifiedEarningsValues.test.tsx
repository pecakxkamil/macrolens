import {afterEach,expect,it} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import {setLanguage} from '../i18n/language';
import type {EarningsItem,FinancialObservation} from './earningsTypes';
import {earningsActual} from './earningsFinancialPresentation';
import {earningsDifference} from './earningsComparison';
import {UnifiedEarningsValues} from './UnifiedEarningsValues';

const observation=(actual:string,metric:'reported_diluted_eps'|'revenue'='reported_diluted_eps')=>({actual,metric,currency:'USD',methodology:metric==='revenue'?'consolidated_revenue':'reported_diluted_total_eps',reporting_standard:'US_GAAP',share_basis:metric==='revenue'?'not_applicable':'common_share'} as FinancialObservation);
const event=(current='1.46',previous='1.38')=>({fiscal_year:2026,fiscal_quarter:3,previous_period:{fiscal_year:2026,fiscal_quarter:2},current_eps_actual:observation(current),previous_eps_actual:observation(previous),current_revenue_actual:observation('13377000000','revenue'),previous_revenue_actual:observation('11536000000','revenue')} as EarningsItem);
afterEach(()=>{cleanup();setLanguage('en');});

it('subtracts API decimals before formatting and scales only the result',()=>{
 expect(earningsDifference(event(),'eps')).toBe('+0.08 USD');
 expect(earningsDifference(event(),'revenue')).toBe('+1.84 bn USD');
 expect(earningsDifference(event('9007199254740993.02','9007199254740993.01'),'eps')).toBe('+0.01 USD');
});
it.each([['0','0','0.00 USD'],['0','0.25','-0.25 USD'],['-0.25','-0.55','+0.30 USD']])('handles zero and loss %s versus %s',(a,b,result)=>{
 expect(earningsDifference(event(a,b),'eps')).toBe(result);
});
it('supports the Q1 fiscal-year rollover',()=>{
 const e=event();e.fiscal_quarter=1;e.previous_period={fiscal_year:2025,fiscal_quarter:4,period_label:'Q4',period_end:null};
 expect(earningsDifference(e,'eps')).toBe('+0.08 USD');
});
it.each(['currency','methodology','reporting_standard','share_basis','unit'] as const)('rejects incompatible %s',key=>{
 const e=event();e.current_eps_actual={...e.current_eps_actual!,unit:'USD/share'};e.previous_eps_actual={...e.previous_eps_actual!,[key]:'incompatible'};
 expect(earningsDifference(e,'eps')).toBe('—');
});
it('normalizes only the existing legacy reported GAAP method',()=>{
 const e=event();e.current_eps_actual!.methodology='gaap_diluted';expect(earningsDifference(e,'eps')).toBe('+0.08 USD');
 e.current_eps_actual!.methodology='gaap_diluted_attributable_to_intel';expect(earningsDifference(e,'eps')).toBe('—');
});
it('rejects another year, missing period and malformed numbers',()=>{
 const e=event();e.previous_period!.fiscal_year=2025;expect(earningsDifference(e,'eps')).toBe('—');
 e.previous_period=null;expect(earningsDifference(e,'eps')).toBe('—');
 const bad=event('NaN');expect(earningsDifference(bad,'eps')).toBe('—');
});
it('preserves explicit null and never substitutes forecasts or older legacy Actual',()=>{
 const e=event();e.current_eps_actual=null;e.reported_eps_actual=observation('9');e.current_eps_forecast=observation('10');
 expect(earningsActual(e,'current_eps')).toBeNull();expect(earningsDifference(e,'eps')).toBe('—');
 e.current_eps_actual=undefined;expect(earningsActual(e,'current_eps')?.actual).toBe('9');
 e.previous_eps_actual=null;expect(earningsDifference(e,'eps')).toBe('—');
});
it.each(['en','pl'] as const)('renders two compact actual and difference lines in %s',language=>{
 setLanguage(language);const e=event();const view=render(<UnifiedEarningsValues event={e} kind="current"/>);
 expect(screen.getByText(language==='pl'?'1,46 USD':'1.46 USD')).toBeInTheDocument();
 expect(screen.getByText(language==='pl'?'13,38 mld USD':'13.38 bn USD')).toBeInTheDocument();
 expect(document.querySelectorAll('.agenda-financial-line')).toHaveLength(2);
 view.rerender(<UnifiedEarningsValues event={e} kind="difference"/>);
 expect(screen.getByText(language==='pl'?'+0,08 USD':'+0.08 USD')).toBeInTheDocument();
 expect(screen.getByText(language==='pl'?'+1,84 mld USD':'+1.84 bn USD')).toBeInTheDocument();
 e.previous_eps_actual=null;view.rerender(<UnifiedEarningsValues event={e} kind="previous"/>);
 expect(screen.getByText('—')).toBeInTheDocument();expect(screen.getByText(language==='pl'?'11,54 mld USD':'11.54 bn USD')).toBeInTheDocument();
});
