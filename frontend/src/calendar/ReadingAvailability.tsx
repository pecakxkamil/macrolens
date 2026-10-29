import type {CalendarCheck,CalendarMeasure,OverviewRefreshState} from '../api/macrolens';
import {availabilityTime,checkStatusLabel} from '../brief/sourceCheckPresentation';
import {formatObservationDate} from '../format';
import {tText,tLabel} from '../i18n/language';

// Source checks describe contact with a provider, not acceptance of a new Actual.
export function ReadingAvailability({measure,check,refresh,revision,now}:{measure:CalendarMeasure;check?:CalendarCheck;refresh?:OverviewRefreshState;revision?:string;now:Date}){
 const source=check?.sources.find(row=>row.resource===`fred:${measure.series_id}`);
 if(!source)return null;
 const scope=source.scope,report=measure.period_provenance?.report_url;
 const documentCheck=report?check?.sources.find(row=>row.resource==='calendar:periods')?.scope?.sources?.find(row=>row.source_url===report):undefined;
 const finished=source.last_finished_at;
 const outcome=refresh?.results.find(row=>row.resource===source.resource);
 const next=refresh?.status!=='running'&&refresh?.next_check_at&&Date.parse(refresh.next_check_at)>+now?refresh.next_check_at:null;
 const version=measure.actual_provenance?.vintage_date;
 return <section aria-label={tLabel('Reading availability')}>
  <strong>{tText('Reading availability')}</strong>
  <p>{measure.series_id}: {tText(checkStatusLabel(source.range_status))}{finished?` · ${availabilityTime(finished)}`:''}</p>
  {outcome?.status==='skipped'?<p>{tText('This refresh skipped the source; no new source check is confirmed.')}</p>:outcome?.status==='cached'?<p>{tText('This refresh reused a stored source check within its cooldown.')}</p>:outcome?.status==='error'?<p>{tText('The source check failed; stored readings are retained.')}</p>:null}
  {outcome?.outcome==='unchanged'?<p>{tText('The last refresh completed without a change to this series.')}</p>:null}
  {source.last_attempt_at&&!finished?<p>{tText('Last source check attempt')}: {availabilityTime(source.last_attempt_at)}</p>:null}
  {source.range_status==='error'?<p>{tText('The source check failed; stored readings are retained.')}</p>:null}
  {scope?.observation_fetch_status==='metadata_unchanged'?<p>{tText('No observations were downloaded because provider metadata was unchanged. This does not prove that the observations endpoint had no newer period.')}</p>:scope?.observation_fetch_status==='fetched'||scope?.observations_received!==undefined?<p>{tText('Observations downloaded; this alone does not confirm Actual for the expected period.')}</p>:null}
  {scope?.observation_end?<p>{tText('Latest period reported by provider metadata')}: {formatObservationDate(scope.observation_end,measure.frequency)}</p>:null}
  {measure.reference_period?<p>{tText('Expected report period')}: {formatObservationDate(measure.reference_period,measure.frequency)}</p>:null}
  {scope?.last_updated?<p>{tText('Provider update timestamp')}: {scope.last_updated}</p>:null}
  {documentCheck?.status==='error'?<p>{tText('The official result document could not be validated; a source check does not confirm its publication stage.')}</p>:report&&!measure.result_provenance?<p>{tText('No confirmed result document is stored.')}</p>:null}
  {measure.actual===null?<p>{tText('Actual has not been confirmed for this reading. See the missing-value reason below.')}</p>:<>
   <p>{tText('Actual is available in the displayed data; a source check time is not its first publication time.')}</p>
   {revision?<p>{tText('Displayed data generation')}: <span title={revision}>{revision.slice(0,8)}</span>{refresh?.publication_id===revision&&refresh.completed_at&&(refresh.status==='complete'||refresh.status==='partial')?` · ${tText('Generation published')}: ${availabilityTime(refresh.completed_at)}`:''}</p>:null}
  </>}
  {measure.data_version==='current_vintage'?<p>{tText('Current-vintage value')}{typeof version==='string'?` · ${tText('Vintage date')}: ${version}`:''}</p>:null}
  {next?<p>{tText('Next permitted source check')}: {availabilityTime(next)}</p>:null}
 </section>;
}
