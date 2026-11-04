import {getLanguage} from '../i18n/language';
import type {EarningsItem} from './earningsTypes';

/** USD remains an exact decimal string; round only the displayed billions. */
export function marketCap(e:EarningsItem):{value:string;date:string;provider?:string;source?:string}|null {
 if(e.market_cap_status!=='verified_snapshot'||!e.market_cap_usd||!e.market_cap_as_of)return null;
 if(!/^\d+(\.\d+)?$/.test(e.market_cap_usd)||!/^\d{4}-\d{2}-\d{2}$/.test(e.market_cap_as_of))return null;
 const instant=new Date(e.market_cap_as_of+'T00:00:00Z');
 if(!Number.isFinite(instant.getTime())||instant.toISOString().slice(0,10)!==e.market_cap_as_of)return null;
 const [integer,fraction='']=e.market_cap_usd.split('.');
 if(BigInt(integer)===0n&&!/[1-9]/.test(fraction))return null;
 const language=getLanguage()==='pl'?'pl-PL':'en-US',polish=language==='pl-PL';
 const dollars=BigInt(integer),hundredths=(dollars+5000000n)/10000000n;
 const whole=polish?String(hundredths/100n).replace(/\B(?=(\d{3})+(?!\d))/g,'\u00a0'):new Intl.NumberFormat(language).format(hundredths/100n);
 const decimals=String(hundredths%100n).padStart(2,'0').replace(/0+$/,'');
 const number=hundredths===0n?(polish?'< 0,01':'< 0.01'):whole+(decimals?(polish?',':'.')+decimals:'');
 const sources={TGMCharts:'https://tgmcharts.com',DeltaScreener:'https://deltascreener.com/data'};
 const provider=e.market_cap_provider,source=provider&&sources[provider]===e.market_cap_source?sources[provider]:undefined;
 return {value:number+(polish?' mld USD':' bn USD'),date:new Intl.DateTimeFormat(language,{day:'2-digit',month:'2-digit',year:'numeric',timeZone:'UTC'}).format(instant),provider:source?provider:undefined,source};
}
