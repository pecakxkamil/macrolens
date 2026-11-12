import type {CalendarEvent,CalendarMeasure} from '../api/macrolens';
import {calendarComparison} from './calendarComparisons';
import {calendarReadingValue} from './calendarPresentation';
import {et} from './earningsPresentation';
import {macroFamily,familyText} from './macroInsightFamilies';

export function macroInsight(event:CalendarEvent,measure?:CalendarMeasure):string|null {
 if(!measure||measure.actual===null||!Number.isFinite(measure.actual))return null;
 const comparison=calendarComparison(measure,'previous'),family=macroFamily(event,measure);
 if(!comparison)return et('No comparable previous reading is available; no change is inferred.','Brak porównywalnego poprzedniego odczytu; nie wyciąga się wniosku o zmianie.');
 if(!family)return comparison.explanation;
 const subject=familyText(family.subject),actual=calendarReadingValue(measure,'actual'),previous=calendarReadingValue(measure,'previous');
 const relation=measure.previous_kind==='previous_estimate'?et('the preceding estimate of the same quarter','poprzedniego szacunku tego samego kwartału'):measure.previous_kind==='previous_decision'?et('the preceding decision','poprzedniej decyzji'):et('the preceding reference period','poprzedniego okresu referencyjnego');
 const direction=comparison.direction;
 let text=direction==='neutral'?et(`${subject} was unchanged from ${relation}.`,`${subject}: bez zmiany względem ${relation}.`)
  :et(`${subject} ${direction==='positive'?'rose':'fell'} from ${previous} to ${actual} compared with ${relation}.`,`${subject}: ${direction==='positive'?'wzrost':'spadek'} z ${previous} do ${actual} względem ${relation}.`);
 if(family.id==='jolts'){
  const amount=comparison.text.replace(/^[+−-]/,'');
  text=direction==='neutral'?et('Job openings were unchanged from the preceding month.','Liczba wolnych miejsc pracy nie zmieniła się względem poprzedniego miesiąca.')
   :et(`Job openings ${direction==='positive'?'rose':'fell'} by ${amount} from the preceding month. This is not the same as a change in employment.`,`Liczba wolnych miejsc pracy ${direction==='positive'?'wzrosła':'spadła'} o ${amount} względem poprzedniego miesiąca. Nie jest to równoznaczne ze zmianą zatrudnienia.`);
 }
 if(family.pmi&&measure.actual>=0&&measure.actual<=100){
  // Avoid the grammatical gender of the general template for an index.
  text=et(`${subject} moved from ${previous} to ${actual}.`,`${subject}: zmiana z ${previous} do ${actual}.`);
  text+=et(` It is ${measure.actual>50?'above':measure.actual<50?'below':'at'} 50 points.`,` Znajduje się ${measure.actual>50?'powyżej':measure.actual<50?'poniżej':'na poziomie'} 50 pkt.`);
 }
 return text;
}

export function insightWarnings(event:CalendarEvent,measure?:CalendarMeasure):string[]{
 const warnings:string[]=[];
 if(event.schedule_status==='conflict')warnings.push(et('Official schedule evidence conflicts; the publication time is unconfirmed.','Dowody harmonogramu są rozbieżne; godzina publikacji nie jest potwierdzona.'));
 if(!measure)return warnings;
 if(measure.mapping_status!=='confirmed')warnings.push(et('The observation period or measure mapping is unconfirmed.','Okres odczytu lub przypisanie miary nie są potwierdzone.'));
 if(measure.source_comparison==='conflict')warnings.push(et('Available sources disagree; the selected reading is shown.','Dostępne źródła podają rozbieżne wartości; pokazano wybrany odczyt.'));
 if(measure.comparison_status==='mixed_sources')warnings.push(et('Actual and Previous use different sources; no change is calculated.','Aktualny i Poprzednio pochodzą z różnych źródeł; zmiana nie jest obliczana.'));
 if(measure.selected_source==='bls:cpi'){
  warnings.push(measure.cpi_rate_kind==='published_report_rate'?et('Published rates from one verified BLS report.','Opublikowane stopy z jednego zweryfikowanego raportu BLS.'):et('Derived from BLS index levels, rounded to one decimal; may differ from published rates. History uses the same captured response and may include revisions.','Wyliczone z poziomów indeksu BLS, zaokrąglone do jednego miejsca; mogą różnić się od opublikowanych stóp. Historia z tej samej odpowiedzi może zawierać rewizje.'));
  return warnings;
 }
 if(measure.selected_source==='bls:employment'){
  warnings.push(et('Current and Previous come from one captured BLS response. Previous may include revisions.','Aktualny i Poprzednio pochodz\u0105 z jednej pobranej odpowiedzi BLS. Poprzednio mo\u017ce zawiera\u0107 rewizje.'));
  const earlier=measure.fred_alternative?.previous;
  if(earlier!==null&&earlier!==undefined&&earlier!==measure.previous)warnings.push(et(`BLS Previous: ${calendarReadingValue(measure,'previous')}. Earlier locally stored: ${calendarReadingValue({...measure,previous:earlier},'previous')}.`,`Poprzednio BLS: ${calendarReadingValue(measure,'previous')}. Wcze\u015bniej zapisane lokalnie: ${calendarReadingValue({...measure,previous:earlier},'previous')}.`));
  if(measure.bls_method?.startsWith('derived'))warnings.push(et('Monthly wage change is derived from published dollar levels and rounded to one decimal.','Miesi\u0119czna zmiana p\u0142ac jest wyliczona z opublikowanych poziom\u00f3w dolarowych i zaokr\u0105glona do jednego miejsca.'));
  return warnings;
 }
 if(measure.data_version==='current_vintage')warnings.push(et('This reading may include later revisions.','Odczyt może obejmować późniejsze rewizje.'));
 else if(measure.revision_confirmed)warnings.push(et('This is a revised estimate.','To zrewidowany szacunek.'));
 return warnings;
}
