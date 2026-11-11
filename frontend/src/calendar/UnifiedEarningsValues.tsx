import type {EarningsItem} from './earningsTypes';
import {earningsActual,financialValue} from './earningsFinancialPresentation';
import {earningsChange} from './earningsComparison';
import {et} from './earningsPresentation';
import {MissingValue,earningsMissingReason} from './MissingValue';

export function UnifiedEarningsValues({event,kind}:{event:EarningsItem;kind:'current'|'previous'|'difference'}){
 return <div className="agenda-financials">{(['eps','revenue'] as const).map(metric=>{
 const change=kind==='difference'?earningsChange(event,metric):null;
 const text=change?change.text:financialValue(earningsActual(event,`${kind==='previous'?'previous':'current'}_${metric}`));
 return <div className={`agenda-financial-line${change?' agenda-financial-line--'+change.direction:''}`} key={metric}>
  <span className="agenda-financial-label">{metric==='eps'?'EPS':et('Rev.','Przych.')}</span>
  <span data-financial-metric={metric}>{text==='—'?<MissingValue reason={earningsMissingReason(event,metric,kind)}/>:text}</span>
 </div>;})}</div>;
}
