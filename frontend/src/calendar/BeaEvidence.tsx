import type {CalendarCheck,CalendarMeasure} from '../api/macrolens';
import {tText} from '../i18n/language';
import {calendarReadingValue} from './calendarPresentation';

export function BeaEvidence({measure:m,check}:{measure:CalendarMeasure;check?:CalendarCheck}){
 if(!m.selected_source)return null;
 if(m.selected_source!=='bea_official')return <p>{tText('FRED fallback: no matching direct BEA value is confirmed for this report.')}</p>;
 const p=m.actual_provenance,source=check?.sources.find(s=>s.resource==='bea:reports');
 return <section aria-label={tText('Official BEA reading')}>
 <strong>{tText('Official BEA reading')}: {calendarReadingValue(m,'actual')}</strong>
 <p>{tText('Source: U.S. Bureau of Economic Analysis')} · {String(p?.original_title??'')} · {String(p?.estimate_stage??'monthly')}</p>
 <p>{tText('Published precision: one decimal. This is the published rate, not a calculation from FRED levels.')}</p>
 <p>{tText('Captured document snapshot; not proof of the first print or first availability time.')}</p>
 {m.annual_context_source==='fred'?<p>{tText('The annual context shown alongside this monthly reading comes separately from FRED current-vintage data.')}</p>:null}
 <p>{tText('Retrieved')}: {String(p?.retrieved_at??'')} · {tText('Document hash')}: {String(p?.raw_hash??'')}</p>
 <p>{tText('Official publication')}: {String(p?.document_published_at??'')}</p>
 {m.comparison_status==='mixed_sources'?<p>{tText('Previous is a separate FRED current-vintage fallback. A difference across these sources is not calculated.')}</p>:m.comparison_status==='previous_unavailable'?<p>{tText('Previous is not available in this BEA document.')}</p>:<p>{tText('Previous is the preceding period in the same BEA document.')}</p>}
 {m.fred_alternative?.actual!==null&&m.fred_alternative?.actual!==undefined?<p>{tText('Separate FRED alternative')}: {m.fred_alternative.actual}% · {tText(m.source_comparison==='conflict'?'Source conflict: FRED differs beyond published rounding. BEA remains the displayed Actual.':'FRED agrees within published rounding.')} <a href={`https://fred.stlouisfed.org/series/${m.series_id}`} target="_blank" rel="noreferrer">FRED</a></p>:null}
 {source&&(source.range_status==='error'||source.range_status==='partial')?<p>{tText('The BEA source check is incomplete; the last validated reading is retained.')}</p>:null}
 <p><a href={m.source_url} target="_blank" rel="noreferrer">{tText('Official event document')}</a>{' · '}<a href={m.usage_rights?.terms_url} target="_blank" rel="noreferrer">{tText('BEA data use policy')}</a></p>
 <p>{tText('BEA attribution is retained. MacroLens normalizes periods and compares published rounded rates; no BEA endorsement is implied. Public-domain policy has exceptions.')}</p>
 </section>;
}
