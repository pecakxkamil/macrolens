import type {CalendarEvent,CalendarMeasure} from '../api/macrolens';
import type {EarningsItem} from './earningsTypes';
import {earningsActual} from './earningsFinancialPresentation';
import {et} from './earningsPresentation';

export function MissingValue({reason}:{reason:string}){
 return <span className="missing-value" role="img" aria-label={reason} title={reason}>—</span>;
}

export function macroMissingReason(event:CalendarEvent,measure:CalendarMeasure|undefined,kind:'actual'|'previous'|'forecast'|'difference'){
 if(event.expects_numeric_result===false)return et('A numerical reading does not apply to this event.','Odczyt liczbowy nie dotyczy tego wydarzenia.');
 if(kind==='forecast')return et('No comparable forecast for this measure and period.','Brak porównywalnej prognozy dla tej miary i okresu.');
 if(kind==='difference'){
  if(measure?.actual==null)return macroMissingReason(event,measure,'actual');
  if(measure.previous==null)return macroMissingReason(event,measure,'previous');
  return et('The readings do not form a comparable pair.','Odczyty nie tworzą porównywalnej pary.');
 }
 if(!measure)return et('No verified numerical reading for this event.','Brak zweryfikowanego odczytu liczbowego dla tego wydarzenia.');
 const reason=measure?.missing_reason?.[kind];
 if(kind==='actual'&&reason==='publisher_base_unavailable'&&measure.selected_source==='bls:cpi'&&measure.cpi_missing_proof&&measure.cpi_missing_base_period)return et(`Year-over-year reading unavailable: missing base data for ${measure.cpi_missing_base_period.slice(0,7)}.`,`Odczyt r/r niedostępny: brak danych bazowych za ${measure.cpi_missing_base_period.slice(0,7)}.`);
 if(reason==='reference_period_unconfirmed'||measure?.mapping_status!=='confirmed')return et('The reference period has not been confirmed.','Okres odczytu nie został potwierdzony.');
 if(kind==='actual'&&(reason==='not_yet_published'||measure?.result_status==='scheduled'))return et('Awaiting publication.','Oczekiwanie na publikację.');
 if(kind==='previous')return et('No verified previous reading for this measure and period.','Brak zweryfikowanego poprzedniego odczytu tej miary i okresu.');
 return et('No verified reading for this period.','Brak zweryfikowanego odczytu dla tego okresu.');
}

export function earningsMissingReason(event:EarningsItem,metric:'eps'|'revenue',kind:'current'|'previous'|'difference'|'forecast'){
 if(kind==='forecast')return et('No comparable forecast for this metric and fiscal period.','Brak porównywalnej prognozy dla tej metryki i okresu fiskalnego.');
 if(kind==='difference'){
  if(!earningsActual(event,`current_${metric}`))return earningsMissingReason(event,metric,'current');
  if(!earningsActual(event,`previous_${metric}`))return earningsMissingReason(event,metric,'previous');
  return et('Current and Previous do not form a comparable pair.','Current i Previous nie tworzą porównywalnej pary.');
 }
 if(event.financial_store_status==='not_activated')return et('Financial data are not activated in this database.','Dane finansowe nie są aktywne w tej bazie.');
 if(kind==='previous')return event.previous_period
  ?et(`No comparable previous ${metric==='eps'?'EPS':'revenue'} for this quarter.`,`Brak porównywalnych ${metric==='eps'?'danych EPS':'przychodów'} z poprzedniego kwartału.`)
  :et('No verified previous report in the application.','Brak zweryfikowanego poprzedniego raportu w aplikacji.');
 const state=event.publication_state?.code;
 if(state==='scheduled')return et('Awaiting publication.','Oczekiwanie na publikację.');
 if(state==='date_passed_unconfirmed'||state==='unconfirmed')return et('The earnings release has not been confirmed.','Publikacja wyników nie została potwierdzona.');
 return et(`No verified current ${metric==='eps'?'EPS':'revenue'}.`,`Brak zweryfikowanych bieżących ${metric==='eps'?'danych EPS':'przychodów'}.`);
}
