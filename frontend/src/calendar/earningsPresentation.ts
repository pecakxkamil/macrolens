import {getLanguage} from '../i18n/language';
import type {EarningsItem} from './earningsTypes';
export const et=(en:string,pl:string)=>getLanguage()==='pl'?pl:en;
export function earningsAnchor(e:EarningsItem){return e.release.date_status!=='unknown'?e.release:e.call;}
export function earningsDay(e:EarningsItem){const a=earningsAnchor(e);return a.poland_date??a.source_local_date;}
export {earningsSessionLabel as earningsSummary} from './earningsSessionPresentation';
