import type {EarningsItem,FinancialObservation} from './earningsTypes';
import {earningsActual,financialValue} from './earningsFinancialPresentation';
import {changeDirection,type ChangeDirection} from './changeDirection';

function decimal(value:string){
 const match=/^([+-]?)(\d+)(?:\.(\d+))?$/.exec(value);
 if(!match)return null;
 const fraction=match[3]??'';
 return {integer:BigInt((match[1]==='-'?'-':'')+match[2]+fraction),scale:fraction.length};
}
const method=(value:FinancialObservation)=>value.methodology==='gaap_diluted'?'reported_diluted_total_eps':value.methodology;

/** Arithmetic quarter-on-quarter change; not a forecast surprise or a rating. */
export function earningsChange(e:EarningsItem,metric:'eps'|'revenue'):{text:string;direction:ChangeDirection} {
 const unavailable={text:'—',direction:'neutral' as const};
 const current=earningsActual(e,`current_${metric}`),previous=earningsActual(e,`previous_${metric}`),period=e.previous_period;
 const year=e.fiscal_quarter===1?e.fiscal_year-1:e.fiscal_year,quarter=e.fiscal_quarter===1?4:e.fiscal_quarter-1;
 if(!current||!previous||!period||period.fiscal_year!==year||period.fiscal_quarter!==quarter)return unavailable;
 // E2E history carries canonical actual amounts but omits the optional unit
 // label. Source scaling is already applied by the shared backend reader.
 if(current.currency!==previous.currency||(current.unit&&previous.unit&&current.unit!==previous.unit)||method(current)!==method(previous))return unavailable;
 if(current.reporting_standard&&previous.reporting_standard&&current.reporting_standard!==previous.reporting_standard)return unavailable;
 if(current.share_basis&&previous.share_basis&&current.share_basis!==previous.share_basis)return unavailable;
 const a=decimal(current.actual),b=decimal(previous.actual);if(!a||!b)return unavailable;
 const scale=Math.max(a.scale,b.scale),difference=a.integer*10n**BigInt(scale-a.scale)-b.integer*10n**BigInt(scale-b.scale);
 const digits=(difference<0n?-difference:difference).toString().padStart(scale+1,'0');
 const actual=(difference<0n?'-':'')+(scale?digits.slice(0,-scale)+'.'+digits.slice(-scale):digits);
 return {text:(difference>0n?'+':'')+financialValue({...current,actual}),direction:changeDirection(difference)};
}

export function earningsDifference(e:EarningsItem,metric:'eps'|'revenue'):string {
 return earningsChange(e,metric).text;
}
