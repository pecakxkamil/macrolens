import {getLanguage} from '../i18n/language';
import type {ForecastDetail} from '../api/macrolens';

export function ForecastValue({forecast,unit,currency}:{forecast:ForecastDetail;unit?:string;currency?:string}){
 const pl=getLanguage()==='pl';
 const kind=({consensus:pl?'Konsensus':'Consensus',model_nowcast:'Nowcast',issuer_guidance:'Guidance'})[forecast.kind];
 const format=(value:string)=>{
  const n=Number(value);if(!Number.isFinite(n))return '—';
  const divisor=currency&&Math.abs(n)>=1e9?1e9:currency&&Math.abs(n)>=1e6?1e6:1;
  return new Intl.NumberFormat(pl?'pl-PL':'en-US',{maximumFractionDigits:6}).format(n/divisor)+(divisor===1e9?(pl?' mld':' bn'):divisor===1e6?(pl?' mln':' m'):'')+(currency?' '+currency:unit==='percent'?'%':'');
 };
 const range=()=>{
  const low=format(forecast.low!),high=format(forecast.high!);
  const suffix=high.match(/(?: (?:bn|mld|m|mln))? (?:USD|EUR|TWD)$/)?.[0];
  return suffix&&low.endsWith(suffix)?`${low.slice(0,-suffix.length)}\u2013${high}`:`${low}\u2013${high}`;
 };
 const value=forecast.low!==null&&forecast.high!==null?range():forecast.value!==null?format(forecast.value):'\u2014';
 if(value==='—')return <>—</>;
 return <a href={forecast.source_url.startsWith('https://')?forecast.source_url:undefined} target="_blank" rel="noreferrer" title={`${kind} · ${forecast.methodology}${forecast.state==='frozen'?(pl?' · zapis przed publikacją':' · pre-release snapshot'):''}`}><small>{value} · {kind}</small></a>;
}
