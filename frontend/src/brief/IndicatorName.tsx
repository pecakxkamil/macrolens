import type {ReactNode} from 'react';

export function IndicatorName({href,label,fullLabel=label,period,children}:{href:string;label:string;fullLabel?:string;period:ReactNode;children:ReactNode}){
 return <span className="overview-indicator-name">
  <a className="overview-name-link" href={href} title={fullLabel} aria-label={fullLabel}>{label}</a>
  <span className="overview-indicator-meta">{period}{children}</span>
 </span>;
}
