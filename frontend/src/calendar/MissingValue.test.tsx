import {afterEach,expect,it} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import type {CalendarEvent,CalendarMeasure} from '../api/macrolens';
import type {EarningsItem} from './earningsTypes';
import {setLanguage} from '../i18n/language';
import {MissingValue,macroMissingReason,earningsMissingReason} from './MissingValue';
import {UnifiedEarningsValues} from './UnifiedEarningsValues';

afterEach(()=>{cleanup();setLanguage('en');});
const event={} as CalendarEvent;
const measure={mapping_status:'confirmed',actual:null,previous:null,result_status:'scheduled',missing_reason:{actual:'not_yet_published',previous:null}} as CalendarMeasure;
it.each(['en','pl'] as const)('exposes truthful missing-value reasons in %s',language=>{
 setLanguage(language);
 const reason=macroMissingReason(event,measure,'actual');render(<MissingValue reason={reason}/>);
 expect(screen.getByRole('img',{name:reason})).toHaveAttribute('title',reason);
 expect(screen.getByRole('img')).toHaveTextContent('—');
 expect(reason).toContain(language==='pl'?'Oczekiwanie':'Awaiting');
 expect(macroMissingReason(event,{...measure,mapping_status:'reference_period_unconfirmed'},'actual')).toContain(language==='pl'?'Okres':'period');
 expect(macroMissingReason(event,measure,'previous')).toContain(language==='pl'?'poprzedniego':'previous');
 expect(macroMissingReason(event,measure,'forecast')).toContain(language==='pl'?'prognozy':'forecast');
 expect(macroMissingReason({expects_numeric_result:false} as CalendarEvent,undefined,'actual')).toContain(language==='pl'?'nie dotyczy':'does not apply');
});
it('distinguishes scheduled, unconfirmed and missing history without inventing a split or source report',()=>{
 const e={publication_state:{code:'scheduled'}} as EarningsItem;
 expect(earningsMissingReason(e,'eps','current')).toBe('Awaiting publication.');
 expect(earningsMissingReason({...e,publication_state:{...e.publication_state!,code:'date_passed_unconfirmed'}},'eps','current')).toContain('not been confirmed');
 expect(earningsMissingReason(e,'eps','previous')).toContain('No verified previous report');
 const partial={...e,ticker:'CRWD',previous_period:{fiscal_year:2026,fiscal_quarter:2,period_label:'Q2 2026',period_end:null}};
 expect(earningsMissingReason(partial,'eps','previous')).toContain('No comparable previous EPS');
 expect(earningsMissingReason(partial,'eps','previous')).not.toMatch(/split|pro forma/i);
});
it('keeps zero as a value and adds a reason only to the missing metric',()=>{
 const e={current_eps_actual:{actual:'0',metric:'reported_diluted_eps',currency:'USD'},current_revenue_actual:null} as EarningsItem;
 render(<UnifiedEarningsValues event={e} kind="current"/>);
 expect(document.querySelector('[data-financial-metric="eps"]')).toHaveTextContent('0.00 USD');
 expect(document.querySelector('[data-financial-metric="eps"] .missing-value')).toBeNull();
 expect(document.querySelector('[data-financial-metric="revenue"] .missing-value')).toHaveAttribute('title','No verified current revenue.');
});
